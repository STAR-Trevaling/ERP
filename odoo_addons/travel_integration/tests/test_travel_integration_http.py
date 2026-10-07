import hashlib
import hmac
import json
import uuid

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestTravelIntegrationHTTP(HttpCase):
    """
    Enterprise SE-grade Integration & API Contract Test Suite.
    Tests real HTTP inbound requests against /api/v1/travel/* endpoints:
    - HMAC-SHA256 signature verification (security against spoofing/tampering)
    - Idempotency-Key protection (protection against network duplicate retries)
    - Bearer and X-API-Key authorization
    - RFC 7807 Problem Details error formats
    """

    def setUp(self):
        super().setUp()
        self.api_key = "star_travels_inbound_api_token_2026"
        self.secret = "star_travels_super_secret_webhook_key_2026"

        self.env["ir.config_parameter"].sudo().set_param(
            "travel.inbound_api_key", self.api_key
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "travel.webhook_secret", self.secret
        )

    def _sign_payload(self, body_bytes: bytes) -> str:
        return hmac.new(self.secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    def test_health_check_endpoint(self):
        """GET /api/v1/travel/health must return 200 OK without requiring authentication."""
        response = self.url_open("/api/v1/travel/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("service", data)

    def test_inquiry_unauthorized_when_credentials_missing(self):
        """POST /api/v1/travel/inquiry without auth header or HMAC must return 401 Problem Details."""
        payload = json.dumps({"test": "data"}).encode("utf-8")
        response = self.url_open(
            "/api/v1/travel/inquiry",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data.get("title"), "Unauthorized")

    def test_inquiry_with_valid_hmac_sha256(self):
        """POST /api/v1/travel/inquiry with correct HMAC-SHA256 signature creates CRM Lead."""
        event_id = str(uuid.uuid4())
        phone = f"091{uuid.uuid4().hex[:7]}"
        payload_dict = {
            "event_id": event_id,
            "event_type": "inquiry.created",
            "source": "website",
            "data": {
                "customer": {
                    "name": "Tran Van Test",
                    "phone": phone,
                    "email": f"{event_id[:8]}@example.com",
                },
                "message": "Looking for Phu Quoc sunset tour.",
                "interest": {
                    "traveler_count": 2,
                },
            },
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._sign_payload(body_bytes)

        response = self.url_open(
            "/api/v1/travel/inquiry",
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Signature-SHA256": signature,
                "Idempotency-Key": event_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("lead_id"))

        # Verify Lead in Odoo Database
        lead = self.env["crm.lead"].sudo().browse(data["lead_id"])
        self.assertEqual(lead.phone, phone)
        self.assertEqual(lead.partner_id.name, "Tran Van Test")

    def test_inquiry_with_api_key_header(self):
        """POST /api/v1/travel/inquiry authenticated via X-API-Key header."""
        event_id = str(uuid.uuid4())
        phone = f"098{uuid.uuid4().hex[:7]}"
        payload_dict = {
            "event_id": event_id,
            "data": {
                "customer": {
                    "name": "Le Thi API Key",
                    "phone": phone,
                },
                "message": "Consultation request via API Key.",
            },
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")

        response = self.url_open(
            "/api/v1/travel/inquiry",
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
                "Idempotency-Key": event_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))

    def test_inquiry_idempotency_replay_protection(self):
        """
        Verify that receiving the identical event twice via HTTP returns cached 200
        response and strictly creates only ONE CRM Lead.
        """
        event_id = str(uuid.uuid4())
        phone = f"097{uuid.uuid4().hex[:7]}"
        payload_dict = {
            "event_id": event_id,
            "data": {
                "customer": {
                    "name": "Bui Hoang Idempotent",
                    "phone": phone,
                },
                "message": "Testing duplicate HTTP submissions.",
            },
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._sign_payload(body_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Signature-SHA256": signature,
            "Idempotency-Key": event_id,
        }

        # First HTTP request
        resp1 = self.url_open("/api/v1/travel/inquiry", data=body_bytes, headers=headers)
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()

        # Second HTTP request (Network Retry / Replay attack)
        resp2 = self.url_open("/api/v1/travel/inquiry", data=body_bytes, headers=headers)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()

        self.assertEqual(data1["lead_id"], data2["lead_id"])

        # Assert database record count
        lead_count = self.env["crm.lead"].sudo().search_count([("phone", "=", phone)])
        self.assertEqual(lead_count, 1, "Must strictly not duplicate CRM lead on retry")

    def test_inquiry_missing_idempotency_key(self):
        """POST /api/v1/travel/inquiry without Idempotency-Key header or event_id must return 400."""
        payload_dict = {
            "data": {
                "customer": {"name": "No Key"},
                "message": "Should fail",
            }
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._sign_payload(body_bytes)

        response = self.url_open(
            "/api/v1/travel/inquiry",
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Signature-SHA256": signature,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("title"), "Missing Idempotency Key")

    def test_partner_application_endpoint(self):
        """POST /api/v1/travel/partner-application with valid auth creates draft partner application."""
        app_id = str(uuid.uuid4())
        payload_dict = {
            "event_id": app_id,
            "data": {
                "application_id": app_id,
                "business_name": "Ha Long Luxury Cruise JSC",
                "email": f"partner_{app_id[:6]}@halong.vn",
                "phone": "0909123456",
                "contact_person": "Nguyen Giam Doc",
                "business_license": "0109887766",
            },
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._sign_payload(body_bytes)

        response = self.url_open(
            "/api/v1/travel/partner-application",
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Signature-SHA256": signature,
                "Idempotency-Key": app_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("application_id"))
