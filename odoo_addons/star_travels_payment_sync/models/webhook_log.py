# -*- coding: utf-8 -*-
from odoo import fields, models


class StarTravelsWebhookLog(models.Model):
    _name = "star.travels.webhook.log"
    _description = "STAR Travels Webhook Idempotency & Audit Log"
    _order = "processed_at desc, id desc"

    event_id = fields.Char(
        string="Event ID",
        required=True,
        index=True,
        copy=False,
        help="Unique UUID idempotency key from Django webhook (Header Idempotency-Key or payload event_id)",
    )
    event_type = fields.Char(
        string="Event Type",
        required=True,
        index=True,
        help="Event action type (e.g. booking.paid, booking.refunded)",
    )
    payload = fields.Text(
        string="Raw JSON Payload",
        help="Full raw request body received from Django webhook",
    )
    processed_at = fields.Datetime(
        string="Processed At",
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )
    state = fields.Selection(
        [
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="success",
        required=True,
        index=True,
    )
    result_summary = fields.Text(
        string="Result JSON Summary",
        help="Cached JSON response payload returned to caller",
    )
    res_model = fields.Char(
        string="Related Model",
        help="Odoo model created or updated (e.g. sale.order, account.move)",
    )
    res_id = fields.Integer(
        string="Related Record ID",
        help="ID of record created or updated in Odoo",
    )

    _sql_constraints = [
        (
            "uniq_event_id",
            "unique(event_id)",
            "A webhook with this Event ID has already been recorded (Idempotency violation)!",
        ),
    ]
