# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid
import re


class TravelPartnerApplication(models.Model):
    _name = 'travel.partner.application'
    _description = 'Star Travels Partner Onboarding Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    business_name = fields.Char(string="Business / Organization Name", required=True, tracking=True)
    organization_slug = fields.Char(string="Organization Slug", index=True, copy=False)
    public_application_id = fields.Char(string="Public Platform Application UUID", index=True, copy=False)
    applicant_id = fields.Char(string="Applicant User UUID", copy=False)
    email = fields.Char(string="Contact Email", required=True, tracking=True)
    phone = fields.Char(string="Contact Phone", tracking=True)
    website = fields.Char(string="Business Website")
    message = fields.Text(string="Application Statement / Pitch")

    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string="Review Status", default='submitted', required=True, tracking=True, index=True)

    rejection_reason = fields.Text(string="Rejection Reason", tracking=True)
    reviewed_by_id = fields.Many2one('res.users', string="Reviewed By", readonly=True)
    reviewed_at = fields.Datetime(string="Reviewed Date", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Created Partner Entity", readonly=True)
    internal_notes = fields.Text(string="Staff Verification Notes")

    def action_start_review(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_("Only submitted applications can be put under review."))
            rec.write({'state': 'under_review'})

    def action_approve(self):
        for rec in self:
            if rec.state != 'under_review':
                raise UserError(_("Application must be in review before approval."))
            
            # Generate organization slug
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', rec.business_name.lower()).strip('-')
            
            # Create or update Partner organization
            partner_vals = {
                'name': rec.business_name,
                'email': rec.email,
                'phone': rec.phone,
                'website': rec.website,
                'is_company': True,
                'comment': f"Star Travels Partner approved from application {rec.public_application_id or rec.id}",
            }
            partner = self.env['res.partner'].create(partner_vals)

            rec.write({
                'state': 'approved',
                'reviewed_by_id': self.env.user.id,
                'reviewed_at': fields.Datetime.now(),
                'organization_slug': slug,
                'partner_id': partner.id,
            })

            rec._emit_outbox_event('partner.approved')

    def action_reject(self):
        for rec in self:
            if rec.state != 'under_review':
                raise UserError(_("Application must be in review before rejection."))
            if not rec.rejection_reason:
                raise UserError(_("Please provide a rejection reason before rejecting."))
            rec.write({
                'state': 'rejected',
                'reviewed_by_id': self.env.user.id,
                'reviewed_at': fields.Datetime.now(),
            })
            rec._emit_outbox_event('partner.rejected')

    def action_reset_submitted(self):
        for rec in self:
            rec.write({'state': 'submitted'})

    def _emit_outbox_event(self, event_type):
        """Helper to create transactional outbox event if travel_integration is available."""
        if 'travel.integration.outbox' in self.env:
            for rec in self:
                payload = {
                    'application_id': rec.public_application_id or str(uuid.uuid4()),
                    'applicant_id': rec.applicant_id or '',
                    'business_name': rec.business_name,
                    'email': rec.email,
                    'phone': rec.phone or '',
                    'website': rec.website or '',
                    'status': rec.state,
                    'organization': {
                        'id': str(uuid.uuid4()),
                        'name': rec.business_name,
                        'slug': rec.organization_slug or '',
                    } if rec.state == 'approved' else None,
                    'rejection_reason': rec.rejection_reason or '',
                    'reviewed_at': rec.reviewed_at.isoformat() if rec.reviewed_at else fields.Datetime.now().isoformat(),
                }
                self.env['travel.integration.outbox'].create_event(
                    event_type=event_type,
                    payload=payload,
                    source='odoo',
                )
