from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from app.domain.inventory.models import SKU, AllocationPlan
from app.domain.inventory.services import OmnichannelAllocationPolicy
from app.domain.inventory.ports import IInventoryRepository


@dataclass(frozen=True)
class AllocateStockCommand:
    sku_code: str
    requested_qty: float
    order_reference: str
    allow_split_shipment: bool = False


@dataclass(frozen=True)
class AllocateStockResult:
    is_success: bool
    sku: str
    requested_qty: float
    allocated_qty: float
    missing_qty: float
    plan: Optional[AllocationPlan] = None
    message: str = ""


class AllocateStockHandler:
    def __init__(self, repo: IInventoryRepository):
        self.repo = repo

    async def handle(self, command: AllocateStockCommand) -> AllocateStockResult:
        sku = SKU(command.sku_code)
        levels = await self.repo.get_inventory_levels(sku)

        # Áp dụng Domain Policy
        plan = OmnichannelAllocationPolicy.allocate(
            sku=sku,
            requested_qty=command.requested_qty,
            inventory_levels=levels,
            allow_split_shipment=command.allow_split_shipment
        )

        if not plan.is_fulfilled:
            return AllocateStockResult(
                is_success=False,
                sku=str(sku),
                requested_qty=command.requested_qty,
                allocated_qty=command.requested_qty - plan.missing_qty,
                missing_qty=plan.missing_qty,
                plan=plan,
                message=plan.notes or "Không đủ tồn kho trên toàn hệ thống"
            )

        # Thực thi giữ tồn kho qua Adapter
        exec_ok = await self.repo.execute_allocation(plan, command.order_reference)
        if not exec_ok:
            return AllocateStockResult(
                is_success=False,
                sku=str(sku),
                requested_qty=command.requested_qty,
                allocated_qty=0.0,
                missing_qty=command.requested_qty,
                plan=plan,
                message="Lỗi khi xác lập giữ chỗ tồn kho trên ERP Odoo"
            )

        return AllocateStockResult(
            is_success=True,
            sku=str(sku),
            requested_qty=command.requested_qty,
            allocated_qty=command.requested_qty,
            missing_qty=0.0,
            plan=plan,
            message=plan.notes or "Phân bổ tồn kho thành công"
        )
