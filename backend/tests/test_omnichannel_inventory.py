import pytest
from app.domain.inventory.models import (
    SKU,
    StockLocation,
    WarehouseType,
    InventoryLevel
)
from app.domain.inventory.services import OmnichannelAllocationPolicy


@pytest.fixture
def central_warehouse():
    return StockLocation(
        id=1,
        code="WH-DC",
        name="Kho Tổng Phân Phối (Central DC)",
        warehouse_type=WarehouseType.CENTRAL_DC,
        is_omnichannel_enabled=True,
        priority=1
    )


@pytest.fixture
def store_q1():
    return StockLocation(
        id=2,
        code="STORE-Q1",
        name="Cửa hàng Quận 1",
        warehouse_type=WarehouseType.RETAIL_STORE,
        is_omnichannel_enabled=True,
        priority=10
    )


@pytest.fixture
def store_cau_giay():
    return StockLocation(
        id=3,
        code="STORE-CG",
        name="Cửa hàng Cầu Giấy",
        warehouse_type=WarehouseType.RETAIL_STORE,
        is_omnichannel_enabled=True,
        priority=10
    )


def test_allocation_priority_central_dc(central_warehouse, store_q1):
    """Khi Kho Tổng có đủ hàng, 100% đơn hàng được phân bổ từ Kho Tổng"""
    sku = SKU("POLO-BLACK-L")
    inventory = [
        InventoryLevel(location=central_warehouse, sku=sku, on_hand_qty=20, reserved_qty=0),
        InventoryLevel(location=store_q1, sku=sku, on_hand_qty=10, reserved_qty=0, safety_stock_buffer=2)
    ]

    plan = OmnichannelAllocationPolicy.allocate(sku, requested_qty=5, inventory_levels=inventory)

    assert plan.is_fulfilled is True
    assert len(plan.items) == 1
    assert plan.items[0].location.id == central_warehouse.id
    assert plan.items[0].allocated_qty == 5.0
    assert plan.notes is not None and "Kho Tổng" in plan.notes


def test_allocation_fallback_to_store_when_dc_empty(central_warehouse, store_q1):
    """Khi Kho Tổng hết hàng, hệ thống tự động fallback sang Cửa hàng có đủ hàng"""
    sku = SKU("POLO-BLACK-L")
    inventory = [
        InventoryLevel(location=central_warehouse, sku=sku, on_hand_qty=0, reserved_qty=0),
        InventoryLevel(location=store_q1, sku=sku, on_hand_qty=15, reserved_qty=0, safety_stock_buffer=2)
    ]

    plan = OmnichannelAllocationPolicy.allocate(sku, requested_qty=8, inventory_levels=inventory)

    assert plan.is_fulfilled is True
    assert len(plan.items) == 1
    assert plan.items[0].location.id == store_q1.id
    assert plan.items[0].allocated_qty == 8.0
    assert plan.notes is not None and "Cửa hàng Quận 1" in plan.notes


def test_safety_stock_buffer_protection(central_warehouse, store_q1):
    """Cửa hàng có 10 sản phẩm, buffer an toàn 2 -> Chỉ bán online tối đa 8 sản phẩm"""
    sku = SKU("POLO-BLACK-L")
    inventory = [
        InventoryLevel(location=central_warehouse, sku=sku, on_hand_qty=0, reserved_qty=0),
        InventoryLevel(location=store_q1, sku=sku, on_hand_qty=10, reserved_qty=0, safety_stock_buffer=2)  # available = 8
    ]

    # Đặt 9 cái (vượt quá 8) -> Không cho xuất nếu không có kho khác
    plan = OmnichannelAllocationPolicy.allocate(sku, requested_qty=9, inventory_levels=inventory, allow_split_shipment=False)

    assert plan.is_fulfilled is False
    assert plan.missing_qty == 9.0


def test_split_shipment_across_multiple_locations(central_warehouse, store_q1, store_cau_giay):
    """Khi bật allow_split_shipment, hệ thống gom tồn từ nhiều kho để đáp ứng đủ đơn"""
    sku = SKU("POLO-BLACK-L")
    inventory = [
        InventoryLevel(location=central_warehouse, sku=sku, on_hand_qty=3, reserved_qty=0),                  # dc available = 3
        InventoryLevel(location=store_q1, sku=sku, on_hand_qty=5, reserved_qty=0, safety_stock_buffer=1),   # q1 available = 4
        InventoryLevel(location=store_cau_giay, sku=sku, on_hand_qty=5, reserved_qty=0, safety_stock_buffer=1) # cg available = 4
    ]

    plan = OmnichannelAllocationPolicy.allocate(sku, requested_qty=10, inventory_levels=inventory, allow_split_shipment=True)

    assert plan.is_fulfilled is True
    assert len(plan.items) == 3
    total_allocated = sum(item.allocated_qty for item in plan.items)
    assert total_allocated == 10.0


def test_sku_value_object():
    """Kiểm tra tính bất biến và chuẩn hóa của Value Object SKU (Requirement 1A)"""
    sku1 = SKU("  polo-den-l  ")
    assert sku1.value == "POLO-DEN-L"
    assert str(sku1) == "POLO-DEN-L"

    with pytest.raises(ValueError):
        SKU("  ")

    with pytest.raises(ValueError):
        SKU("A")


def test_inventory_level_properties(store_q1):
    """Kiểm tra logic tính toán tồn khả dụng và tồn đệm an toàn"""
    sku = SKU("POLO-WHITE-M")
    inv = InventoryLevel(
        location=store_q1,
        sku=sku,
        on_hand_qty=15.0,
        reserved_qty=3.0,
        safety_stock_buffer=2.0
    )
    assert inv.free_qty == 12.0
    assert inv.available_for_online == 10.0


@pytest.mark.asyncio
async def test_odoo_adapter_custom_rpc_stock():
    """Kiểm tra Adapter đọc trực tiếp custom RPC action_get_omnichannel_stock của Odoo 18"""
    from unittest.mock import AsyncMock
    from app.infrastructure.odoo.odoo_inventory_adapter import OdooInventoryAdapter

    mock_client = AsyncMock()
    mock_client.execute_kw.return_value = {
        "status": "success",
        "data": [
            {
                "location_id": 10,
                "location_code": "WH/Stock",
                "location_name": "Kho Tổng",
                "warehouse_type": "central_dc",
                "priority": 1,
                "safety_stock_buffer": 0.0,
                "on_hand_qty": 50.0,
                "reserved_qty": 5.0,
                "free_qty": 45.0,
                "available_for_online": 45.0
            }
        ]
    }

    adapter = OdooInventoryAdapter(mock_client)
    sku = SKU("POLO-DEN-L")
    levels = await adapter.get_inventory_levels(sku)

    assert len(levels) == 1
    assert levels[0].location.warehouse_type == WarehouseType.CENTRAL_DC
    assert levels[0].available_for_online == 45.0


@pytest.mark.asyncio
async def test_inventory_api_endpoints(client):
    """Kiểm tra API Router /api/v1/inventory qua FastAPI Test Client"""
    # 1. Test GET /stock/{sku}
    res = await client.get("/api/v1/inventory/stock/POLO-PIMA-M")
    assert res.status_code == 200
    data = res.json()
    assert data["sku"] == "POLO-PIMA-M"
    assert "total_available_for_online" in data

    # 2. Test POST /allocate
    alloc_res = await client.post("/api/v1/inventory/allocate", json={
        "sku": "POLO-PIMA-M",
        "qty": 2.0,
        "order_ref": "TEST-ORD-001",
        "allow_split": False
    })
    assert alloc_res.status_code == 200
    alloc_data = alloc_res.json()
    assert alloc_data["sku"] == "POLO-PIMA-M"
    assert alloc_data["requested_qty"] == 2.0


@pytest.mark.asyncio
async def test_inventory_api_multi_modes(client):
    """Kiểm tra các chế độ truy vấn tồn kho đa kênh (Multi-Mode Strategy)"""
    # 1. POS Mode với location_id chỉ định
    res_pos = await client.get("/api/v1/inventory/stock/POLO-PIMA-M?mode=pos&location_id=2")
    assert res_pos.status_code == 200
    data_pos = res_pos.json()
    assert data_pos["mode"] == "pos"

    # 2. B2B Mode
    res_b2b = await client.get("/api/v1/inventory/stock/POLO-PIMA-M?mode=b2b")
    assert res_b2b.status_code == 200
    assert res_b2b.json()["mode"] == "b2b"

    # 3. Audit Mode
    res_audit = await client.get("/api/v1/inventory/stock/POLO-PIMA-M?mode=audit")
    assert res_audit.status_code == 200
    assert res_audit.json()["mode"] == "audit"


