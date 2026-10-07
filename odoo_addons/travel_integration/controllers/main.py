# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging

from odoo import SUPERUSER_ID, http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


class TravelIntegrationController(http.Controller):

    def _verify_auth(self):
        """
        Verify request using either:
        1. Bearer API Key header against config 'travel.inbound_api_key'
        2. HMAC-SHA256 signature in 'X-Signature-SHA256' against config 'travel.webhook_secret'
        """
        auth_header = request.httprequest.headers.get('Authorization', '')
        api_key_header = request.httprequest.headers.get('X-API-Key', '')
        sig_header = request.httprequest.headers.get('X-Signature-SHA256', '')

        conf_api_key = request.env['ir.config_parameter'].sudo().get_param(
            'travel.inbound_api_key', 'star_travels_inbound_api_token_2026'
        )
        conf_secret = request.env['ir.config_parameter'].sudo().get_param(
            'travel.webhook_secret', 'star_travels_super_secret_webhook_key_2026'
        )

        # Check API Key (Bearer or Header)
        token = auth_header.replace('Bearer ', '').strip() if auth_header.startswith('Bearer ') else api_key_header
        if token and hmac.compare_digest(token, conf_api_key):
            return True

        # Check HMAC-SHA256 signature
        if sig_header:
            raw_body = request.httprequest.get_data()
            body_bytes = raw_body.encode('utf-8') if isinstance(raw_body, str) else raw_body
            computed_sig = hmac.new(conf_secret.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig_header, computed_sig):
                return True

        return False

    def _json_response(self, data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type='application/json; charset=utf-8'
        )

    def _problem_response(self, title, detail, status=400, error_code="INVALID_REQUEST"):
        """RFC 7807 Problem Details for HTTP APIs format."""
        problem = {
            'type': f'https://star-travels.com/errors/{error_code.lower()}',
            'title': title,
            'status': status,
            'detail': detail,
            'instance': request.httprequest.path,
        }
        return self._json_response(problem, status=status)

    @http.route('/api/v1/travel/health', type='http', auth='public', methods=['GET'], csrf=False, readonly=True)
    def health_check(self, **kwargs):
        """Public healthcheck probe for integration endpoints."""
        return self._json_response({
            'status': 'ok',
            'service': 'Star Travels Odoo 18 Integration Backbone',
            'version': '18.0.1.0.0',
        })

    @http.route('/api/v1/travel/inquiry', type='http', auth='public', methods=['POST'], csrf=False, readonly=False)
    def handle_inquiry(self, **kwargs):
        """Inbound endpoint for public website / social channel inquiries."""
        if not self._verify_auth():
            return self._problem_response(
                title="Unauthorized",
                detail="Missing or invalid authentication token / HMAC signature.",
                status=401,
                error_code="UNAUTHORIZED"
            )

        try:
            raw_data = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            return self._problem_response(
                title="Invalid JSON",
                detail="Request body must be valid JSON.",
                status=400,
                error_code="BAD_REQUEST"
            )

        # Extract idempotency key
        idempotency_key = (
            request.httprequest.headers.get('Idempotency-Key') or
            request.httprequest.headers.get('X-Event-ID') or
            payload.get('event_id') or
            payload.get('external_id')
        )

        if not idempotency_key:
            return self._problem_response(
                title="Missing Idempotency Key",
                detail="Header 'Idempotency-Key' or payload 'event_id' is required.",
                status=400,
                error_code="MISSING_IDEMPOTENCY_KEY"
            )

        envelope = {
            'event_id': idempotency_key,
            'event_type': payload.get('event_type') or 'inquiry.created',
            'source': payload.get('source') or 'website',
            'event_version': payload.get('event_version') or 1,
            'data': payload.get('data') or payload,
        }

        try:
            env = request.env(user=SUPERUSER_ID)
            result = env['travel.integration.event'].process_inbound_envelope(envelope)
            return self._json_response(result, status=200)
        except Exception as e:
            _logger.exception("Error handling inbound inquiry: %s", str(e))
            return self._problem_response(
                title="Internal Server Error",
                detail=str(e),
                status=500,
                error_code="PROCESSING_ERROR"
            )

    @http.route('/api/v1/travel/partner-application', type='http', auth='public', methods=['POST'], csrf=False, readonly=False)
    def handle_partner_application(self, **kwargs):
        """Inbound endpoint for partner onboarding applications from public platform."""
        if not self._verify_auth():
            return self._problem_response(
                title="Unauthorized",
                detail="Missing or invalid authentication token / HMAC signature.",
                status=401,
                error_code="UNAUTHORIZED"
            )

        try:
            raw_data = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            return self._problem_response(
                title="Invalid JSON",
                detail="Request body must be valid JSON.",
                status=400,
                error_code="BAD_REQUEST"
            )

        idempotency_key = (
            request.httprequest.headers.get('Idempotency-Key') or
            request.httprequest.headers.get('X-Event-ID') or
            payload.get('event_id') or
            payload.get('application_id')
        )

        if not idempotency_key:
            return self._problem_response(
                title="Missing Idempotency Key",
                detail="Header 'Idempotency-Key' or payload 'event_id' is required.",
                status=400,
                error_code="MISSING_IDEMPOTENCY_KEY"
            )

        envelope = {
            'event_id': idempotency_key,
            'event_type': 'partner.application.created',
            'source': payload.get('source') or 'public-platform',
            'event_version': payload.get('event_version') or 1,
            'data': payload.get('data') or payload,
        }

        try:
            env = request.env(user=SUPERUSER_ID)
            result = env['travel.integration.event'].process_inbound_envelope(envelope)
            return self._json_response(result, status=200)
        except Exception as e:
            _logger.exception("Error handling partner application: %s", str(e))
            return self._problem_response(
                title="Internal Server Error",
                detail=str(e),
                status=500,
                error_code="PROCESSING_ERROR"
            )
