#!/usr/bin/env python3
"""
Star Travels ERP — Safe Mock Data Cleanup Utility
Purges Odoo Core demo leads, demo partners, and transient test artifacts
while strictly preserving administrative, internal staff, and Star Travels domain records.
"""
import sys
import xmlrpc.client

sys.stdout.reconfigure(encoding="utf-8")

URL = "http://localhost:8069"
DB = "odoo_travel"
USER = "admin"
PASSWORD = "admin"

PROTECTED_EMAILS = [
    "admin@example.com",
    "info@yourcompany.com",
    "nam.nguyen@startravels.vn",
    "tuan.hoang@gmail.com",
    "livesync@test.vn",
]


def clean_mock_data():
    print(f"Connecting to Odoo at {URL} (Database: {DB})...")
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, USER, PASSWORD, {})
    if not uid:
        print("Failed to authenticate with Odoo.")
        return

    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
    print("Authentication successful as UID:", uid)

    # -------------------------------------------------------------
    # 1. PURGE DEMO & TRANSIENT CRM LEADS
    # -------------------------------------------------------------
    print("\n--- 1. Rà soát và Dọn dẹp CRM Leads ---")
    # Identify Odoo core demo leads via ir.model.data
    demo_lead_data = models.execute_kw(
        DB, uid, PASSWORD, "ir.model.data", "search_read",
        [[("model", "=", "crm.lead"), ("module", "=", "crm"), ("name", "=like", "crm_case_%")]],
        {"fields": ["res_id", "name"]}
    )
    demo_lead_ids = [d["res_id"] for d in demo_lead_data if d.get("res_id")]

    # Identify transient test leads from automated tests
    test_lead_ids = models.execute_kw(
        DB, uid, PASSWORD, "crm.lead", "search",
        [[
            "|",
            ("name", "ilike", "E2E Traveler Test"),
            ("name", "ilike", "Idempotent Tester")
        ]]
    )

    lead_ids_to_remove = list(set(demo_lead_ids + test_lead_ids))
    print(f"Phát hiện {len(demo_lead_ids)} leads demo Odoo và {len(test_lead_ids)} leads thử nghiệm.")

    if lead_ids_to_remove:
        # Check that we do not delete live sync lead
        live_leads = models.execute_kw(
            DB, uid, PASSWORD, "crm.lead", "search",
            [[("phone", "=", "0988776655")]]
        )
        safe_lead_ids = [lid for lid in lead_ids_to_remove if lid not in live_leads]

        models.execute_kw(DB, uid, PASSWORD, "crm.lead", "unlink", [safe_lead_ids])
        print(f"-> Đã xóa sạch {len(safe_lead_ids)} CRM leads không liên quan.")

        # Clean ir.model.data entries for deleted leads
        ir_lead_ids = [d["id"] for d in demo_lead_data]
        if ir_lead_ids:
            models.execute_kw(DB, uid, PASSWORD, "ir.model.data", "unlink", [ir_lead_ids])
            print(f"-> Đã gỡ bỏ {len(ir_lead_ids)} bản ghi demo trong ir.model.data.")

    # -------------------------------------------------------------
    # 2. PURGE DEMO & TRANSIENT CONTACTS (RES.PARTNER)
    # -------------------------------------------------------------
    print("\n--- 2. Rà soát và Dọn dẹp Contacts (res.partner) ---")
    # Identify Odoo core demo partners via ir.model.data
    demo_partner_data = models.execute_kw(
        DB, uid, PASSWORD, "ir.model.data", "search_read",
        [[("model", "=", "res.partner"), ("module", "=", "base"), ("name", "=like", "res_partner_%")]],
        {"fields": ["res_id", "name"]}
    )
    demo_partner_ids = [d["res_id"] for d in demo_partner_data if d.get("res_id")]

    # Identify transient test partners
    test_partner_ids = models.execute_kw(
        DB, uid, PASSWORD, "res.partner", "search",
        [[
            "|", "|",
            ("name", "ilike", "E2E Traveler Test"),
            ("name", "ilike", "Idempotent Tester"),
            ("name", "ilike", "Công ty Du lịch E2E")
        ]]
    )

    partner_ids_candidates = list(set(demo_partner_ids + test_partner_ids))

    # Strict protection whitelist
    protected_partners = models.execute_kw(
        DB, uid, PASSWORD, "res.partner", "search",
        [[
            "|", "|",
            ("id", "in", [1, 2, 3]),
            ("email", "in", PROTECTED_EMAILS),
            ("phone", "=", "0988776655")
        ]]
    )
    # Also protect any partner linked to travel.partner.application
    app_partner_ids = []
    apps = models.execute_kw(
        DB, uid, PASSWORD, "travel.partner.application", "search_read",
        [[("partner_id", "!=", False)]],
        {"fields": ["partner_id"]}
    )
    for a in apps:
        if a.get("partner_id"):
            app_partner_ids.append(a["partner_id"][0])

    protected_set = set(protected_partners + app_partner_ids)
    safe_partner_ids = [pid for pid in partner_ids_candidates if pid not in protected_set]
    print(f"Phát hiện {len(safe_partner_ids)} đối tác demo/thử nghiệm đủ điều kiện dọn dẹp.")

    deleted_count = 0
    archived_count = 0
    for pid in safe_partner_ids:
        try:
            models.execute_kw(DB, uid, PASSWORD, "res.partner", "unlink", [[pid]])
            deleted_count += 1
        except Exception:
            # If partner is referenced by internal logs/history, safely archive it
            try:
                models.execute_kw(DB, uid, PASSWORD, "res.partner", "write", [[pid], {"active": False}])
                archived_count += 1
            except Exception:
                pass

    print(f"-> Đã xóa trực tiếp: {deleted_count} contacts.")
    if archived_count:
        print(f"-> Đã ẩn (archive) an toàn: {archived_count} contacts do có ràng buộc lịch sử.")

    # -------------------------------------------------------------
    # 3. KIỂM TRA HIỆN TRẠNG SAU KHI DỌN DẸP
    # -------------------------------------------------------------
    remaining_leads = models.execute_kw(DB, uid, PASSWORD, "crm.lead", "search_read", [[]], {"fields": ["id", "name", "phone", "email_from"]})
    remaining_partners = models.execute_kw(DB, uid, PASSWORD, "res.partner", "search_read", [[("active", "=", True)]], {"fields": ["id", "name", "email", "phone", "is_company"]})

    print("\n================= HIỆN TRẠNG SAU KHI DỌN DẸP =================")
    print(f"Tổng CRM Leads du lịch thực còn lại: {len(remaining_leads)}")
    for lead_rec in remaining_leads:
        print(f"  - Lead [{lead_rec['id']}]: {lead_rec['name']} | SĐT: {lead_rec['phone']} | Email: {lead_rec['email_from']}")

    print(f"\nTổng Contacts hoạt động (res.partner) còn lại: {len(remaining_partners)}")
    for p in remaining_partners:
        print(f"  - Contact [{p['id']}]: {p['name']} | Email: {p['email']} | Doanh nghiệp: {p['is_company']}")
    print("=============================================================")


if __name__ == "__main__":
    clean_mock_data()
