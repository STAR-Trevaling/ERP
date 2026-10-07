# -*- coding: utf-8 -*-
from odoo import fields, models


class TravelAmenity(models.Model):
    _name = 'travel.amenity'
    _description = 'Travel Amenity & Feature'
    _order = 'name'

    name = fields.Char(string="Amenity Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True, index=True)
    icon = fields.Char(string="Icon Name")
    description = fields.Char(string="Description")
    category = fields.Selection([
        ('general', 'General'),
        ('dining', 'Food & Drink'),
        ('wellness', 'Wellness & Spa'),
        ('outdoor', 'Outdoor & Nature'),
        ('accessibility', 'Accessibility'),
    ], string="Type", default='general')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'The amenity code must be unique!'),
    ]
