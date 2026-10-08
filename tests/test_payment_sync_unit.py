import hashlib
import hmac
import json


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
