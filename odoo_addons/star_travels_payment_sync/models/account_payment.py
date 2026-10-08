# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    x_gateway = fields.Selection(
        [
            ("vnpay", "VNPay"),
            ("momo", "MoMo"),
            ("zalopay", "ZaloPay"),
            ("stripe", "Stripe"),
        ],
        string="Payment Gateway",
        index=True,
        tracking=True,
        help="Third-party payment gateway used by traveler",
    )
    x_gateway_transaction_id = fields.Char(
        string="Gateway Transaction ID",
        index=True,
        copy=False,
        tracking=True,
        help="Transaction reference code from payment gateway (VNPay/MoMo/ZaloPay)",
    )
    x_reconciliation_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("matched", "Matched"),
            ("unmatched", "Unmatched"),
        ],
        string="Reconciliation State",
        default="pending",
        required=True,
        index=True,
        tracking=True,
        help="State of settlement reconciliation against bank/gateway statement",
    )

    @api.model
    def cron_check_unmatched_payments(self):
        """
        Scheduled action (Daily):
        Identifies unmatched payment transactions older than 2 days
        and alerts the accounting team via chatter activities / system logs.
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=2)
        unmatched_payments = self.search([
            ("x_reconciliation_state", "=", "unmatched"),
            ("create_date", "<=", cutoff_date),
            ("state", "=", "posted"),
        ])

        if not unmatched_payments:
            _logger.info("STAR Travels Payment Reconciliation Cron: No stale unmatched payments found.")
            return True

        _logger.warning(
            "STAR Travels Payment Reconciliation Cron: Found %d unmatched payment(s) older than 2 days!",
            len(unmatched_payments),
        )

        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        accountant_group = self.env.ref("account.group_account_user", raise_if_not_found=False)
        manager = accountant_group.users[0] if (accountant_group and accountant_group.users) else self.env.user

        for payment in unmatched_payments:
            existing_activity = self.env["mail.activity"].search([
                ("res_model", "=", "account.payment"),
                ("res_id", "=", payment.id),
                ("summary", "ilike", "Unmatched Gateway Payment Alert"),
            ], limit=1)

            if not existing_activity and activity_type:
                payment.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary="[STAR Travels] Unmatched Gateway Payment Alert (> 2 days)",
                    note=(
                        f"Payment reference {payment.name} (Amount: {payment.amount} {payment.currency_id.name}) "
                        f"for Gateway {payment.x_gateway or 'N/A'} "
                        f"(Transaction ID: {payment.x_gateway_transaction_id or 'N/A'}) "
                        "has been marked UNMATCHED during statement reconciliation for more than 48 hours. "
                        "Please verify with the gateway portal."
                    ),
                    user_id=manager.id,
                )

        return True
