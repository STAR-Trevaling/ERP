# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import uuid

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestStarTravelsPaymentWebhook(HttpCase):
    """
    Enterprise-grade test suite for star_travels_payment_sync module:
    1. Valid booking.paid webhook creates Sale Order, posted Customer Invoice, and reconciled Payment.
    2. Invalid HMAC-SHA256 signature is rejected with HTTP 401 Problem Details.
    3. Duplicate event_id triggers idempotency protection (returns cached response, no duplicate order).
    4. Valid booking.refunded webhook creates Credit Note (out_refund) linked to invoice and outbound payment.
    5. Reconciliation Wizard processes CSV statements and matches payments correctly.
    """

    def setUp(self):
        super().setUp()
        self.secret = "star_travels_super_secret_webhook_key_2026"
        self.api_key = "star_travels_inbound_api_token_2026"

        self.env["ir.config_parameter"].sudo().set_param(
            "travel.webhook_secret", self.secret
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "travel.inbound_api_key", self.api_key
        )

        # Ensure gateway journal exists
        self.company = self.env.company
        self.journal_vnpay = self.env["account.journal"].search([
            ("code", "=", "VNPAY"),
            ("company_id", "=", self.company.id),
        ], limit=1)
        if not self.journal_vnpay:
            self.journal_vnpay = self.env["account.journal"].create({
                "name": "VNPay Test Gateway",
                "code": "VNPAY",
                "type": "bank",
                "company_id": self.company.id,
            })

    def _sign_payload(self, body_bytes: bytes) -> str:
        return hmac.new(self.secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    def test_booking_paid_invalid_signature_rejected(self):
        """Invalid HMAC-SHA256 signature must return HTTP 401 Problem Details."""
        payload = json.dumps({"test": "tampered_data"}).encode("utf-8")
        response = self.url_open(
            "/api/v1/travel/booking-paid",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Signature-SHA256": "bad_signature_hex_00000000000000000000000000",
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        self.assertEqual(response.status_code, 401)
        res_json = response.json()
        self.assertEqual(res_json.get("title"), "Unauthorized")

    def test_booking_paid_valid_creates_so_invoice_and_reconciled_payment(self):
        """Valid webhook creates Sale Order, posted Customer Invoice, and reconciled Payment."""
        event_id = str(uuid.uuid4())
        booking_uuid = str(uuid.uuid4())
        booking_code = f"ST-{uuid.uuid4().hex[:6].upper()}"
        gateway_tx_id = f"VNPAY-{uuid.uuid4().hex[:8]}"

        payload_dict = {
            "event_id": event_id,
            "event_type": "booking.paid",
            "source": "public-platform",
            "data": {
                "booking_id": booking_uuid,
                "booking_code": booking_code,
                "customer": {
                    "name": "Nguyen Van Du Khach",
                    "email": f"traveler_{event_id[:8]}@example.com",
                    "phone": "0912345678",
                },
                "items": [
                    {
                        "tour_slug": "phu-quoc-sunset",
                        "title": "Tour Phu Quoc Sunset Cruise",
                        "adults": 2,
                        "children": 1,
                        "price_adult": 1500000.0,
                        "price_child": 1000000.0,
                    }
                ],
                "payment": {
                    "gateway": "vnpay",
                    "gateway_transaction_id": gateway_tx_id,
                    "amount": 4000000.0,
                },
            },
        }

        body_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._sign_payload(body_bytes)

        response = self.url_open(
            "/api/v1/travel/booking-paid",
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
        self.assertTrue(data.get("odoo_sale_order_id"))
        self.assertTrue(data.get("odoo_invoice_id"))
        self.assertTrue(data.get("odoo_payment_id"))

        # Verify Sale Order in Odoo
        so = self.env["sale.order"].sudo().browse(data["odoo_sale_order_id"])
        self.assertEqual(so.state, "sale")
        self.assertEqual(so.x_star_booking_id, booking_uuid)
        self.assertEqual(so.x_star_booking_code, booking_code)

        # Verify Invoice in Odoo
        inv = self.env["account.move"].sudo().browse(data["odoo_invoice_id"])
        self.assertEqual(inv.state, "posted")
        self.assertEqual(inv.move_type, "out_invoice")

        # Verify Payment & Reconciliation
        payment = self.env["account.payment"].sudo().browse(data["odoo_payment_id"])
        self.assertEqual(payment.state, "posted")
        self.assertEqual(payment.x_gateway, "vnpay")
        self.assertEqual(payment.x_gateway_transaction_id, gateway_tx_id)
        self.assertEqual(payment.x_reconciliation_state, "pending")
        self.assertEqual(payment.amount, 4000000.0)

        # Verify Invoice is reconciled (payment_state in in_payment or paid)
        self.assertIn(inv.payment_state, ("in_payment", "paid"))

    def test_booking_paid_duplicate_event_id_idempotency(self):
        """Second webhook with same event_id returns cached response without duplicate order."""
        event_id = str(uuid.uuid4())
        booking_uuid = str(uuid.uuid4())
        booking_code = f"ST-{uuid.uuid4().hex[:6].upper()}"

        payload_dict = {
            "event_id": event_id,
            "event_type": "booking.paid",
            "data": {
                "booking_id": booking_uuid,
                "booking_code": booking_code,
                "customer": {
                    "name": "Tran Thi Test",
                    "email": f"test_{event_id[:8]}@example.com",
                    "phone": "0987654321",
                },
                "payment": {
                    "gateway": "momo",
                    "gateway_transaction_id": f"MOMO-{uuid.uuid4().hex[:8]}",
                    "amount": 2500000.0,
                },
            },
        }

        body_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = self._sign_payload(body_bytes)
        headers = {
            "Content-Type": "application/json",
            "X-Signature-SHA256": signature,
            "Idempotency-Key": event_id,
        }

        # 1. First invocation
        resp1 = self.url_open("/api/v1/travel/booking-paid", data=body_bytes, headers=headers)
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertTrue(data1.get("odoo_sale_order_id"))

        # 2. Second invocation (network retry)
        resp2 = self.url_open("/api/v1/travel/booking-paid", data=body_bytes, headers=headers)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()

        self.assertEqual(data1.get("odoo_sale_order_id"), data2.get("odoo_sale_order_id"))
        self.assertEqual(data1.get("odoo_invoice_id"), data2.get("odoo_invoice_id"))

        # Verify only 1 sale order exists with this booking id
        orders = self.env["sale.order"].sudo().search([("x_star_booking_id", "=", booking_uuid)])
        self.assertEqual(len(orders), 1)

    def test_booking_refund_creates_credit_note_and_payment(self):
        """Refund webhook creates posted Credit Note linked to original invoice and outbound payment."""
        # Setup: First create an original paid booking
        event_paid = str(uuid.uuid4())
        booking_uuid = str(uuid.uuid4())
        booking_code = f"ST-RF-{uuid.uuid4().hex[:6].upper()}"

        paid_payload = {
            "event_id": event_paid,
            "event_type": "booking.paid",
            "data": {
                "booking_id": booking_uuid,
                "booking_code": booking_code,
                "customer": {
                    "name": "Refund Customer",
                    "email": f"refund_{event_paid[:8]}@example.com",
                    "phone": "0901234567",
                },
                "payment": {
                    "gateway": "vnpay",
                    "gateway_transaction_id": f"TX-ORIG-{event_paid[:8]}",
                    "amount": 2000000.0,
                },
            },
        }
        body_paid = json.dumps(paid_payload).encode("utf-8")
        resp_paid = self.url_open(
            "/api/v1/travel/booking-paid",
            data=body_paid,
            headers={
                "Content-Type": "application/json",
                "X-Signature-SHA256": self._sign_payload(body_paid),
                "Idempotency-Key": event_paid,
            },
        )
        self.assertEqual(resp_paid.status_code, 200)
        orig_invoice_id = resp_paid.json()["odoo_invoice_id"]

        # Now execute refund webhook
        event_refund = str(uuid.uuid4())
        refund_tx_id = f"RF-{uuid.uuid4().hex[:8]}"
        refund_payload = {
            "event_id": event_refund,
            "event_type": "booking.refunded",
            "data": {
                "booking_id": booking_uuid,
                "refund_amount": 1000000.0,  # Partial refund
                "reason": "Khách hủy vé trước ngày khởi hành 7 ngày",
                "refund_transaction_id": refund_tx_id,
                "gateway": "vnpay",
            },
        }

        body_refund = json.dumps(refund_payload).encode("utf-8")
        resp_refund = self.url_open(
            "/api/v1/travel/booking-refunded",
            data=body_refund,
            headers={
                "Content-Type": "application/json",
                "X-Signature-SHA256": self._sign_payload(body_refund),
                "Idempotency-Key": event_refund,
            },
        )
        self.assertEqual(resp_refund.status_code, 200)
        refund_data = resp_refund.json()
        self.assertTrue(refund_data.get("success"))
        self.assertTrue(refund_data.get("odoo_refund_id"))
        self.assertTrue(refund_data.get("odoo_payment_id"))

        # Verify Credit Note
        credit_note = self.env["account.move"].sudo().browse(refund_data["odoo_refund_id"])
        self.assertEqual(credit_note.move_type, "out_refund")
        self.assertEqual(credit_note.state, "posted")
        self.assertEqual(credit_note.reversed_entry_id.id, orig_invoice_id)
        self.assertEqual(credit_note.amount_total, 1000000.0)

        # Verify Outbound Payment
        outbound_payment = self.env["account.payment"].sudo().browse(refund_data["odoo_payment_id"])
        self.assertEqual(outbound_payment.payment_type, "outbound")
        self.assertEqual(outbound_payment.state, "posted")
        self.assertEqual(outbound_payment.amount, 1000000.0)

    def test_reconciliation_wizard_csv_matching(self):
        """Reconciliation Wizard parses CSV statements and matches payments accurately."""
        # Create a test payment in Odoo
        tx_id_matched = f"VNP-MATCH-{uuid.uuid4().hex[:6]}"
        tx_id_diff = f"VNP-DIFF-{uuid.uuid4().hex[:6]}"

        partner = self.env["res.partner"].create({"name": "Recon Test Partner"})
        pay1 = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": partner.id,
            "amount": 1800000.0,
            "journal_id": self.journal_vnpay.id,
            "x_gateway": "vnpay",
            "x_gateway_transaction_id": tx_id_matched,
            "x_reconciliation_state": "pending",
        })
        pay1.action_post()

        pay2 = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": partner.id,
            "amount": 2500000.0,
            "journal_id": self.journal_vnpay.id,
            "x_gateway": "vnpay",
            "x_gateway_transaction_id": tx_id_diff,
            "x_reconciliation_state": "pending",
        })
        pay2.action_post()

        # Generate CSV statement file
        csv_content = f"""gateway_transaction_id,amount,bank_code
{tx_id_matched},1800000,NCB
{tx_id_diff},2000000,VCB
VNP-UNKNOWN-999,500000,TCB
"""
        csv_b64 = base64.b64encode(csv_content.encode("utf-8"))

        wizard = self.env["star.travels.reconciliation.wizard"].create({
            "statement_file": csv_b64,
            "filename": "vnpay_statement_sample.csv",
            "gateway": "vnpay",
        })

        wizard.action_process_reconciliation()

        self.assertEqual(wizard.state, "done")
        self.assertEqual(wizard.total_rows, 3)
        self.assertEqual(wizard.matched_count, 1)
        self.assertEqual(wizard.unmatched_count, 2)

        # Verify pay1 is now matched, pay2 is unmatched
        self.assertEqual(pay1.x_reconciliation_state, "matched")
        self.assertEqual(pay2.x_reconciliation_state, "unmatched")
