# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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

    @api.model
    def create_from_inquiry_payload(self, payload):
        """
        Receives normalized canonical data and creates/links:
        1. res.partner via smart deduplication
        2. travel.destination and travel.place interests by slug
        3. crm.lead with complete channel attribution
        """
        customer_data = payload.get('customer') or {}
        interest_data = payload.get('interest') or {}
        source_meta = payload.get('source_metadata') or {}
        channel = payload.get('source') or source_meta.get('channel') or 'website'

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

        # 3. Resolve UTM Source
        utm_source_id = False
        if channel:
            source_rec = self.env['utm.source'].search([('name', '=ilike', channel)], limit=1)
            if not source_rec:
                source_rec = self.env['utm.source'].create({'name': channel.capitalize()})
            utm_source_id = source_rec.id

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
            'source_id': utm_source_id,
        }

        lead = self.create(lead_vals)
        _logger.info("Created Star Travels Lead ID %s for Partner ID %s from %s", lead.id, partner.id, channel)
        return lead
