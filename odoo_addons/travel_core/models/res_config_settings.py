# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    travel_public_platform_url = fields.Char(
        string="Public Platform Base URL",
        config_parameter='travel.public_platform_url',
        default="http://localhost:8000",
        help="Base URL of the public Django/Next.js platform for webhook delivery",
    )
    travel_webhook_secret = fields.Char(
        string="Webhook HMAC Secret Key",
        config_parameter='travel.webhook_secret',
        default="star_travels_super_secret_webhook_key_2026",
        help="Shared secret key used to compute and verify HMAC-SHA256 signatures",
    )
    travel_api_key = fields.Char(
        string="Inbound API Key",
        config_parameter='travel.inbound_api_key',
        default="star_travels_inbound_api_token_2026",
        help="Bearer token required for public platform to push events into Odoo",
    )
    travel_auto_publish_sync = fields.Boolean(
        string="Auto-sync to Public Platform on Publish",
        config_parameter='travel.auto_publish_sync',
        default=True,
        help="When enabled, publishing content or approving partners immediately enqueues outbox events",
    )
