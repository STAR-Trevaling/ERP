# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_retail_available_qty(self, location_id):
        """
        Calculates the actual available quantity for retail checkout at a specific location,
        taking into account physical stock, safety buffer percentage, and active unexpired reservations.
        """
        self.ensure_one()
        location = self.env['stock.location'].browse(location_id)

        # 1. Total physical on-hand
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.id),
            ('location_id', '=', location.id)
        ])
        physical_qty = sum(quants.mapped('quantity'))

        # 2. Safety buffer
        buffer_qty = 0.0
        if location.safety_buffer_pct > 0:
            buffer_qty = (physical_qty * location.safety_buffer_pct) / 100.0

        # 3. Active unexpired reservations
        self.env.cr.execute("""
            SELECT COALESCE(SUM(quantity), 0)
            FROM retail_stock_reservation
            WHERE product_id = %s 
              AND location_id = %s 
              AND state = 'active'
              AND reserved_until > NOW()
        """, (self.id, location.id))
        active_reserved = self.env.cr.fetchone()[0]

        net_available = physical_qty - buffer_qty - active_reserved
        return max(0.0, net_available)
