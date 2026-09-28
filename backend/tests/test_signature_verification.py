import pytest
import hmac
import hashlib
import urllib.parse
from app.services.payment_verifier import PaymentSignatureVerifier


def test_vnpay_signature_verification_success():
    secret = "TEST_SECRET_KEY_123456"
    params = {
        "vnp_Amount": "10000000",
        "vnp_Command": "pay",
        "vnp_CreateDate": "20260928120000",
        "vnp_CurrCode": "VND",
        "vnp_IpAddr": "127.0.0.1",
        "vnp_Locale": "vn",
        "vnp_OrderInfo": "Thanh toan don hang WEB123",
        "vnp_ResponseCode": "00",
        "vnp_TmnCode": "TESTTMN",
        "vnp_TransactionNo": "14234567",
        "vnp_TxnRef": "WEB123",
    }

    # Tính chữ ký chuẩn
    sorted_keys = sorted(params.keys())
    hash_data = "&".join([f"{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(str(params[k]))}" for k in sorted_keys])
    expected_hash = hmac.new(secret.encode("utf-8"), hash_data.encode("utf-8"), hashlib.sha512).hexdigest()

    params["vnp_SecureHash"] = expected_hash

    # Verify
    assert PaymentSignatureVerifier.verify_vnpay_signature(params, secret_key=secret) is True


def test_vnpay_signature_verification_tampered():
    secret = "TEST_SECRET_KEY_123456"
    params = {
        "vnp_Amount": "10000000",
        "vnp_TxnRef": "WEB123",
        "vnp_SecureHash": "fake_or_tampered_hash_123"
    }
    assert PaymentSignatureVerifier.verify_vnpay_signature(params, secret_key=secret) is False


def test_momo_signature_verification():
    secret = "TEST_MOMO_SECRET_789"
    access_key = "ACCESS123"
    params = {
        "accessKey": access_key,
        "amount": 250000,
        "extraData": "",
        "message": "Successful.",
        "orderId": "MM_ORDER_999",
        "orderInfo": "Thanh toan don hang MM_ORDER_999",
        "orderType": "momo_wallet",
        "partnerCode": "MOMO_VN",
        "payType": "qr",
        "requestId": "REQ_999",
        "responseTime": 1727521200,
        "resultCode": 0,
        "transId": 9876543210
    }

    raw_signature = (
        f"accessKey={params['accessKey']}&"
        f"amount={params['amount']}&"
        f"extraData={params['extraData']}&"
        f"message={params['message']}&"
        f"orderId={params['orderId']}&"
        f"orderInfo={params['orderInfo']}&"
        f"orderType={params['orderType']}&"
        f"partnerCode={params['partnerCode']}&"
        f"payType={params['payType']}&"
        f"requestId={params['requestId']}&"
        f"responseTime={params['responseTime']}&"
        f"resultCode={params['resultCode']}&"
        f"transId={params['transId']}"
    )

    signature = hmac.new(secret.encode("utf-8"), raw_signature.encode("utf-8"), hashlib.sha256).hexdigest()
    params["signature"] = signature

    assert PaymentSignatureVerifier.verify_momo_signature(params, secret_key=secret) is True
