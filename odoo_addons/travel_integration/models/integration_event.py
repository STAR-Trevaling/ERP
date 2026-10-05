# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import json
import hashlib
import logging

_logger = logging.getLogger(__name__)


class TravelIntegrationEvent(models.Model):
    _name = 'travel.integration.event'
    _description = 'Inbound Integration Event & Idempotency Log'
    _order = 'received_at desc'

    source = fields.Selection([
        ('public-platform', 'Star Travels Public Platform'),
        ('facebook', 'Facebook Messenger'),
        ('zalo', 'Zalo OA'),
        ('pancake', 'Pancake POS'),
        ('ota', 'OTA Integration'),
        ('partner', 'Partner Platform'),
        ('ai-assistant', 'AI Assistant'),
    ], string="Source Channel", required=True, index=True)

    external_event_id = fields.Char(
        string="External Event ID",
        required=True,
        index=True,
        help="Unique identifier from the producer (Idempotency Key)",
    )
    event_type = fields.Char(string="Event Type", required=True, index=True)
    event_version = fields.Integer(string="Version", default=1)
    payload_hash = fields.Char(string="SHA256 Payload Hash", readonly=True)

    state = fields.Selection([
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ], string="Processing Status", default='pending', required=True, index=True)

    received_at = fields.Datetime(string="Received At", default=fields.Datetime.now, readonly=True)
    processed_at = fields.Datetime(string="Processed At", readonly=True)
    attempt_count = fields.Integer(string="Attempts", default=1)
    last_error = fields.Text(string="Last Error Message")

    raw_payload = fields.Text(string="Raw JSON Payload")
    response_json = fields.Text(string="Stored JSON Response")

    res_model = fields.Char(string="Target Model", readonly=True)
    res_id = fields.Integer(string="Target Record ID", readonly=True)

    _sql_constraints = [
        ('source_event_uniq', 'unique(source, external_event_id)', 
         'An event with this ID from this source has already been recorded (Idempotency Violation)!'),
    ]

    @api.model
    def process_inbound_envelope(self, envelope):
        """
        Atomically process incoming event with strict idempotency defense:
        If event with (source, external_event_id) exists and state == 'processed',
        return the cached response immediately without executing side effects!
        """
        event_id = envelope.get('event_id') or envelope.get('idempotency_key')
        event_type = envelope.get('event_type')
        source = envelope.get('source') or 'public-platform'
        event_version = envelope.get('event_version') or 1
        data = envelope.get('data') or envelope

        if not event_id:
            raise ValueError("Event envelope missing mandatory 'event_id' or 'idempotency_key'.")

        raw_str = json.dumps(envelope, sort_keys=True)
        payload_hash = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

        # Check existing event for idempotency
        existing = self.search([
            ('source', '=', source),
            ('external_event_id', '=', str(event_id))
        ], limit=1)

        if existing:
            existing.attempt_count += 1
            if existing.state == 'processed' and existing.response_json:
                _logger.info("Idempotent replay detected for event %s from %s. Returning cached response.", event_id, source)
                return json.loads(existing.response_json)
            # If previous attempt failed, re-attempt
            event_record = existing
        else:
            event_record = self.create({
                'source': source,
                'external_event_id': str(event_id),
                'event_type': event_type or 'unknown',
                'event_version': event_version,
                'payload_hash': payload_hash,
                'raw_payload': raw_str,
                'state': 'pending',
                'received_at': fields.Datetime.now(),
            })

        # Process domain logic based on event_type
        try:
            result = self._dispatch_event(event_type, data, source, event_id)
            event_record.write({
                'state': 'processed',
                'processed_at': fields.Datetime.now(),
                'response_json': json.dumps(result),
                'res_model': result.get('target_model'),
                'res_id': result.get('target_id'),
                'last_error': False,
            })
            return result
        except Exception as e:
            _logger.exception("Error processing inbound event %s: %s", event_id, str(e))
            event_record.write({
                'state': 'failed',
                'last_error': str(e),
            })
            raise

    def _dispatch_event(self, event_type, data, source, event_id):
        """Dispatch event payload to domain models."""
        if event_type in ('inquiry.created', 'lead.created') or 'customer' in data:
            data['source'] = source
            data['external_id'] = event_id
            lead = self.env['crm.lead'].create_from_inquiry_payload(data)
            return {
                'success': True,
                'event_id': event_id,
                'lead_id': lead.id,
                'lead_name': lead.name,
                'partner_id': lead.partner_id.id,
                'target_model': 'crm.lead',
                'target_id': lead.id,
                'status': 'created',
            }

        elif event_type in ('partner.application.created', 'partner_application') or 'business_name' in data:
            app_vals = {
                'business_name': data.get('business_name'),
                'email': data.get('email'),
                'phone': data.get('phone') or '',
                'website': data.get('website') or '',
                'message': data.get('message') or '',
                'public_application_id': str(data.get('application_id') or event_id),
                'applicant_id': str(data.get('applicant_id') or ''),
                'state': 'submitted',
            }
            app = self.env['travel.partner.application'].create(app_vals)
            return {
                'success': True,
                'event_id': event_id,
                'application_id': app.id,
                'target_model': 'travel.partner.application',
                'target_id': app.id,
                'status': 'submitted',
            }

        else:
            raise ValueError(f"Unsupported event_type: {event_type}")

    def action_retry(self):
        """Manual retry action for failed events from the dashboard."""
        for rec in self:
            if rec.raw_payload:
                envelope = json.loads(rec.raw_payload)
                data = envelope.get('data') or envelope
                result = self._dispatch_event(rec.event_type, data, rec.source, rec.external_event_id)
                rec.write({
                    'state': 'processed',
                    'processed_at': fields.Datetime.now(),
                    'response_json': json.dumps(result),
                    'res_model': result.get('target_model'),
                    'res_id': result.get('target_id'),
                    'last_error': False,
                })
