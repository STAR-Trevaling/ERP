import json
import uuid

import pytest
import requests


@pytest.mark.e2e
def test_e2e_health_check_endpoint(odoo_url):
    """Verify integration health check probe returns 200 OK without authentication."""
    resp = requests.get(f"{odoo_url}/api/v1/travel/health", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"
    assert "Star Travels" in data.get("service", "")


@pytest.mark.e2e
def test_e2e_inquiry_with_valid_hmac(odoo_url, hmac_signer, odoo_rpc):
    """Verify live inquiry submission with HMAC-SHA256 signature creates crm.lead."""
    event_id = str(uuid.uuid4())
    test_phone = f"093{uuid.uuid4().hex[:7]}"
    payload = {
        "event_id": event_id,
        "event_type": "inquiry.created",
        "source": "website",
        "data": {
            "customer": {
                "name": "E2E Traveler Test",
                "phone": test_phone,
                "email": f"e2e_{event_id[:8]}@example.com",
            },
            "message": "Consultation request from E2E integration test suite.",
            "interest": {
                "traveler_count": 3,
            },
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac_signer(body_bytes)

    headers = {
        "Content-Type": "application/json",
        "X-Signature-SHA256": sig,
        "Idempotency-Key": event_id,
    }

    resp = requests.post(f"{odoo_url}/api/v1/travel/inquiry", data=body_bytes, headers=headers, timeout=10)
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json.get("success") is True
    lead_id = res_json.get("lead_id")
    assert lead_id

    # Verify through XML-RPC that lead is in Odoo database
    lead_records = odoo_rpc.execute("crm.lead", "read", [lead_id], ["name", "phone", "partner_id"])
    assert lead_records
    assert lead_records[0]["phone"] == test_phone


@pytest.mark.e2e
def test_e2e_inquiry_tampered_signature_rejected(odoo_url, hmac_signer):
    """Verify tampering with request body or signature fails with 401 Unauthorized."""
    event_id = str(uuid.uuid4())
    payload = {"event_id": event_id, "data": {"message": "Original"}}
    body_bytes = json.dumps(payload).encode("utf-8")
    valid_sig = hmac_signer(body_bytes)

    tampered_sig = valid_sig[:-4] + "0000"

    headers = {
        "Content-Type": "application/json",
        "X-Signature-SHA256": tampered_sig,
        "Idempotency-Key": event_id,
    }

    resp = requests.post(f"{odoo_url}/api/v1/travel/inquiry", data=body_bytes, headers=headers, timeout=5)
    assert resp.status_code == 401
    problem = resp.json()
    assert problem.get("title") == "Unauthorized"


@pytest.mark.e2e
def test_e2e_inquiry_idempotency_replay_protection(odoo_url, hmac_signer, odoo_rpc):
    """Verify duplicate submission returns cached response and never creates duplicate leads."""
    event_id = str(uuid.uuid4())
    test_phone = f"096{uuid.uuid4().hex[:7]}"
    payload = {
        "event_id": event_id,
        "data": {
            "customer": {
                "name": "Idempotent Tester",
                "phone": test_phone,
            },
            "message": "Testing duplicate delivery.",
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac_signer(body_bytes)

    headers = {
        "Content-Type": "application/json",
        "X-Signature-SHA256": sig,
        "Idempotency-Key": event_id,
    }

    # First attempt
    resp1 = requests.post(f"{odoo_url}/api/v1/travel/inquiry", data=body_bytes, headers=headers, timeout=10)
    assert resp1.status_code == 200
    lead_id_1 = resp1.json()["lead_id"]

    # Second attempt (Duplicate / Retry)
    resp2 = requests.post(f"{odoo_url}/api/v1/travel/inquiry", data=body_bytes, headers=headers, timeout=10)
    assert resp2.status_code == 200
    lead_id_2 = resp2.json()["lead_id"]

    assert lead_id_1 == lead_id_2

    # Verify only 1 lead in DB for this phone
    count = odoo_rpc.execute("crm.lead", "search_count", [("phone", "=", test_phone)])
    assert count == 1


@pytest.mark.e2e
def test_e2e_partner_application_submission(odoo_url, hmac_signer, odoo_rpc):
    """Verify partner onboarding application submission via API creates pending application."""
    app_id = str(uuid.uuid4())
    org_slug = f"tour-corp-{app_id[:6]}"
    payload = {
        "event_id": app_id,
        "data": {
            "application_id": app_id,
            "business_name": f"Tour Corp {org_slug}",
            "organization_slug": org_slug,
            "email": f"{org_slug}@partner.travel.vn",
            "phone": "0911223344",
            "contact_person": "Tran Truong Phong",
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac_signer(body_bytes)

    headers = {
        "Content-Type": "application/json",
        "X-Signature-SHA256": sig,
        "Idempotency-Key": app_id,
    }

    resp = requests.post(f"{odoo_url}/api/v1/travel/partner-application", data=body_bytes, headers=headers, timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    odoo_app_id = data.get("application_id")

    # Verify record in Odoo
    app_records = odoo_rpc.execute("travel.partner.application", "read", [odoo_app_id], ["state", "organization_slug"])
    assert app_records
    assert app_records[0]["state"] == "submitted"
    assert app_records[0]["organization_slug"] == org_slug
