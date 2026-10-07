# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    public_customer_id = fields.Char(
        string="Public Platform UUID",
        index=True,
        copy=False,
        help="UUID of traveler on the public Django platform",
    )
    identity_provider = fields.Selection([
        ('public_auth', 'Public Web App'),
        ('website', 'Public Website'),
        ('facebook', 'Facebook Messenger'),
        ('zalo', 'Zalo Official Account'),
        ('pancake', 'Pancake POS'),
        ('google', 'Google OAuth'),
        ('phone', 'SMS / Direct Phone'),
        ('direct', 'Direct Walk-in / Call'),
        ('ota', 'OTA Channel'),
        ('partner', 'Partner Platform'),
    ], string="Identity Provider", default='public_auth', index=True)

    travel_inquiry_count = fields.Integer(
        string="Inquiry Count",
        compute='_compute_travel_inquiry_count',
    )

    def _compute_travel_inquiry_count(self):
        for partner in self:
            partner.travel_inquiry_count = self.env['crm.lead'].search_count([
                ('partner_id', '=', partner.id)
            ])

    @classmethod
    def normalize_phone(cls, phone):
        """Standardize phone number for reliable deduplication."""
        if not phone:
            return False
        digits = re.sub(r'\D', '', str(phone))
        if digits.startswith('84'):
            digits = '0' + digits[2:]
        elif digits.startswith('0'):
            pass
        elif len(digits) == 9:
            digits = '0' + digits
        return digits if len(digits) >= 9 else False

    @classmethod
    def normalize_email(cls, email):
        """Standardize email for deduplication."""
        if not email:
            return False
        return email.strip().lower()

    @api.model
    def find_or_create_traveler(self, name, phone=None, email=None, public_id=None, provider='public_auth'):
        """
        Deduplication Strategy:
        1. Exact match by public_customer_id (if provided)
        2. Exact match by normalized phone (if valid)
        3. Exact match by normalized email (if valid)
        4. If not found, create a new res.partner record.
        """
        norm_phone = self.normalize_phone(phone) if phone else False
        norm_email = self.normalize_email(email) if email else False

        partner = False

        # Rule 1: Match by public UUID
        if public_id:
            partner = self.search([('public_customer_id', '=', str(public_id))], limit=1)

        # Rule 2: Match by normalized phone
        if not partner and norm_phone:
            # Match directly or by clean phone format
            domain = ['|', ('phone', '=like', f'%{norm_phone[-9:]}'), ('mobile', '=like', f'%{norm_phone[-9:]}')]
            partner = self.search(domain, limit=1)

        # Rule 3: Match by normalized email
        if not partner and norm_email:
            partner = self.search([('email', '=ilike', norm_email)], limit=1)

        # If existing partner found, update missing identifiers
        if partner:
            vals_to_update = {}
            if public_id and not partner.public_customer_id:
                vals_to_update['public_customer_id'] = str(public_id)
            if norm_phone and not partner.phone:
                vals_to_update['phone'] = norm_phone
            if norm_email and not partner.email:
                vals_to_update['email'] = norm_email
            if vals_to_update:
                partner.write(vals_to_update)
            return partner

        # Rule 4: Create new partner
        valid_providers = dict(self._fields['identity_provider'].selection)
        safe_provider = provider if provider in valid_providers else 'website'
        vals = {
            'name': name or (norm_phone or norm_email or "Anonymous Traveler"),
            'phone': norm_phone or (phone or False),
            'email': norm_email or (email or False),
            'public_customer_id': str(public_id) if public_id else False,
            'identity_provider': safe_provider,
        }
        return self.create(vals)
