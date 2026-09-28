import hmac
import hashlib
import urllib.parse
from typing import Dict, Any
from app.core.config import settings


class PaymentSignatureVerifier:
    @staticmethod
    def verify_vnpay_signature(params: Dict[str, Any], secret_key: str = None) -> bool:
        """
        Verify chữ ký HMAC-SHA512 của VNPay:
        1. Lọc bỏ vnp_SecureHash và vnp_SecureHashType
        2. Sắp xếp key theo alphabet
        3. Tạo hashData dạng key=value&key=value (URL-encoded)
        4. Tính HMAC-SHA512 và so sánh với vnp_SecureHash
        """
        secret = secret_key or settings.VNPAY_HASH_SECRET
        vnp_secure_hash = params.get("vnp_SecureHash", "")
        if not vnp_secure_hash:
            return False

        # Lọc tham số bắt đầu bằng 'vnp_' và loại trừ hash
        filtered_params = {
            k: v for k, v in params.items()
            if k.startswith("vnp_") and k not in ["vnp_SecureHash", "vnp_SecureHashType"] and v is not None and str(v) != ""
        }

        # Sắp xếp theo key
        sorted_keys = sorted(filtered_params.keys())
        hash_data = "&".join([f"{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(str(filtered_params[k]))}" for k in sorted_keys])

        calculated_hash = hmac.new(
            secret.encode("utf-8"),
            hash_data.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(calculated_hash.lower(), vnp_secure_hash.lower())

    @staticmethod
    def verify_momo_signature(params: Dict[str, Any], secret_key: str = None) -> bool:
        """
        Verify chữ ký HMAC-SHA256 của MoMo:
        Chuỗi ký chuẩn: accessKey={}&amount={}&extraData={}&message={}&orderId={}&orderInfo={}&orderType={}&partnerCode={}&payType={}&requestId={}&responseTime={}&resultCode={}&transId={}
        """
        secret = secret_key or settings.MOMO_SECRET_KEY
        received_signature = params.get("signature", "")
        if not received_signature:
            return False

        raw_signature = (
            f"accessKey={params.get('accessKey', settings.MOMO_ACCESS_KEY)}&"
            f"amount={params.get('amount')}&"
            f"extraData={params.get('extraData', '')}&"
            f"message={params.get('message', '')}&"
            f"orderId={params.get('orderId')}&"
            f"orderInfo={params.get('orderInfo', '')}&"
            f"orderType={params.get('orderType', '')}&"
            f"partnerCode={params.get('partnerCode')}&"
            f"payType={params.get('payType', '')}&"
            f"requestId={params.get('requestId')}&"
            f"responseTime={params.get('responseTime')}&"
            f"resultCode={params.get('resultCode')}&"
            f"transId={params.get('transId')}"
        )

        calculated_signature = hmac.new(
            secret.encode("utf-8"),
            raw_signature.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_signature.lower(), received_signature.lower())
