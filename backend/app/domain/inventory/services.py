from typing import List
from app.domain.inventory.models import (
    SKU,
    InventoryLevel,
    AllocationPlan,
    AllocationItem,
    WarehouseType
)


class OmnichannelAllocationPolicy:
    """
    Domain Service: Chính sách điều phối & phân bổ tồn kho đa điểm (Omnichannel).
    Nguyên tắc cốt lõi:
    1. Ưu tiên số 1: Xuất từ Kho Tổng (Central DC) để tập trung đơn online và tối ưu logistics.
    2. Fallback số 2: Nếu Kho Tổng không đủ hàng, tìm Cửa hàng bán lẻ (Retail Store) có đủ tồn kho.
    3. Bảo vệ quầy POS: Luôn tôn trọng `safety_stock_buffer` tại Cửa hàng để quầy thu ngân không bị thiếu hàng.
    """

    @staticmethod
    def allocate(
        sku: SKU,
        requested_qty: float,
        inventory_levels: List[InventoryLevel],
        allow_split_shipment: bool = False
    ) -> AllocationPlan:
        if requested_qty <= 0:
            raise ValueError("Số lượng yêu cầu phân bổ phải lớn hơn 0")

        # 1. Lọc các kho được phép bán online và sắp xếp theo thứ tự ưu tiên
        valid_stocks = [
            inv for inv in inventory_levels
            if inv.location.is_omnichannel_enabled and inv.available_for_online > 0
        ]
        # Sắp xếp: Kho Tổng trước (priority nhỏ nhất), sau đó đến Cửa hàng có tồn kho nhiều nhất
        valid_stocks.sort(key=lambda x: (x.location.priority, -x.available_for_online))

        if not valid_stocks:
            return AllocationPlan(
                is_fulfilled=False,
                items=[],
                missing_qty=requested_qty,
                notes=f"SKU {sku} đã hết hàng trên toàn bộ hệ thống (kể cả lượng đệm an toàn)."
            )

        # 2. Chiến lược A: Kiểm tra xem Kho Tổng có đủ toàn bộ số lượng không
        central_stocks = [s for s in valid_stocks if s.location.warehouse_type == WarehouseType.CENTRAL_DC]
        if central_stocks and central_stocks[0].available_for_online >= requested_qty:
            return AllocationPlan(
                is_fulfilled=True,
                items=[AllocationItem(sku=sku, location=central_stocks[0].location, allocated_qty=requested_qty)],
                missing_qty=0.0,
                notes="Phân bổ thành công 100% từ Kho Tổng (Central DC)."
            )

        # 3. Chiến lược B: Nếu Kho Tổng không đủ, tìm 1 Cửa hàng duy nhất có đủ toàn bộ số lượng (tránh chia đơn nếu không cho phép)
        if not allow_split_shipment:
            for store_stock in valid_stocks:
                if store_stock.available_for_online >= requested_qty:
                    return AllocationPlan(
                        is_fulfilled=True,
                        items=[AllocationItem(sku=sku, location=store_stock.location, allocated_qty=requested_qty)],
                        missing_qty=0.0,
                        notes=f"Kho Tổng không đủ. Điều phối thành công từ Cửa hàng {store_stock.location.name}."
                    )
            # Nếu không cho phép chia đơn và không có kho nào chứa đủ requested_qty -> Trả về Thất bại
            return AllocationPlan(
                is_fulfilled=False,
                items=[],
                missing_qty=requested_qty,
                notes=f"Không có địa điểm kho nào đáp ứng đủ {requested_qty} sản phẩm (không cho phép chia đơn)."
            )

        # 4. Chiến lược C: Cho phép chia đơn (Split fulfillment) qua nhiều kho
        allocated_items: List[AllocationItem] = []
        remaining = requested_qty

        for stock in valid_stocks:
            alloc_from_this_loc = min(remaining, stock.available_for_online)
            if alloc_from_this_loc > 0:
                allocated_items.append(AllocationItem(
                    sku=sku,
                    location=stock.location,
                    allocated_qty=alloc_from_this_loc
                ))
                remaining -= alloc_from_this_loc

            if remaining <= 0:
                break

        if remaining <= 0:
            return AllocationPlan(
                is_fulfilled=True,
                items=allocated_items,
                missing_qty=0.0,
                notes="Phân bổ thành công qua hình thức gộp đa kho (Split shipment)."
            )
        else:
            return AllocationPlan(
                is_fulfilled=False,
                items=allocated_items,
                missing_qty=remaining,
                notes=f"Toàn hệ thống chỉ đáp ứng được {requested_qty - remaining}/{requested_qty} sản phẩm."
            )
