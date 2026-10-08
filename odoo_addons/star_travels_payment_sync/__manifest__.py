# -*- coding: utf-8 -*-
{
    "name": "Star Travels - Payment & Reconciliation Sync",
    "version": "18.0.1.0.0",
    "category": "Accounting/Travel",
    "summary": "Automated booking payment & refund webhook sync, VietQR manual confirmation with append-only audit trail, and VNPay reconciliation",
    "description": """
Star Travels Payment & Reconciliation Sync
==========================================
- Inbound Webhook controller for payment and refund events:
  * POST /api/v1/travel/booking-paid
  * POST /api/v1/travel/booking-refunded
  * POST /api/v1/travel/payment-pending (VietQR queue ingestion)
- VietQR Manual Bank Transfer Confirmation Workflow:
  * Inbound pending payment queue with customer & transfer content details.
  * Confirmation Wizard with Separation of Duties (SoD) enforcement.
  * Mandatory evidence justification if declared amount != confirmed amount.
  * Outbound notification to Django (POST /api/v1/payments/{id}/vietqr-confirm/) with HMAC-SHA256 signature and resilient Transactional Outbox retry fallback.
- Append-Only Payment Audit Trail (star.travels.payment.audit.log):
  * Hard immutability constraints blocking write() and unlink() even for administrators.
  * Full traceability of all state transitions, amounts, users, and evidence notes.
  * Direct Excel/CSV export action for compliance and internal auditing.
- Timing-safe HMAC-SHA256 signature verification & Bearer/API Key security matching `travel_integration`.
- Strictly idempotent event processing via `star.travels.webhook.log`.
- End-to-end automated ERP accounting flow:
  1. Find or create traveler partner (res.partner).
  2. Create & confirm Sale Order (sale.order).
  3. Create & post Customer Invoice (account.move).
  4. Create & post Payment (account.payment) in dedicated gateway journals (VNPay, MoMo, ZaloPay, VietQR).
  5. Automatically reconcile payment lines against invoice receivable lines.
- Refund processing:
  * Create posted Credit Note (account.move out_refund) linked to original invoice.
  * Create outbound payment and reconcile against credit note.
- VNPay Statement Reconciliation Wizard (star.travels.reconciliation.wizard):
  * Import CSV/Excel settlement statements.
  * Auto-match gateway transaction IDs and amounts.
  * Update payment reconciliation state (matched / unmatched).
  * Report discrepancy metrics and status summary.
- Scheduled Actions alerting accountants of unmatched payments (> 2 days) and stale pending VietQR transfers (> 4 hours).
    """,
    "author": "Star Travels ERP Architect",
    "website": "https://star-travels.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale",
        "account",
        "travel_core",
        "travel_integration",
        "travel_cms",
    ],
    "data": [
        "security/payment_security.xml",
        "security/ir.model.access.csv",
        "data/account_journal_data.xml",
        "data/ir_cron_data.xml",
        "views/account_payment_views.xml",
        "views/webhook_log_views.xml",
        "views/reconciliation_wizard_views.xml",
        "views/payment_pending_views.xml",
        "views/payment_audit_log_views.xml",
        "views/vietqr_confirm_wizard_views.xml",
        "views/vietqr_reject_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
