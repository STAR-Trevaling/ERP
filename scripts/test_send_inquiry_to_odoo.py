import hashlib
import hmac
import json
import urllib.error
import urllib.request
import uuid

SECRET = "star_travels_super_secret_webhook_key_2026"
URL = "http://localhost:8069/api/v1/travel/inquiry"

event_id = str(uuid.uuid4())
payload = {
    "event_id": event_id,
    "event_type": "inquiry.created",
    "event_version": 1,
    "source": "website",
    "data": {
        "customer": {
            "name": "Nguyễn Hoàng Nam",
            "email": "nam.nguyen@startravels.vn",
            "phone": "+84 988 123 456",
            "identity_provider": "website"
        },
        "interest": {
            "type": "tour_booking",
            "destination_slug": "ha-long",
            "tour_slug": "tour-ha-long-cruise-2n1d",
            "travel_date": "2026-11-15",
            "traveler_count": 2,
            "message": "Tôi muốn đặt tour du thuyền Hạ Long 2N1Đ cho 2 người lớn."
        },
        "source_metadata": {
            "channel": "website",
            "campaign": "autumn_promotion_2026"
        }
    }
}

raw_bytes = json.dumps(payload).encode("utf-8")
signature = hmac.new(SECRET.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Signature-SHA256": signature,
    "X-Event-ID": event_id,
    "Idempotency-Key": event_id,
}

req = urllib.request.Request(URL, data=raw_bytes, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("HTTP Status:", resp.getcode())
        print("Response:", resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode("utf-8"))
except Exception as e:
    print("Error:", str(e))
