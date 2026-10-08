# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_star_booking_id = fields.Char(
        string="STAR Booking UUID",
        copy=False,
        index=True,
        help="UUID identifier of booking in external Django backend",
    )
    x_star_booking_code = fields.Char(
        string="STAR Booking Code",
        index=True,
        copy=False,
        help="Human-readable booking reference code (e.g. ST-202610-001)",
    )
