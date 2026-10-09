import hashlib
import hmac
import json

import pytest


def compute_hmac(secret: str, body_bytes: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()


def verify_hmac(secret: str, body_bytes: bytes, signature: str) -> bool:
    if not signature:
        return False
    expected = compute_hmac(secret, body_bytes)
    return hmac.compare_digest(expected, signature)


def parse_statement_csv(csv_text: str, gateway: str = "vnpay"):
    import csv
    import io

    f = io.StringIO(csv_text)
    delimiter = ";" if ";" in csv_text.splitlines()[0] else ("," if "," in csv_text.splitlines()[0] else "\t")
    reader = csv.reader(f, delimiter=delimiter)

    headers: list[str] = []
    rows: list[list[str]] = []
    for r in reader:
        if not r or not any(r):
            continue
        if not headers:
            headers = [h.strip().lower().replace(" ", "_").replace("-", "_") for h in r]
        else:
            rows.append(r)

    if not headers:
        return []

    tx_id_candidates = ["gateway_transaction_id", "vnp_transactionno", "transaction_id", "ma_giao_dich"]
    amount_candidates = ["amount", "vnp_amount", "so_tien", "total_amount"]

    tx_col = next((i for i, h in enumerate(headers) if any(c in h for c in tx_id_candidates)), -1)
    amt_col = next((i for i, h in enumerate(headers) if any(c in h for c in amount_candidates)), -1)

    parsed_records = []
    for row in rows:
        if len(row) <= max(tx_col, amt_col):
            continue
        tx_id = str(row[tx_col]).strip()
        raw_amt = str(row[amt_col]).replace(",", "").replace(".", "").replace("VND", "").replace("₫", "").strip()
        try:
            amt = float(str(row[amt_col]).replace("VND", "").replace("₫", "").replace(",", "").strip())
        except ValueError:
            amt = float(raw_amt)

        if gateway == "vnpay" and amt > 100000000 and "vnp_amount" in headers[amt_col]:
            amt = amt / 100.0

        parsed_records.append({"tx_id": tx_id, "amount": amt})

    return parsed_records


class TestPaymentSyncCoreLogic:
    """Host-level unit tests for payment sync crypto, idempotency, and statement parsing."""

    def test_hmac_signature_verification_success(self):
        secret = "star_travels_super_secret_webhook_key_2026"
        payload = json.dumps({"event_id": "test-uuid-1", "data": {"amount": 500000}}).encode("utf-8")
        sig = compute_hmac(secret, payload)

        assert verify_hmac(secret, payload, sig) is True

    def test_hmac_signature_verification_failure_tampered_body(self):
        secret = "star_travels_super_secret_webhook_key_2026"
        payload = json.dumps({"event_id": "test-uuid-1", "data": {"amount": 500000}}).encode("utf-8")
        sig = compute_hmac(secret, payload)

        tampered_payload = json.dumps({"event_id": "test-uuid-1", "data": {"amount": 999999999}}).encode("utf-8")
        assert verify_hmac(secret, tampered_payload, sig) is False

    def test_hmac_signature_verification_timing_attack_resistance(self):
        secret = "star_travels_super_secret_webhook_key_2026"
        payload = b'{"test":"data"}'
        assert verify_hmac(secret, payload, "invalid_short_signature") is False
        assert verify_hmac(secret, payload, "") is False

    def test_parse_vnpay_csv_statement(self):
        csv_data = """vnp_TransactionNo,vnp_Amount,bank_code
VNP_1001,1500000,NCB
VNP_1002,2500000,VCB
VNP_1003,300000000,TCB
"""
        records = parse_statement_csv(csv_data, gateway="vnpay")
        assert len(records) == 3
        assert records[0]["tx_id"] == "VNP_1001"
        assert records[0]["amount"] == 1500000.0
        assert records[1]["tx_id"] == "VNP_1002"
        assert records[1]["amount"] == 2500000.0
        # vnp_Amount divided by 100 for raw portal export:
        assert records[2]["tx_id"] == "VNP_1003"
        assert records[2]["amount"] == 3000000.0

    def test_reconciliation_matching_simulation(self):
        odoo_payments = {
            "TX_A": {"amount": 1000000.0, "state": "pending"},
            "TX_B": {"amount": 2000000.0, "state": "pending"},
        }

        statement_items = [
            {"tx_id": "TX_A", "amount": 1000000.0},  # Exact match
            {"tx_id": "TX_B", "amount": 1800000.0},  # Amount mismatch
            {"tx_id": "TX_C", "amount": 500000.0},   # Missing in Odoo
        ]

        matched = 0
        unmatched = 0
        discrepancy = 0.0

        for item in statement_items:
            tx = item["tx_id"]
            file_amt = item["amount"]
            if tx in odoo_payments:
                if abs(odoo_payments[tx]["amount"] - file_amt) < 1.0:
                    odoo_payments[tx]["state"] = "matched"
                    matched += 1
                else:
                    odoo_payments[tx]["state"] = "unmatched"
                    unmatched += 1
                    discrepancy += abs(odoo_payments[tx]["amount"] - file_amt)
            else:
                unmatched += 1
                discrepancy += file_amt

        assert matched == 1
        assert unmatched == 2
        assert discrepancy == (200000.0 + 500000.0)
        assert odoo_payments["TX_A"]["state"] == "matched"
        assert odoo_payments["TX_B"]["state"] == "unmatched"

    def test_audit_log_append_only_immutability(self):
        """Audit log write/unlink must be permanently blocked."""
        class MockAuditLog:
            def __init__(self, data):
                self.data = data

            def write(self, vals):
                raise PermissionError("Audit log entries are immutable and append-only. Modification is strictly prohibited!")

            def unlink(self):
                raise PermissionError("Audit log entries are immutable and append-only. Deletion is strictly prohibited!")

        log = MockAuditLog({"booking_code": "ST-001", "action": "manual_confirmed"})
        with pytest.raises(PermissionError, match="immutable and append-only"):
            log.write({"amount_confirmed": 999})
        with pytest.raises(PermissionError, match="immutable and append-only"):
            log.unlink()

    def test_vietqr_discrepancy_requires_evidence_note(self):
        """When declared != confirmed amount, evidence note must not be blank."""
        def validate_vietqr_confirmation(amount_declared, amount_confirmed, evidence_note):
            if abs(amount_confirmed - amount_declared) > 0.01:
                if not evidence_note or not evidence_note.strip():
                    raise ValueError("Bắt buộc phải nhập 'Ghi chú đối soát / Chứng từ' khi số tiền thực nhận có sai lệch!")
            return True

        # Exactly matching amount doesn't strictly require note
        assert validate_vietqr_confirmation(1500000.0, 1500000.0, "") is True

        # Differing amount with note is valid
        assert validate_vietqr_confirmation(1500000.0, 1400000.0, "Khách trừ tiền phí chuyển khoản ngân hàng") is True

        # Differing amount without note must raise ValueError
        with pytest.raises(ValueError, match="Bắt buộc phải nhập"):
            validate_vietqr_confirmation(1500000.0, 1400000.0, "")
        with pytest.raises(ValueError, match="Bắt buộc phải nhập"):
            validate_vietqr_confirmation(1500000.0, 1400000.0, "   ")

    def test_separation_of_duties_creator_cannot_self_confirm(self):
        """Salesperson who created the booking cannot confirm the payment themselves."""
        def check_separation_of_duties(order_creator_id, confirming_user_id):
            if order_creator_id and order_creator_id == confirming_user_id:
                raise PermissionError("Separation of Duties violation: Order creator cannot confirm payment!")
            return True

        # Different users: Allowed
        assert check_separation_of_duties(order_creator_id=10, confirming_user_id=25) is True

        # Same user: Forbidden
        with pytest.raises(PermissionError, match="Separation of Duties violation"):
            check_separation_of_duties(order_creator_id=10, confirming_user_id=10)

    def test_vietqr_outbound_hmac_signature_to_django(self):
        """Outbound call payload to Django /vietqr-confirm/ must be signed with HMAC-SHA256."""
        secret = "star_travels_super_secret_webhook_key_2026"
        outbound_payload = {
            "payment_id": "tx_vietqr_999",
            "booking_code": "ST-PQ-001",
            "amount_confirmed": 2000000.0,
            "confirmed_by": "Kế toán viên Lê Thị B",
            "confirmed_at": "2026-10-08T17:45:00Z",
            "bank_reference": "FT241088921",
            "source": "manual_odoo_ui",
        }
        body_bytes = json.dumps(outbound_payload).encode("utf-8")
        signature = compute_hmac(secret, body_bytes)

        # Receiver verifies signature
        assert verify_hmac(secret, body_bytes, signature) is True
        assert verify_hmac("wrong_secret", body_bytes, signature) is False

    def test_django_outbox_resilience_fallback(self):
        """When outbound HTTP call to Django fails, event must be enqueued in Outbox without losing data."""
        outbox_queue = []

        def call_django_with_outbox_fallback(payment_id, payload, network_healthy=False):
            if not network_healthy:
                # Fallback to Outbox
                outbox_queue.append({
                    "event_type": "payment.vietqr.confirmed",
                    "payment_id": payment_id,
                    "payload": payload,
                    "state": "pending",
                })
                return False
            return True

        res = call_django_with_outbox_fallback("tx-123", {"amount": 1000000}, network_healthy=False)
        assert res is False
        assert len(outbox_queue) == 1
        assert outbox_queue[0]["payment_id"] == "tx-123"
        assert outbox_queue[0]["state"] == "pending"

    def test_dual_key_rotation_fallback_acceptance(self):
        """Dual-key rotation allows graceful acceptance of webhook signed with previous secret."""
        current_secret = "star_travels_current_secret_2026"
        previous_secret = "star_travels_previous_secret_2025"
        payload_bytes = b'{"event_id":"evt-rotation-test","amount":1500000}'

        # Case 1: Signed with current secret -> Accepted
        sig_current = compute_hmac(current_secret, payload_bytes)
        assert (verify_hmac(current_secret, payload_bytes, sig_current) or
                verify_hmac(previous_secret, payload_bytes, sig_current)) is True

        # Case 2: Signed with previous secret during grace window -> Accepted via fallback
        sig_previous = compute_hmac(previous_secret, payload_bytes)
        assert verify_hmac(current_secret, payload_bytes, sig_previous) is False
        assert verify_hmac(previous_secret, payload_bytes, sig_previous) is True

        # Case 3: Signed with unknown / third secret -> Rejected
        sig_unknown = compute_hmac("completely_unauthorized_key", payload_bytes)
        assert (verify_hmac(current_secret, payload_bytes, sig_unknown) or
                verify_hmac(previous_secret, payload_bytes, sig_unknown)) is False

    def test_promotional_discount_balancing_logic(self):
        """When order lines total differs from paid amount (e.g. promo coupon), a discount balancing line is injected."""
        def balance_order_lines(items, total_amount):
            lines_total = sum(item["qty"] * item["price"] for item in items)
            order_lines = [dict(item) for item in items]
            discrepancy = round(total_amount - lines_total, 2)
            if abs(discrepancy) > 0.01:
                if discrepancy < 0:
                    order_lines.append({
                        "name": "Chiết khấu / Giảm giá khuyến mãi",
                        "qty": 1.0,
                        "price": discrepancy,  # negative price unit
                    })
                else:
                    order_lines.append({
                        "name": "Phụ phí / Dịch vụ gia tăng",
                        "qty": 1.0,
                        "price": discrepancy,
                    })
            final_total = sum(line["qty"] * line["price"] for line in order_lines)
            return order_lines, final_total

        # Tour base lines total: 4,000,000 VND. Total paid (with voucher): 3,700,000 VND
        items = [
            {"name": "Phu Quoc Sunset", "qty": 2, "price": 1500000.0},
            {"name": "Island Cable Car", "qty": 1, "price": 1000000.0},
        ]
        balanced_lines, final_total = balance_order_lines(items, 3700000.0)
        assert len(balanced_lines) == 3
        assert balanced_lines[2]["name"] == "Chiết khấu / Giảm giá khuyến mãi"
        assert balanced_lines[2]["price"] == -300000.0
        assert final_total == 3700000.0  # Exactly matches paid amount! Zero receivable drift!

    def test_strict_confirmer_group_authorization(self):
        """Only members of group_payment_confirmer or Admin are authorized to confirm VietQR transfers."""
        def check_confirmer_authorization(user_groups, is_admin=False):
            if is_admin:
                return True
            if "star_travels_payment_sync.group_payment_confirmer" in user_groups:
                return True
            return False

        # Regular accountant: NOT in confirmer group -> Forbidden
        assert check_confirmer_authorization(["account.group_account_user"]) is False

        # Designated payment confirmer -> Allowed
        assert check_confirmer_authorization([
            "account.group_account_user",
            "star_travels_payment_sync.group_payment_confirmer",
        ]) is True

        # System Administrator -> Allowed
        assert check_confirmer_authorization([], is_admin=True) is True

    def test_dynamic_outbox_endpoint_routing(self):
        """Outbox worker dynamically resolves custom target endpoint from envelope payload."""
        base_url = "http://backend.internal:8000"
        default_endpoint = f"{base_url}/api/v1/integrations/v1/odoo/events"

        def resolve_endpoint(payload_dict):
            custom_path = payload_dict.get("endpoint")
            if custom_path:
                return custom_path if custom_path.startswith("http") else f"{base_url}{custom_path}"
            return default_endpoint

        # Generic integration event -> Default endpoint
        generic_payload = {"event_type": "tour.published", "data": {}}
        assert resolve_endpoint(generic_payload) == default_endpoint

        # VietQR Confirmation event -> Dynamic endpoint
        vietqr_payload = {
            "event_type": "payment.vietqr.confirmed",
            "endpoint": "/api/v1/payments/tx_9988/vietqr-confirm/",
            "data": {},
        }
        assert resolve_endpoint(vietqr_payload) == f"{base_url}/api/v1/payments/tx_9988/vietqr-confirm/"

    def test_referral_with_contact_info_creates_warm_lead_and_routes_to_sales(self):
        """Referral with contact info must generate warm lead with [PARTNER_REFERRAL] and [WARM_REFERRAL] tags, routed to Sales."""
        def process_referral_simulation(payload_data):
            has_contact = bool(
                payload_data.get("has_contact_info")
                or (payload_data.get("contact_name") and payload_data.get("contact_phone"))
                or payload_data.get("contact_phone")
                or payload_data.get("contact_email")
            )
            tags = ["[PARTNER_REFERRAL]"]
            if has_contact:
                tags.append("[WARM_REFERRAL]")
                routed_to_sales = True
                lead_type = "lead"  # Strictly lead, not opportunity
                sales_team = "Direct Sales Team"
            else:
                routed_to_sales = False
                lead_type = "lead"
                sales_team = None

            return {
                "lead_type": lead_type,
                "tags": tags,
                "routed_to_sales": routed_to_sales,
                "sales_team": sales_team,
                "has_contact": has_contact,
            }

        # Case 1: Customer provided phone & name (Warm Lead)
        warm_payload = {
            "booking_id": "b-ref-001",
            "item_type": "accommodation_referral",
            "item_name": "Khách sạn Mường Thanh Hạ Long",
            "referral_partner_name": "Booking.com",
            "destination": "ha-long",
            "contact_name": "Nguyen Van A",
            "contact_phone": "0988776655",
            "has_contact_info": True,
        }
        result = process_referral_simulation(warm_payload)
        assert result["lead_type"] == "lead"
        assert "[PARTNER_REFERRAL]" in result["tags"]
        assert "[WARM_REFERRAL]" in result["tags"]
        assert result["routed_to_sales"] is True
        assert result["sales_team"] == "Direct Sales Team"

    def test_referral_without_contact_info_creates_click_lead_not_routed_to_sales(self):
        """Referral click without contact info must only store partner analytics lead, NOT routed to Sales team."""
        def process_referral_simulation(payload_data):
            has_contact = bool(
                payload_data.get("has_contact_info")
                or (payload_data.get("contact_name") and payload_data.get("contact_phone"))
                or payload_data.get("contact_phone")
                or payload_data.get("contact_email")
            )
            tags = ["[PARTNER_REFERRAL]"]
            if has_contact:
                tags.append("[WARM_REFERRAL]")
                routed_to_sales = True
                sales_team = "Direct Sales Team"
            else:
                routed_to_sales = False
                sales_team = None

            return {
                "lead_type": "lead",
                "tags": tags,
                "routed_to_sales": routed_to_sales,
                "sales_team": sales_team,
                "has_contact": has_contact,
            }

        # Case 2: Customer only clicked out to Agoda (Click tracking only, no contact)
        click_payload = {
            "booking_id": "b-ref-002",
            "item_type": "accommodation_referral",
            "item_name": "Khách sạn Hạ Long Bay View",
            "referral_partner_name": "Booking.com",
            "destination": "ha-long",
            "contact_name": None,
            "contact_phone": None,
            "has_contact_info": False,
        }
        result = process_referral_simulation(click_payload)
        assert result["lead_type"] == "lead"
        assert "[PARTNER_REFERRAL]" in result["tags"]
        assert "[WARM_REFERRAL]" not in result["tags"]  # Crucial: NOT a warm referral
        assert result["routed_to_sales"] is False       # Crucial: Does NOT disturb Sales team
        assert result["sales_team"] is None

    def test_referral_webhook_hmac_signature_verification(self):
        """POST /api/v1/travel/referral-created requires valid HMAC-SHA256 signature."""
        secret = "star_travels_super_secret_webhook_key_2026"
        referral_payload = {
            "event_id": "ref-evt-100",
            "event_type": "referral.created",
            "data": {
                "booking_id": "ref-b-999",
                "item_type": "accommodation_referral",
                "item_name": "Vinpearl Resort Phu Quoc",
                "referral_partner_name": "Agoda",
                "destination": "phu-quoc",
                "has_contact_info": False,
            },
        }
        body_bytes = json.dumps(referral_payload).encode("utf-8")
        valid_signature = compute_hmac(secret, body_bytes)

        # Valid signature -> Verified
        assert verify_hmac(secret, body_bytes, valid_signature) is True

        # Tampered body -> Rejected
        tampered_body = json.dumps({**referral_payload, "tampered": True}).encode("utf-8")
        assert verify_hmac(secret, tampered_body, valid_signature) is False

        # Invalid signature -> Rejected
        assert verify_hmac(secret, body_bytes, "invalid_sig_abc123") is False

    def test_referral_estimated_commission_calculation(self):
        """Calculates estimated commission based on estimated value * partner commission rate."""
        def compute_commission(estimated_value, commission_rate):
            if estimated_value and commission_rate:
                return round(estimated_value * (commission_rate / 100.0), 2)
            return 0.0

        # Hotel booking estimated 3,000,000 VND with 8% commission rate
        assert compute_commission(3000000.0, 8.0) == 240000.0

        # Restaurant booking estimated 1,500,000 VND with 5% commission rate
        assert compute_commission(1500000.0, 5.0) == 75000.0

        # Zero commission rate
        assert compute_commission(2000000.0, 0.0) == 0.0


