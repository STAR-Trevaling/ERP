# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def extract_marketing_attribution(payload):
    """
    Extracts canonical marketing attribution from payload with backward-compatible fallback:
    Priority: payload['marketing'] > payload['source_metadata'] > payload['utm'] > root fields.
    """
    if not isinstance(payload, dict):
        return {}

    marketing_data = payload.get('marketing') or {}
    source_meta = payload.get('source_metadata') or {}
    utm_data = payload.get('utm') or {}

    channel = (
        marketing_data.get('channel')
        or payload.get('source')
        or source_meta.get('channel')
        or 'website'
    )
    utm_source = (
        marketing_data.get('utm_source')
        or source_meta.get('utm_source')
        or utm_data.get('source')
        or channel
    )
    utm_medium = (
        marketing_data.get('utm_medium')
        or source_meta.get('utm_medium')
        or utm_data.get('medium')
    )
    utm_campaign = (
        marketing_data.get('utm_campaign')
        or source_meta.get('utm_campaign')
        or source_meta.get('campaign')
        or utm_data.get('campaign')
        or payload.get('campaign')
    )
    utm_term = (
        marketing_data.get('utm_term')
        or source_meta.get('utm_term')
        or utm_data.get('term')
    )
    utm_content = (
        marketing_data.get('utm_content')
        or source_meta.get('utm_content')
        or utm_data.get('content')
    )
    gclid = (
        marketing_data.get('gclid')
        or source_meta.get('gclid')
        or payload.get('gclid')
    )
    fbclid = (
        marketing_data.get('fbclid')
        or source_meta.get('fbclid')
        or payload.get('fbclid')
    )
    landing_page = (
        marketing_data.get('landing_page')
        or source_meta.get('landing_page')
        or payload.get('landing_page')
    )
    referrer = (
        marketing_data.get('referrer')
        or source_meta.get('referrer')
        or payload.get('referrer')
    )

    return {
        'channel': str(channel).strip() if channel else 'website',
        'utm_source': str(utm_source).strip() if utm_source else None,
        'utm_medium': str(utm_medium).strip() if utm_medium else None,
        'utm_campaign': str(utm_campaign).strip() if utm_campaign else None,
        'utm_term': str(utm_term).strip() if utm_term else None,
        'utm_content': str(utm_content).strip() if utm_content else None,
        'gclid': str(gclid).strip() if gclid else None,
        'fbclid': str(fbclid).strip() if fbclid else None,
        'landing_page': str(landing_page).strip() if landing_page else None,
        'referrer': str(referrer).strip() if referrer else None,
    }


def resolve_utm_model_record(model_env, raw_name):
    """
    Finds or creates a UTM model record (utm.source, utm.medium, utm.campaign)
    using case-insensitive comparison (=ilike) to avoid duplicate records.
    """
    if not raw_name or not str(raw_name).strip():
        return False
    clean_name = str(raw_name).strip()
    existing = model_env.search([('name', '=ilike', clean_name)], limit=1)
    if existing:
        return existing.id
    created = model_env.create({'name': clean_name})
    return created.id


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    public_customer_id = fields.Char(
        string="Public Platform UUID",
        index=True,
        copy=False,
        help="UUID of traveler on the public platform",
    )
    source_system = fields.Selection([
        ('website', 'Public Website'),
        ('facebook', 'Facebook'),
        ('zalo', 'Zalo'),
        ('pancake', 'Pancake POS'),
        ('ota', 'Online Travel Agency'),
        ('partner', 'B2B Partner Referral'),
        ('ai_assistant', 'AI Assistant Human Handoff'),
        ('direct', 'Direct Call / Walk-in'),
    ], string="Channel Source", default='website', index=True, tracking=True)

    inquiry_type = fields.Selection([
        ('consultation', 'Destination Consultation'),
        ('tour_booking', 'Tour / Experience Booking'),
        ('partner_inquiry', 'Partner Inquiry'),
        ('general_support', 'General Customer Support'),
    ], string="Inquiry Type", default='consultation', tracking=True)

    destination_interest_id = fields.Many2one(
        'travel.destination',
        string="Destination Interest",
        ondelete='set null',
        tracking=True,
    )
    place_interest_id = fields.Many2one(
        'travel.place',
        string="Place / Attraction Interest",
        ondelete='set null',
        tracking=True,
    )
    travel_date_intended = fields.Date(string="Intended Travel Date")
    traveler_count = fields.Integer(string="Party Size", default=1)
    external_lead_id = fields.Char(
        string="External Lead Ref",
        index=True,
        copy=False,
        help="Unique reference from source channel (e.g. FB Lead ID or Pancake Order ID)",
    )

    # Marketing Attribution & Ad Click IDs
    utm_term = fields.Char(
        string="UTM Term / Keywords",
        index=True,
        copy=False,
        help="Search keywords or targeted audience from campaign",
    )
    utm_content = fields.Char(
        string="UTM Content / Creative",
        copy=False,
        help="Ad creative, banner, or content variation identifier",
    )
    gclid = fields.Char(
        string="Google Click ID (GCLID)",
        index=True,
        copy=False,
        help="Google Ads click tracking identifier",
    )
    fbclid = fields.Char(
        string="Facebook Click ID (FBCLID)",
        index=True,
        copy=False,
        help="Facebook Ads click tracking identifier",
    )
    landing_page_url = fields.Char(
        string="Landing Page URL",
        copy=False,
        help="First page visited by the customer when entering the site",
    )
    referrer_url = fields.Char(
        string="Referrer URL",
        copy=False,
        help="HTTP Referrer URL from which the customer arrived",
    )

    @api.model
    def create_from_inquiry_payload(self, payload):
        """
        Receives normalized canonical data and creates/links:
        1. res.partner via smart deduplication
        2. travel.destination and travel.place interests by slug
        3. crm.lead with complete marketing attribution (utm.mixin + click IDs)
        """
        customer_data = payload.get('customer') or {}
        interest_data = payload.get('interest') or {}
        source_meta = payload.get('source_metadata') or {}

        # Marketing attribution extraction
        attribution = extract_marketing_attribution(payload)
        channel = attribution.get('channel') or 'website'

        # 1. Deduplicate & resolve Partner
        partner = self.env['res.partner'].find_or_create_traveler(
            name=customer_data.get('name'),
            phone=customer_data.get('phone'),
            email=customer_data.get('email'),
            public_id=customer_data.get('public_customer_id'),
            provider=customer_data.get('identity_provider') or channel,
        )

        # 2. Resolve Destination and Place interest
        dest_record = False
        dest_slug = interest_data.get('destination_slug')
        if dest_slug:
            dest_record = self.env['travel.destination'].search([('slug', '=', dest_slug)], limit=1)

        place_record = False
        place_slug = interest_data.get('place_slug')
        if place_slug:
            place_record = self.env['travel.place'].search([('slug', '=', place_slug)], limit=1)

        # 3. Resolve UTM Source, Medium, Campaign via auto-discovery
        utm_source_id = resolve_utm_model_record(self.env['utm.source'], attribution.get('utm_source'))
        utm_medium_id = resolve_utm_model_record(self.env['utm.medium'], attribution.get('utm_medium'))
        utm_campaign_id = resolve_utm_model_record(self.env['utm.campaign'], attribution.get('utm_campaign'))

        # 4. Construct Lead Title
        cust_name = customer_data.get('name') or partner.name
        interest_desc = (dest_record and dest_record.name) or (place_record and place_record.name) or "Travel Inquiry"
        lead_name = f"[{channel.upper()}] {interest_desc} - {cust_name}"

        # 5. Create Lead
        lead_vals = {
            'name': lead_name,
            'partner_id': partner.id,
            'contact_name': customer_data.get('name') or partner.name,
            'phone': customer_data.get('phone') or partner.phone,
            'email_from': customer_data.get('email') or partner.email,
            'source_system': channel if channel in [x[0] for x in self._fields['source_system'].selection] else 'website',
            'inquiry_type': payload.get('inquiry_type') or 'consultation',
            'destination_interest_id': dest_record.id if dest_record else False,
            'place_interest_id': place_record.id if place_record else False,
            'travel_date_intended': interest_data.get('travel_date') or False,
            'traveler_count': interest_data.get('traveler_count') or 1,
            'public_customer_id': customer_data.get('public_customer_id') or partner.public_customer_id or False,
            'external_lead_id': source_meta.get('external_lead_id') or payload.get('external_id') or False,
            'description': payload.get('message') or '',
            # UTM Attribution & Tracking
            'campaign_id': utm_campaign_id or False,
            'source_id': utm_source_id or False,
            'medium_id': utm_medium_id or False,
            'utm_term': attribution.get('utm_term') or False,
            'utm_content': attribution.get('utm_content') or False,
            'gclid': attribution.get('gclid') or False,
            'fbclid': attribution.get('fbclid') or False,
            'landing_page_url': attribution.get('landing_page') or False,
            'referrer_url': attribution.get('referrer') or False,
        }

        lead = self.create(lead_vals)
        _logger.info("Created Star Travels Lead ID %s for Partner ID %s from %s (Campaign: %s, Source: %s, Medium: %s)",
                     lead.id, partner.id, channel, utm_campaign_id, utm_source_id, utm_medium_id)
        return lead
