# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta
import json
import uuid
import hmac
import hashlib
import urllib.request
import urllib.error
import logging

_logger = logging.getLogger(__name__)


class TravelIntegrationOutbox(models.Model):
    _name = 'travel.integration.outbox'
    _description = 'Transactional Outbox for Star Travels Events'
    _order = 'create_date desc'

    event_id = fields.Char(string="Event UUID", required=True, index=True, default=lambda self: str(uuid.uuid4()))
    event_type = fields.Char(string="Event Type", required=True, index=True)
    event_version = fields.Integer(string="Version", default=1)
    source = fields.Char(string="Source", default="odoo")
    payload = fields.Text(string="JSON Payload", required=True)

    state = fields.Selection([
        ('pending', 'Pending Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Permanently Failed'),
    ], string="Delivery Status", default='pending', required=True, index=True)

    retry_count = fields.Integer(string="Retry Count", default=0)
    max_retries = fields.Integer(string="Max Retries", default=5)
    next_retry_at = fields.Datetime(string="Next Retry At", default=fields.Datetime.now, index=True)
    delivered_at = fields.Datetime(string="Delivered At", readonly=True)
    last_error = fields.Text(string="Last Delivery Error")
    http_status = fields.Integer(string="HTTP Status", readonly=True)

    @api.model
    def create_event(self, event_type, payload, source='odoo', event_version=1):
        """Enqueue an event atomically inside the current business transaction."""
        event_id = str(uuid.uuid4())
        envelope = {
            'event_id': event_id,
            'event_type': event_type,
            'event_version': event_version,
            'source': source,
            'occurred_at': fields.Datetime.now().isoformat(),
            'data': payload,
        }
        record = self.create({
            'event_id': event_id,
            'event_type': event_type,
            'event_version': event_version,
            'source': source,
            'payload': json.dumps(envelope),
            'state': 'pending',
            'next_retry_at': fields.Datetime.now(),
        })
        _logger.info("Enqueued Outbox Event %s [%s]", event_id, event_type)
        return record

    @api.model
    def dispatch_pending_events(self, batch_size=50):
        """Cron worker method to dispatch pending outbox events with exponential backoff."""
        now = fields.Datetime.now()
        pending_records = self.search([
            ('state', '=', 'pending'),
            ('next_retry_at', '<=', now)
        ], limit=batch_size, order='create_date asc')

        if not pending_records:
            return True

        base_url = self.env['ir.config_parameter'].sudo().get_param('travel.public_platform_url', 'http://localhost:8000').rstrip('/')
        secret = self.env['ir.config_parameter'].sudo().get_param('travel.webhook_secret', 'star_travels_super_secret_webhook_key_2026')
        endpoint = f"{base_url}/api/integrations/v1/odoo/events"

        for rec in pending_records:
            rec._dispatch_single(endpoint, secret)

        return True

    def _dispatch_single(self, endpoint, secret):
        """Dispatch a single event via HTTP POST with HMAC signature."""
        self.ensure_one()
        payload_bytes = self.payload.encode('utf-8')
        signature = hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'StarTravels-Odoo18-Integration/1.0',
            'X-Signature-SHA256': signature,
            'X-Event-Type': self.event_type,
            'X-Event-ID': self.event_id,
            'Idempotency-Key': self.event_id,
        }

        req = urllib.request.Request(endpoint, data=payload_bytes, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.getcode()
                if 200 <= status_code < 300:
                    self.write({
                        'state': 'delivered',
                        'delivered_at': fields.Datetime.now(),
                        'http_status': status_code,
                        'last_error': False,
                    })
                    _logger.info("Successfully delivered Outbox Event %s to %s", self.event_id, endpoint)
                    return True
        except urllib.error.HTTPError as e:
            err_msg = f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"
            self._handle_failure(err_msg, e.code)
        except Exception as e:
            err_msg = f"Network/Connection error: {str(e)}"
            self._handle_failure(err_msg, 0)
        return False

    def _handle_failure(self, err_msg, status_code):
        """Calculate exponential backoff or mark as permanently failed."""
        self.ensure_one()
        new_retry = self.retry_count + 1
        _logger.warning("Failed delivery for Outbox Event %s (attempt %s/%s): %s", 
                       self.event_id, new_retry, self.max_retries, err_msg)
        
        if new_retry >= self.max_retries:
            self.write({
                'state': 'failed',
                'retry_count': new_retry,
                'http_status': status_code,
                'last_error': err_msg,
            })
        else:
            # Exponential backoff: 10s, 30s, 90s, 270s...
            delay_seconds = 10 * (3 ** (new_retry - 1))
            self.write({
                'retry_count': new_retry,
                'next_retry_at': fields.Datetime.now() + timedelta(seconds=delay_seconds),
                'http_status': status_code,
                'last_error': err_msg,
            })

    def action_force_retry(self):
        """Action button on form to reset failed event and trigger delivery."""
        for rec in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('travel.public_platform_url', 'http://localhost:8000').rstrip('/')
            secret = self.env['ir.config_parameter'].sudo().get_param('travel.webhook_secret', 'star_travels_super_secret_webhook_key_2026')
            endpoint = f"{base_url}/api/integrations/v1/odoo/events"
            rec._dispatch_single(endpoint, secret)
