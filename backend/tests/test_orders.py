import pytest
from unittest.mock import AsyncMock, patch
from app.core.odoo_client import odoo_client


@pytest.mark.asyncio
async def test_checkout_order_success(client, db_session):
    payload = {
        "client_order_ref": "WEB-ORDER-TDD-001",
        "customer": {
            "name": "Trần Văn B",
            "phone": "0912345678",
            "email": "vanb@example.com",
            "shipping_address": {
                "street": "456 Nguyễn Huệ",
                "city": "Hồ Chí Minh"
            }
        },
        "payment_method": "vnpay",
        "hold_minutes": 15,
        "order_lines": [
            {
                "sku": "SP-GIAY-THE-THAO-42",
                "qty": 1,
                "price_unit": 750000
            }
        ]
    }

    mock_odoo_res = {
        "status": "success",
        "odoo_order_id": 9999,
        "odoo_name": "SO00999",
        "hold_expires_at": "2026-09-28T18:00:00Z",
        "amount_total": 750000.0
    }

    with patch.object(odoo_client, "create_web_order_atomic", new=AsyncMock(return_value=mock_odoo_res)):
        response = await client.post("/api/v1/orders/checkout", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["odoo_order_id"] == 9999
        assert "sandbox.vnpayment.vn" in data["payment_url"]

        # Test Idempotency: Gửi lại cùng payload -> phải trả về cached response
        response_dup = await client.post("/api/v1/orders/checkout", json=payload)
        assert response_dup.status_code == 200
        assert response_dup.json()["odoo_order_id"] == 9999


@pytest.mark.asyncio
async def test_checkout_order_insufficient_stock(client):
    payload = {
        "client_order_ref": "WEB-ORDER-OOS-001",
        "customer": {
            "name": "Lê Thị C",
            "phone": "0933333333",
            "shipping_address": {"street": "789 Điện Biên Phủ", "city": "Đà Nẵng"}
        },
        "payment_method": "vnpay",
        "order_lines": [{"sku": "SP-OUT-OF-STOCK", "qty": 10, "price_unit": 100000}]
    }

    mock_odoo_res = {
        "status": "error",
        "code": "INSUFFICIENT_STOCK",
        "message": "Sản phẩm SP-OUT-OF-STOCK không đủ tồn kho"
    }

    with patch.object(odoo_client, "create_web_order_atomic", new=AsyncMock(return_value=mock_odoo_res)):
        response = await client.post("/api/v1/orders/checkout", json=payload)
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error_code"] == "INSUFFICIENT_STOCK"
