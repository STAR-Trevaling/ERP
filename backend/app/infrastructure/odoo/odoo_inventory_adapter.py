import logging
from typing import List, Dict, Any
from app.domain.inventory.models import (
    SKU,
    StockLocation,
    WarehouseType,
    InventoryLevel,
    AllocationPlan
)
from app.domain.inventory.ports import IInventoryRepository
from app.core.odoo_client import AsyncOdooClient

logger = logging.getLogger(__name__)


class OdooInventoryAdapter(IInventoryRepository):
    """
    Infrastructure Adapter kết nối Odoo 18:
    Thực thi IInventoryRepository qua giao thức JSON-RPC bất đồng bộ.
    """

    def __init__(self, odoo_client: AsyncOdooClient):
        self.odoo = odoo_client

    async def get_inventory_levels(
        self,
        sku: SKU,
        mode: str = "online",
        location_id: int | None = None
    ) -> List[InventoryLevel]:
        try:
            # 1. Thử gọi trực tiếp Custom RPC action_get_omnichannel_stock từ addon custom_inventory_core
            try:
                rpc_res = await self.odoo.execute_kw(
                    model="product.product",
                    method="action_get_omnichannel_stock",
                    args=[sku.value, mode, location_id]
                )
                if rpc_res and rpc_res.get("status") == "success" and "data" in rpc_res:
                    results: List[InventoryLevel] = []
                    for item in rpc_res["data"]:
                        loc_type = (
                            WarehouseType.CENTRAL_DC
                            if item.get("warehouse_type") == "central_dc"
                            else WarehouseType.RETAIL_STORE
                        )
                        location = StockLocation(
                            id=item["location_id"],
                            code=item.get("location_code", f"LOC-{item['location_id']}"),
                            name=item.get("location_name", "Kho"),
                            warehouse_type=loc_type,
                            is_omnichannel_enabled=True,
                            priority=int(item.get("priority", 10))
                        )
                        results.append(InventoryLevel(
                            location=location,
                            sku=sku,
                            on_hand_qty=float(item.get("on_hand_qty", 0.0)),
                            reserved_qty=float(item.get("reserved_qty", 0.0)),
                            safety_stock_buffer=float(item.get("safety_stock_buffer", 0.0))
                        ))
                    return results
            except Exception as rpc_err:
                logger.debug(f"[INVENTORY-ADAPTER] action_get_omnichannel_stock not available, falling back: {rpc_err}")

            # 2. Fallback sang search stock.quant tiêu chuẩn Odoo
            prod_ids = await self.odoo.execute_kw(
                model="product.product",
                method="search",
                args=[[[("default_code", "=", sku.value)]]],
                kwargs={"limit": 1}
            )

            if not prod_ids:
                logger.warning(f"[INVENTORY-ADAPTER] SKU {sku.value} not found in Odoo")
                return []

            product_id = prod_ids[0]

            # Lấy danh sách tồn kho stock.quant theo từng Location
            quants = await self.odoo.execute_kw(
                model="stock.quant",
                method="search_read",
                args=[[[
                    ("product_id", "=", product_id),
                    ("location_id.usage", "=", "internal")
                ]]],
                kwargs={"fields": ["location_id", "quantity", "reserved_quantity"]}
            )

            fallback_results: List[InventoryLevel] = []
            for q in quants:
                loc_id, loc_name = q["location_id"]
                is_central = "WH" in loc_name.upper() or "KHO TỔNG" in loc_name.upper()

                loc_type = WarehouseType.CENTRAL_DC if is_central else WarehouseType.RETAIL_STORE
                priority = 1 if is_central else 10
                safety_buffer = 0.0 if is_central else 2.0  # Cửa hàng giữ lại 2 sản phẩm đệm cho khách tại quầy

                location = StockLocation(
                    id=loc_id,
                    code=f"LOC-{loc_id}",
                    name=loc_name,
                    warehouse_type=loc_type,
                    is_omnichannel_enabled=True,
                    priority=priority
                )

                level = InventoryLevel(
                    location=location,
                    sku=sku,
                    on_hand_qty=float(q.get("quantity", 0.0)),
                    reserved_qty=float(q.get("reserved_quantity", 0.0)),
                    safety_stock_buffer=safety_buffer
                )
                fallback_results.append(level)

            return fallback_results

        except Exception as e:
            logger.error(f"[INVENTORY-ADAPTER] Error fetching stock from Odoo: {str(e)}", exc_info=True)
            return []

    async def execute_allocation(self, plan: AllocationPlan, reference: str) -> bool:
        """Gọi Odoo RPC để giữ chỗ tồn kho chính xác theo từng kho đã chọn"""
        try:
            alloc_payload = [
                {
                    "sku": str(item.sku),
                    "location_id": item.location.id,
                    "qty": item.allocated_qty,
                    "reference": reference
                }
                for item in plan.items
            ]
            res = await self.odoo.execute_kw(
                model="stock.quant",
                method="action_omnichannel_hold_stock",
                args=[alloc_payload]
            )
            return bool(res and res.get("status") == "success")
        except Exception as e:
            logger.error(f"[INVENTORY-ADAPTER] Error executing allocation in Odoo: {str(e)}")
            return False

    async def release_allocation(self, plan: AllocationPlan, reference: str) -> bool:
        """Gọi Odoo RPC để nhả giữ chỗ tồn kho"""
        try:
            release_payload = [
                {
                    "sku": str(item.sku),
                    "location_id": item.location.id,
                    "qty": item.allocated_qty,
                    "reference": reference
                }
                for item in plan.items
            ]
            res = await self.odoo.execute_kw(
                model="stock.quant",
                method="action_omnichannel_release_stock",
                args=[release_payload]
            )
            return bool(res and res.get("status") == "success")
        except Exception as e:
            logger.error(f"[INVENTORY-ADAPTER] Error releasing allocation in Odoo: {str(e)}")
            return False
