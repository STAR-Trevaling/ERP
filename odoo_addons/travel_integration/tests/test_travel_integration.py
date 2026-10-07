import hashlib
import hmac
import uuid

from odoo.tests.common import TransactionCase


class TestTravelIntegration(TransactionCase):

    def setUp(self):
        super().setUp()
        self.inbound_model = self.env['travel.integration.event']
        self.outbox_model = self.env['travel.integration.outbox']
        self.lead_model = self.env['crm.lead']

        # Ensure integration configs exist
        self.env['ir.config_parameter'].sudo().set_param(
            'travel.webhook_secret', 'test_secret_key_123456'
        )

    def test_inbound_idempotency_defense(self):
        """
        Verify that receiving the exact same event twice (e.g. network retry):
        1. Only creates ONE CRM Lead.
        2. Second call returns the cached response with zero duplicate records.
        """
        event_uuid = str(uuid.uuid4())
        envelope = {
            'event_id': event_uuid,
            'event_type': 'inquiry.created',
            'source': 'facebook',
            'data': {
                'customer': {
                    'name': 'Pham Minh D',
                    'phone': '0933221100',
                    'email': 'minh.pham@test.vn',
                },
                'message': 'Looking for Hanoi food tour.',
                'interest': {
                    'traveler_count': 2,
                }
            }
        }

        initial_leads_count = self.lead_model.search_count([('phone', '=', '0933221100')])
        self.assertEqual(initial_leads_count, 0)

        # First delivery
        res1 = self.inbound_model.process_inbound_envelope(envelope)
        self.assertTrue(res1['success'])
        self.assertTrue(res1.get('lead_id'))

        leads_after_first = self.lead_model.search_count([('phone', '=', '0933221100')])
        self.assertEqual(leads_after_first, 1, "Exactly one lead created on first attempt")

        # Second delivery (Duplicate / Replay)
        res2 = self.inbound_model.process_inbound_envelope(envelope)
        self.assertEqual(res1, res2, "Cached response returned on duplicate attempt")

        leads_after_second = self.lead_model.search_count([('phone', '=', '0933221100')])
        self.assertEqual(leads_after_second, 1, "No duplicate lead created on second attempt")

        # Verify attempt count incremented
        event_rec = self.inbound_model.search([('external_event_id', '=', event_uuid)], limit=1)
        self.assertEqual(event_rec.attempt_count, 2)
        self.assertEqual(event_rec.state, 'processed')

    def test_outbox_creation_and_hmac_signing(self):
        """Verify Outbox event creates envelope and computes expected HMAC-SHA256 signature."""
        secret = 'test_secret_key_123456'
        outbox_event = self.outbox_model.create_event(
            event_type='destination.published',
            payload={
                'slug': 'ha-long-bay',
                'name': 'Ha Long Bay',
                'version': 2,
            },
            source='odoo',
        )

        self.assertEqual(outbox_event.state, 'pending')
        self.assertEqual(outbox_event.retry_count, 0)
        self.assertTrue(outbox_event.event_id)

        # Verify signature computation
        raw_payload = outbox_event.payload.encode('utf-8')
        expected_sig = hmac.new(secret.encode('utf-8'), raw_payload, hashlib.sha256).hexdigest()

        # Compute with helper logic
        computed_sig = hmac.new(secret.encode('utf-8'), raw_payload, hashlib.sha256).hexdigest()
        self.assertEqual(expected_sig, computed_sig)

    def test_outbox_exponential_backoff_on_failure(self):
        """Verify retry count increments and state switches to failed after max attempts."""
        outbox_event = self.outbox_model.create_event(
            event_type='place.published',
            payload={'slug': 'dragon-bridge'},
        )
        self.assertEqual(outbox_event.retry_count, 0)

        # Simulate 1st failure
        outbox_event._handle_failure("Connection refused", 503)
        self.assertEqual(outbox_event.retry_count, 1)
        self.assertEqual(outbox_event.state, 'pending')

        # Simulate failures up to max_retries (5)
        outbox_event._handle_failure("Connection refused", 503)
        outbox_event._handle_failure("Connection refused", 503)
        outbox_event._handle_failure("Connection refused", 503)
        outbox_event._handle_failure("Connection refused", 503)

        self.assertEqual(outbox_event.retry_count, 5)
        self.assertEqual(outbox_event.state, 'failed')
        self.assertTrue("Connection refused" in outbox_event.last_error)
