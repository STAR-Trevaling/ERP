from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional

from app.domain.inventory.models import SKU, StockQueryMode
from app.application.inventory.queries import GetOmnichannelStockQuery, GetOmnichannelStockHandler
from app.application.inventory.commands import AllocateStockCommand, AllocateStockHandler
from app.infrastructure.odoo.odoo_inventory_adapter import OdooInventoryAdapter
from app.core.odoo_client import odoo_client
from fastapi import Query

router = APIRouter()
inventory_adapter = OdooInventoryAdapter(odoo_client)


class LocationStockResponse(BaseModel):
    location_id: int
    location_code: str
    location_name: str
    warehouse_type: str
    priority: int = 10
    on_hand: float
    reserved: float
    available_qty: float = 0.0
    available_for_online: float


class OmnichannelStockResponse(BaseModel):
    sku: str
    mode: str = "online"
    total_on_hand: float
    total_reserved: float
    total_available_qty: float = 0.0
    total_available_for_online: float
    locations: List[LocationStockResponse]


class AllocateRequest(BaseModel):
    sku: str = Field(..., description="Mã SKU sản phẩm")
    qty: float = Field(..., gt=0, description="Số lượng cần phân bổ")
    order_ref: str = Field(..., description="Mã tham chiếu đơn hàng")
    allow_split: bool = Field(False, description="Cho phép chia đơn qua nhiều kho")


@router.get("/stock/{sku}", response_model=OmnichannelStockResponse)
async def get_omnichannel_stock(
    sku: str,
    mode: StockQueryMode = Query(StockQueryMode.ONLINE, description="Chế độ tồn kho: online | pos | b2b | audit"),
    location_id: Optional[int] = Query(None, description="ID địa điểm kho chỉ định (dùng cho quầy POS)")
):
    """
    Truy vấn tồn kho đa chế độ (Multi-Mode Omnichannel Stock):
    - mode='online': Lọc kho online, trừ safety buffer quầy POS, ưu tiên DC.
    - mode='pos': Tồn kho quầy POS, không trừ buffer tại quầy hiện tại, xem kho lân cận.
    - mode='b2b': Chỉ quét Kho Tổng / DC số lượng lớn.
    - mode='audit': Kế toán / Kiểm kê xem toàn bộ tồn kho thô.
    """
    try:
        handler = GetOmnichannelStockHandler(inventory_adapter)
        res = await handler.handle(GetOmnichannelStockQuery(
            sku_code=sku,
            mode=mode.value,
            location_id=location_id
        ))
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/allocate")
async def allocate_stock(request: AllocateRequest):
    """
    Kích hoạt thuật toán phân bổ tồn kho đa điểm (Omnichannel Allocation):
    1. Ưu tiên Kho Tổng (Central DC).
    2. Fallback sang Cửa hàng có đủ hàng nếu Kho Tổng thiếu.
    """
    try:
        handler = AllocateStockHandler(inventory_adapter)
        result = await handler.handle(AllocateStockCommand(
            sku_code=request.sku,
            requested_qty=request.qty,
            order_reference=request.order_ref,
            allow_split_shipment=request.allow_split
        ))

        return {
            "is_success": result.is_success,
            "sku": result.sku,
            "requested_qty": result.requested_qty,
            "allocated_qty": result.allocated_qty,
            "missing_qty": result.missing_qty,
            "message": result.message,
            "plan_items": [
                {
                    "location_name": item.location.name,
                    "warehouse_type": item.location.warehouse_type.value,
                    "allocated_qty": item.allocated_qty
                }
                for item in (result.plan.items if result.plan else [])
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
