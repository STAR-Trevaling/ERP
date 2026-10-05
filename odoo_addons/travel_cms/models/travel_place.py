# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid
import re


class TravelPlace(models.Model):
    _name = 'travel.place'
    _description = 'Travel Place & Experience'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string="Place Name", required=True, tracking=True)
    slug = fields.Char(string="Slug", required=True, index=True, tracking=True)
    public_id = fields.Char(string="Public Platform UUID", index=True, copy=False, help="UUID mapping to Django Place.id")
    destination_id = fields.Many2one('travel.destination', string="Destination", required=True, ondelete='restrict', tracking=True)
    category_id = fields.Many2one('travel.category', string="Category", required=True, ondelete='restrict', tracking=True)
    amenity_ids = fields.Many2many('travel.amenity', string="Amenities")
    
    short_description = fields.Char(string="Short Description", size=280, help="Brief excerpt for cards and previews")
    description = fields.Html(string="Detailed Content", sanitize_style=True)
    image_url = fields.Char(string="Primary Image URL")
    overlay_image_url = fields.Char(string="Hero/Overlay Image URL")
    address = fields.Char(string="Street Address", tracking=True)
    website_url = fields.Char(string="Official Website / Link")
    latitude = fields.Float(string="Latitude", digits=(10, 7), required=True)
    longitude = fields.Float(string="Longitude", digits=(10, 7), required=True)
    
    average_rating = fields.Float(string="Average Rating", digits=(3, 2), default=0.0, readonly=True)
    review_count = fields.Integer(string="Review Count", default=0, readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], string="Editorial Status", default='draft', required=True, tracking=True, index=True)

    version = fields.Integer(string="Content Version", default=1, readonly=True)
    published_at = fields.Datetime(string="Published Date", readonly=True)
    reviewer_id = fields.Many2one('res.users', string="Approved By", readonly=True)
    internal_notes = fields.Text(string="Staff Internal Notes")

    _sql_constraints = [
        ('slug_uniq', 'unique(slug)', 'Place slug must be unique!'),
    ]

    @api.onchange('name')
    def _onchange_name(self):
        if self.name and not self.slug:
            self.slug = re.sub(r'[^a-zA-Z0-9]+', '-', self.name.lower()).strip('-')

    def action_submit_review(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft places can be submitted for review."))
            rec.write({'state': 'in_review'})

    def action_approve(self):
        for rec in self:
            if rec.state != 'in_review':
                raise UserError(_("Only places currently in review can be approved."))
            rec.write({
                'state': 'approved',
                'reviewer_id': self.env.user.id,
            })

    def action_publish(self):
        for rec in self:
            if rec.state not in ('approved', 'published'):
                raise UserError(_("Place must be approved before publication."))
            rec.write({
                'state': 'published',
                'published_at': fields.Datetime.now(),
                'version': rec.version + 1,
            })
            rec._emit_outbox_event('place.published')

    def action_archive(self):
        for rec in self:
            rec.write({'state': 'archived'})
            rec._emit_outbox_event('place.archived')

    def action_request_changes(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def action_reset_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def _emit_outbox_event(self, event_type):
        """Helper to create transactional outbox event if travel_integration is available."""
        if 'travel.integration.outbox' in self.env:
            for rec in self:
                payload = {
                    'content_type': 'place',
                    'id': rec.public_id or str(uuid.uuid4()),
                    'slug': rec.slug,
                    'version': rec.version,
                    'published_at': rec.published_at.isoformat() if rec.published_at else fields.Datetime.now().isoformat(),
                    'place': {
                        'name': rec.name,
                        'destination_slug': rec.destination_id.slug,
                        'category_slug': rec.category_id.slug,
                        'short_description': rec.short_description or '',
                        'description': rec.description or '',
                        'image_url': rec.image_url or '',
                        'overlay_image_url': rec.overlay_image_url or '',
                        'address': rec.address or '',
                        'website_url': rec.website_url or '',
                        'latitude': rec.latitude,
                        'longitude': rec.longitude,
                        'average_rating': rec.average_rating,
                        'review_count': rec.review_count,
                    }
                }
                self.env['travel.integration.outbox'].create_event(
                    event_type=event_type,
                    payload=payload,
                    source='odoo',
                )
