from typing import Protocol, List
from app.domain.inventory.models import SKU, InventoryLevel, AllocationPlan


class IInventoryRepository(Protocol):
    """
    Port (Interface) giao tiếp Tồn kho theo nguyên lý Dependency Inversion (DIP).
    Application Layer chỉ gọi interface này, Infrastructure Layer sẽ implement cụ thể qua Odoo 18.
    """

    async def get_inventory_levels(
        self,
        sku: SKU,
        mode: str = "online",
        location_id: int | None = None
    ) -> List[InventoryLevel]:
        """Lấy danh sách tồn kho của SKU trên toàn bộ các kho & chi nhánh theo chế độ (mode)"""
        ...

    async def execute_allocation(self, plan: AllocationPlan, reference: str) -> bool:
        """Thực hiện khóa giữ tồn kho tại các địa điểm theo kế hoạch phân bổ"""
        ...

    async def release_allocation(self, plan: AllocationPlan, reference: str) -> bool:
        """Giải phóng lượng tồn kho đã giữ nếu đơn bị hủy hoặc hết hạn"""
        ...
