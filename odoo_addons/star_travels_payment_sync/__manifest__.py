# -*- coding: utf-8 -*-
{
    "name": "Star Travels - Payment & Reconciliation Sync",
    "version": "18.0.1.0.0",
    "category": "Accounting/Travel",
    "summary": "Automated booking payment & refund webhook sync and VNPay/MoMo statement reconciliation",
    "description": """
Star Travels Payment & Reconciliation Sync
==========================================
- Inbound Webhook controller for payment and refund events:
  * POST /api/v1/travel/booking-paid
  * POST /api/v1/travel/booking-refunded
- Timing-safe HMAC-SHA256 signature verification & Bearer/API Key security matching `travel_integration`.
- Strictly idempotent event processing via `star.travels.webhook.log`.
- End-to-end automated ERP accounting flow:
  1. Find or create traveler partner (res.partner).
  2. Create & confirm Sale Order (sale.order).
  3. Create & post Customer Invoice (account.move).
  4. Create & post Payment (account.payment) in dedicated gateway journals (VNPay, MoMo, ZaloPay).
  5. Automatically reconcile payment lines against invoice receivable lines.
- Refund processing:
  * Create posted Credit Note (account.move out_refund) linked to original invoice.
  * Create outbound payment and reconcile against credit note.
- Statement Reconciliation Wizard (star.travels.reconciliation.wizard):
  * Import CSV/Excel settlement statements.
  * Auto-match gateway transaction IDs and amounts.
  * Update payment reconciliation state (matched / unmatched).
  * Report discrepancy metrics and status summary.
- Scheduled Action alerting accountants of unmatched payments (> 2 days).
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
        "security/ir.model.access.csv",
        "data/account_journal_data.xml",
        "data/ir_cron_data.xml",
        "views/account_payment_views.xml",
        "views/webhook_log_views.xml",
        "views/reconciliation_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
