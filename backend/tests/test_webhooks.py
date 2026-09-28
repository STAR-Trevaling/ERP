import pytest
import hmac
import hashlib
import urllib.parse
from app.core.config import settings


@pytest.mark.asyncio
async def test_vnpay_webhook_flow_and_idempotency(client, db_session):
    # 1. Chuẩn bị payload VNPay hợp lệ
    secret = settings.VNPAY_HASH_SECRET
    params = {
        "vnp_Amount": "50000000",
        "vnp_Command": "pay",
        "vnp_CreateDate": "20260928153000",
        "vnp_CurrCode": "VND",
        "vnp_OrderInfo": "Thanh toan don hang WEB-TEST-001",
        "vnp_ResponseCode": "00",
        "vnp_TmnCode": settings.VNPAY_TMN_CODE,
        "vnp_TransactionNo": "99887766",
        "vnp_TransactionStatus": "00",
        "vnp_TxnRef": "WEB-TEST-001",
    }

    sorted_keys = sorted(params.keys())
    hash_data = "&".join([f"{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(str(params[k]))}" for k in sorted_keys])
    params["vnp_SecureHash"] = hmac.new(secret.encode("utf-8"), hash_data.encode("utf-8"), hashlib.sha512).hexdigest()

    # 2. Gửi Webhook lần 1 (Success)
    response_1 = await client.get("/api/v1/webhooks/vnpay", params=params)
    assert response_1.status_code == 200
    data_1 = response_1.json()
    assert data_1["RspCode"] == "00"
    assert data_1["Message"] == "Confirm Success"

    # 3. Gửi lại Webhook lần 2 (Idempotency test: duplicate call from Gateway)
    response_2 = await client.get("/api/v1/webhooks/vnpay", params=params)
    assert response_2.status_code == 200
    data_2 = response_2.json()
    assert data_2["RspCode"] == "02"
    assert data_2["Message"] == "Order already confirmed"


@pytest.mark.asyncio
async def test_vnpay_webhook_invalid_signature(client):
    params = {
        "vnp_Amount": "50000000",
        "vnp_ResponseCode": "00",
        "vnp_TransactionNo": "99887766",
        "vnp_TxnRef": "WEB-TEST-002",
        "vnp_SecureHash": "invalid_hash_value"
    }

    response = await client.get("/api/v1/webhooks/vnpay", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["RspCode"] == "97"
    assert data["Message"] == "Invalid Checksum"
