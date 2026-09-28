from enum import Enum
from dataclasses import dataclass
from typing import Optional, List


class WarehouseType(str, Enum):
    CENTRAL_DC = "central_dc"       # Kho Tổng phân phối
    RETAIL_STORE = "retail_store"   # Cửa hàng bán lẻ (có máy POS)
    TRANSIT = "transit"             # Kho trung chuyển nội bộ


class StockQueryMode(str, Enum):
    ONLINE = "online"   # E-commerce: Lọc kho online, trừ safety buffer quầy POS, ưu tiên DC
    POS = "pos"         # Bán lẻ tại quầy: Không trừ buffer tại quầy hiện tại, xem kho lân cận
    B2B = "b2b"         # Bán buôn / Đại lý: Chỉ quét Kho Tổng / DC
    AUDIT = "audit"     # Kế toán / Kiểm toán kho: Xem toàn bộ tồn thô (raw inventory)


@dataclass(frozen=True)
class SKU:
    """Value Object đại diện cho mã SKU chuẩn hóa (ví dụ: POLO-DEN-L)"""
    value: str

    def __post_init__(self):
        clean_val = self.value.strip().upper()
        if not clean_val or len(clean_val) < 3:
            raise ValueError(f"SKU không hợp lệ: '{self.value}' (tối thiểu 3 ký tự)")
        object.__setattr__(self, 'value', clean_val)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class StockLocation:
    """Value Object đại diện cho một địa điểm kho vật lý"""
    id: int
    code: str
    name: str
    warehouse_type: WarehouseType
    is_omnichannel_enabled: bool = True
    priority: int = 10  # Số càng nhỏ độ ưu tiên càng cao (Kho Tổng = 1, Cửa hàng = 10+)


@dataclass(frozen=True)
class InventoryLevel:
    """Value Object ghi nhận số lượng tồn kho tại một địa điểm"""
    location: StockLocation
    sku: SKU
    on_hand_qty: float
    reserved_qty: float
    safety_stock_buffer: float = 0.0  # Lượng hàng đệm tại cửa hàng giữ lại cho khách tại quầy

    @property
    def free_qty(self) -> float:
        """Tồn kho thực tế chưa bị đặt mua"""
        return max(0.0, self.on_hand_qty - self.reserved_qty)

    @property
    def available_for_online(self) -> float:
        """Tồn kho cho phép Website bán (đã trừ lượng đệm an toàn của quầy POS)"""
        return max(0.0, self.free_qty - self.safety_stock_buffer)


@dataclass(frozen=True)
class AllocationItem:
    """Kế hoạch trích xuất tồn kho cho một SKU cụ thể"""
    sku: SKU
    location: StockLocation
    allocated_qty: float


@dataclass(frozen=True)
class AllocationPlan:
    """Kết quả phân bổ tồn kho đa điểm Omnichannel"""
    is_fulfilled: bool
    items: List[AllocationItem]
    missing_qty: float = 0.0
    notes: Optional[str] = None
