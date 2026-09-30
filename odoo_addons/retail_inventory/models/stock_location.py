# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_retail_store = fields.Boolean(
        string="Is Retail Store Location",
        default=False,
        help="Indicates whether this location represents an omnichannel retail shop floor or store."
    )
    safety_buffer_pct = fields.Float(
        string="Safety Buffer (%)",
        default=0.0,
        help="Percentage of on-hand inventory reserved as safety buffer to prevent store vs online overselling."
    )
