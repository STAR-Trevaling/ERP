# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class RetailStockReservation(models.Model):
    _name = 'retail.stock.reservation'
    _description = 'Omnichannel Retail Stock Reservation'
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string="Mã giữ hàng",
        default=lambda self: self.env['ir.sequence'].next_by_code('retail.stock.reservation') or 'New',
        copy=False,
        readonly=True,
        index=True,
    )
    order_reference = fields.Char(
        string="Mã đơn hàng",
        required=True,
        index=True,
        help="Mã tham chiếu đơn hàng hoặc giỏ hàng checkout online."
    )
    product_id = fields.Many2one(
        'product.product',
        string="Sản phẩm",
        required=True,
        index=True,
        ondelete='restrict',
    )
    location_id = fields.Many2one(
        'stock.location',
        string="Kho / Điểm bán",
        required=True,
        index=True,
        ondelete='restrict',
    )
    quantity = fields.Float(
        string="Số lượng giữ",
        required=True,
        default=1.0,
    )
    reserved_until = fields.Datetime(
        string="Thời hạn giữ đến",
        required=True,
        index=True,
    )
    state = fields.Selection([
        ('active', 'Đang giữ'),
        ('released', 'Đã giải phóng'),
        ('consumed', 'Đã xuất kho'),
    ], string="Trạng thái", default='active', index=True, required=True)

    company_id = fields.Many2one(
        'res.company',
        string="Công ty",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model
    def create_reservation(self, product_id, location_id, quantity, order_reference, duration_minutes=15):
        """
        Creates a stock reservation using PostgreSQL row-level locking (SELECT FOR UPDATE)
        to prevent race conditions and overselling across omnichannel checkouts.
        """
        if quantity <= 0:
            raise ValidationError("Số lượng đặt trước phải lớn hơn 0.")

        # 1. Lock quant rows for target product and location
        self.env.cr.execute("""
            SELECT id, quantity, reserved_quantity
            FROM stock_quant
            WHERE product_id = %s AND location_id = %s
            FOR UPDATE
        """, (product_id, location_id))
        quant_rows = self.env.cr.fetchall()

        total_physical_qty = sum(r[1] for r in quant_rows) if quant_rows else 0.0

        # 2. Check location safety buffer
        location = self.env['stock.location'].browse(location_id)
        safety_buffer_units = 0.0
        if location.safety_buffer_pct > 0:
            safety_buffer_units = (total_physical_qty * location.safety_buffer_pct) / 100.0

        # 3. Sum current active reservations
        self.env.cr.execute("""
            SELECT COALESCE(SUM(quantity), 0)
            FROM retail_stock_reservation
            WHERE product_id = %s 
              AND location_id = %s 
              AND state = 'active'
              AND reserved_until > NOW()
        """, (product_id, location_id))
        active_reserved_qty = self.env.cr.fetchone()[0]

        # Available for new reservation = Physical - SafetyBuffer - ActiveReservations
        available_qty = total_physical_qty - safety_buffer_units - active_reserved_qty

        if quantity > available_qty:
            raise ValidationError(
                f"Tồn kho khả dụng không đủ ({available_qty:.2f} đơn vị khả dụng, yêu cầu {quantity:.2f})."
            )

        # 4. Create and persist reservation
        expiry = fields.Datetime.now() + timedelta(minutes=duration_minutes)
        return self.create({
            'product_id': product_id,
            'location_id': location_id,
            'quantity': quantity,
            'order_reference': order_reference,
            'reserved_until': expiry,
            'state': 'active',
        })

    def action_release(self):
        """Release reservation manually or via cron expiration"""
        for record in self:
            if record.state == 'active':
                record.write({'state': 'released'})

    def action_consume(self):
        """Consume reservation upon successful order payment and warehouse delivery"""
        for record in self:
            if record.state == 'active':
                record.write({'state': 'consumed'})

    @api.model
    def _cron_release_expired_reservations(self):
        """Periodic background job to release stale reservations older than threshold"""
        now = fields.Datetime.now()
        expired = self.search([
            ('state', '=', 'active'),
            ('reserved_until', '<=', now)
        ])
        if expired:
            expired.action_release()
        return True
