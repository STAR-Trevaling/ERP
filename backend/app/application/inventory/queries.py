from dataclasses import dataclass
from typing import List, Dict, Any
from app.domain.inventory.models import SKU
from app.domain.inventory.ports import IInventoryRepository


@dataclass(frozen=True)
class GetOmnichannelStockQuery:
    sku_code: str
    mode: str = "online"
    location_id: int | None = None


@dataclass(frozen=True)
class LocationStockDTO:
    location_id: int
    location_code: str
    location_name: str
    warehouse_type: str
    priority: int
    on_hand: float
    reserved: float
    available_qty: float
    available_for_online: float


@dataclass(frozen=True)
class OmnichannelStockResult:
    sku: str
    mode: str
    total_on_hand: float
    total_reserved: float
    total_available_qty: float
    total_available_for_online: float
    locations: List[LocationStockDTO]


class GetOmnichannelStockHandler:
    def __init__(self, repo: IInventoryRepository):
        self.repo = repo

    async def handle(self, query: GetOmnichannelStockQuery) -> OmnichannelStockResult:
        sku = SKU(query.sku_code)
        levels = await self.repo.get_inventory_levels(
            sku,
            mode=query.mode,
            location_id=query.location_id
        )

        loc_dtos = [
            LocationStockDTO(
                location_id=lvl.location.id,
                location_code=lvl.location.code,
                location_name=lvl.location.name,
                warehouse_type=lvl.location.warehouse_type.value,
                priority=lvl.location.priority,
                on_hand=lvl.on_hand_qty,
                reserved=lvl.reserved_qty,
                available_qty=lvl.available_for_online,
                available_for_online=lvl.available_for_online
            )
            for lvl in levels
        ]

        total_on_hand = sum(lvl.on_hand_qty for lvl in levels)
        total_reserved = sum(lvl.reserved_qty for lvl in levels)
        total_avail = sum(lvl.available_for_online for lvl in levels)

        return OmnichannelStockResult(
            sku=str(sku),
            mode=query.mode,
            total_on_hand=total_on_hand,
            total_reserved=total_reserved,
            total_available_qty=total_avail,
            total_available_for_online=total_avail,
            locations=loc_dtos
        )

