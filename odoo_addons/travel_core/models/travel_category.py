# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


class TravelCategory(models.Model):
    _name = 'travel.category'
    _description = 'Travel Place & Experience Category'
    _order = 'sequence, name'

    name = fields.Char(string="Category Name", required=True, translate=True)
    slug = fields.Char(string="Slug", required=True, index=True)
    sequence = fields.Integer(string="Sequence", default=10)
    icon = fields.Char(string="Icon Identifier", help="Icon name (e.g. coffee, mountain, landmark)")
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ('slug_uniq', 'unique(slug)', 'The category slug must be unique!'),
    ]

    @api.onchange('name')
    def _onchange_name(self):
        if self.name and not self.slug:
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', self.name.lower()).strip('-')
            self.slug = slug
