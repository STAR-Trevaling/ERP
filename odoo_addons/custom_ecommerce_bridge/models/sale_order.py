# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    web_order_ref = fields.Char(
        string="Mã đơn Website",
        index=True,
        copy=False,
        help="Mã tham chiếu đơn hàng sinh ra từ Website Backend"
    )
    web_payment_status = fields.Selection(
        selection=[
            ('unpaid', 'Chưa thanh toán'),
            ('pending', 'Chờ xác nhận thanh toán'),
            ('paid', 'Đã thanh toán thành công'),
            ('cancelled', 'Đã hủy / Hết hạn giữ hàng'),
        ],
        string="Trạng thái thanh toán Web",
        default='unpaid',
        index=True,
        tracking=True
    )
    hold_expires_at = fields.Datetime(
        string="Hạn giữ tồn kho",
        index=True,
        help="Thời điểm hết hạn giữ tồn kho nếu khách hàng không hoàn tất thanh toán"
    )
    gateway_transaction_id = fields.Char(
        string="Mã giao dịch Cổng TT",
        index=True,
        copy=False
    )
    gateway_name = fields.Char(
        string="Cổng thanh toán",
        help="VNPay, MoMo, ZaloPay, VietQR..."
    )

    @api.model
    def action_create_web_order_atomic(self, order_data: dict) -> dict:
        """
        API Endpoint nguyên khối (Atomic Transaction):
        1. Tìm hoặc tạo Customer (res.partner) dựa trên số điện thoại/email
        2. Kiểm tra tồn kho khả dụng (Free Stock)
        3. Tạo sale.order và xác nhận (action_confirm) để khóa giữ chỗ tồn kho (Hold Stock)
        4. Trả về kết quả cho FastAPI Middleware
        """
        client_order_ref = order_data.get('client_order_ref')
        if not client_order_ref:
            return {'status': 'error', 'code': 'MISSING_REF', 'message': 'client_order_ref là bắt buộc'}

        # 1. Kiểm tra tính Idempotency: nếu đơn đã tồn tại, trả về thông tin đơn hiện tại
        existing_order = self.search([('web_order_ref', '=', client_order_ref)], limit=1)
        if existing_order:
            _logger.info(f"[ECOM-BRIDGE] Order {client_order_ref} already exists (ID: {existing_order.id}).")
            return {
                'status': 'success',
                'is_duplicate': True,
                'odoo_order_id': existing_order.id,
                'odoo_name': existing_order.name,
                'hold_expires_at': fields.Datetime.to_string(existing_order.hold_expires_at) if existing_order.hold_expires_at else None,
                'amount_total': existing_order.amount_total,
            }

        # 2. Xử lý Customer (res.partner)
        customer_data = order_data.get('customer', {})
        phone = customer_data.get('phone', '').strip()
        email = customer_data.get('email', '').strip()
        name = customer_data.get('name', 'Khách Lẻ Website')
        street = customer_data.get('shipping_address', {}).get('street', '')

        partner = False
        if phone:
            partner = self.env['res.partner'].search([('phone', '=', phone)], limit=1)
        if not partner and email:
            partner = self.env['res.partner'].search([('email', '=', email)], limit=1)

        if not partner:
            partner = self.env['res.partner'].create({
                'name': name,
                'phone': phone,
                'email': email,
                'street': street,
                'customer_rank': 1,
            })
            _logger.info(f"[ECOM-BRIDGE] Created new partner {partner.id} for phone: {phone}")

        # 3. Kiểm tra Tồn kho & Chuẩn bị Order Lines
        order_lines = []
        hold_minutes = int(order_data.get('hold_minutes', 15))
        now = fields.Datetime.now()
        hold_deadline = now + timedelta(minutes=hold_minutes)

        for line in order_data.get('order_lines', []):
            sku = line.get('sku')
            qty = float(line.get('qty', 1.0))
            price_unit = float(line.get('price_unit', 0.0))

            product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if not product:
                return {
                    'status': 'error',
                    'code': 'PRODUCT_NOT_FOUND',
                    'message': f"Không tìm thấy sản phẩm có SKU: {sku}"
                }

            # Kiểm tra tồn kho khả dụng (ưu tiên Omnichannel Core nếu đã cài đặt)
            free_qty = 0.0
            if hasattr(product, 'action_get_omnichannel_stock'):
                try:
                    omni_res = product.action_get_omnichannel_stock(sku, mode='online')
                    if omni_res.get('status') == 'success':
                        free_qty = float(omni_res.get('total_available_qty', 0.0))
                    else:
                        free_qty = getattr(product, 'free_qty', product.qty_available - product.outgoing_qty)
                except Exception:
                    free_qty = getattr(product, 'free_qty', product.qty_available - product.outgoing_qty)
            else:
                free_qty = getattr(product, 'free_qty', product.qty_available - product.outgoing_qty)

            if free_qty < qty:
                return {
                    'status': 'error',
                    'code': 'INSUFFICIENT_STOCK',
                    'message': f"Sản phẩm {product.name} ({sku}) không đủ tồn kho khả dụng online. Yêu cầu: {qty}, Khả dụng: {free_qty}"
                }

            order_lines.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': price_unit if price_unit > 0 else product.list_price,
            }))

        if not order_lines:
            return {'status': 'error', 'code': 'EMPTY_ORDER', 'message': 'Đơn hàng không có sản phẩm nào'}

        # 4. Tạo Sale Order trong 1 Atomic Transaction
        try:
            order_vals = {
                'partner_id': partner.id,
                'web_order_ref': client_order_ref,
                'web_payment_status': 'pending',
                'hold_expires_at': hold_deadline,
                'gateway_name': order_data.get('payment_method', ''),
                'order_line': order_lines,
            }
            if order_data.get('warehouse_id'):
                order_vals['warehouse_id'] = order_data['warehouse_id']

            order = self.create(order_vals)

            # Confirm order để Odoo tự động khóa tồn kho (Reserved Quantities)
            order.action_confirm()

            _logger.info(f"[ECOM-BRIDGE] Successfully created atomic order {order.name} (ID: {order.id}) with hold until {hold_deadline}")

            return {
                'status': 'success',
                'is_duplicate': False,
                'odoo_order_id': order.id,
                'odoo_name': order.name,
                'hold_expires_at': fields.Datetime.to_string(hold_deadline),
                'amount_total': order.amount_total,
            }

        except Exception as e:
            _logger.error(f"[ECOM-BRIDGE] Error creating atomic order: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'code': 'SERVER_ERROR',
                'message': f"Lỗi hệ thống khi tạo đơn Odoo: {str(e)}"
            }

    @api.model
    def action_confirm_web_payment(self, payment_data: dict) -> dict:
        """
        Xác nhận thanh toán từ Webhook:
        - Chuyển trạng thái đơn sang 'paid'
        - Tạo Hóa đơn (Account Move) & Post hóa đơn (nếu chính sách xuất hóa đơn cho phép)
        - Nếu chính sách xuất hóa đơn theo giao hàng (Delivered quantities), tạo bút toán Khách trả trước (Prepayment)
        - Ghi nhận Payment vào đúng Payment Journal tương ứng của cổng thanh toán
        """
        odoo_order_id = payment_data.get('odoo_order_id')
        gateway_trans_id = payment_data.get('gateway_transaction_id')
        journal_code = payment_data.get('payment_journal_code', 'BANK')
        amount_paid = float(payment_data.get('amount_paid', 0.0))

        order = self.browse(odoo_order_id)
        if not order.exists():
            return {'status': 'error', 'code': 'ORDER_NOT_FOUND', 'message': f"Đơn hàng ID {odoo_order_id} không tồn tại"}

        # Idempotency: Nếu đơn đã thanh toán rồi, không ghi nhận đè
        if order.web_payment_status == 'paid':
            _logger.info(f"[ECOM-BRIDGE] Order {order.name} was already paid. Skipping duplicate payment.")
            return {'status': 'success', 'message': 'Đơn hàng đã được thanh toán trước đó'}

        try:
            # 1. Cập nhật trạng thái Sale Order
            order.write({
                'web_payment_status': 'paid',
                'gateway_transaction_id': gateway_trans_id,
            })

            # 2. Xác định Payment Journal riêng của cổng
            journal = self.env['account.journal'].search([('code', '=', journal_code)], limit=1)
            if not journal:
                # Fallback về journal loại bank mặc định
                journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

            # 3. Tạo Hóa đơn (Customer Invoice) nếu chính sách cho phép xuất ngay
            invoices = order._create_invoices()
            for inv in invoices:
                inv.action_post()

            if invoices and journal:
                payment_register = self.env['account.payment.register'].with_context(
                    active_model='account.move',
                    active_ids=invoices.ids
                ).create({
                    'journal_id': journal.id,
                    'amount': amount_paid or order.amount_total,
                    'communication': f"{order.name} - {gateway_trans_id}",
                })
                payment_register._create_payments()
                _logger.info(f"[ECOM-BRIDGE] Invoice & Payment registered for {order.name} via {journal_code}")
            elif not invoices and journal:
                # Trường hợp hàng giao sau (Delivered quantities): Ghi nhận bút toán Khách hàng trả trước (Prepayment Nợ 112 / Có 131)
                prepayment_vals = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': order.partner_id.id,
                    'amount': amount_paid or order.amount_total,
                    'journal_id': journal.id,
                    'ref': f"{order.name} - {gateway_trans_id} (Tra truoc)",
                }
                prepayment = self.env['account.payment'].create(prepayment_vals)
                prepayment.action_post()
                _logger.info(f"[ECOM-BRIDGE] Prepayment recorded for {order.name} via {journal_code} (Invoicing delayed until delivery)")

            _logger.info(f"[ECOM-BRIDGE] Payment captured for {order.name} via {journal_code} (Trans: {gateway_trans_id})")
            return {
                'status': 'success',
                'odoo_order_id': order.id,
                'invoice_ids': invoices.ids if invoices else [],
            }

        except Exception as e:
            _logger.error(f"[ECOM-BRIDGE] Error confirming payment for order {odoo_order_id}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'code': 'PAYMENT_CAPTURE_ERROR',
                'message': f"Lỗi ghi nhận thanh toán: {str(e)}"
            }

    @api.model
    def action_cron_release_expired_web_orders(self):
        """
        Scheduled Cron Action (chạy mỗi 5 phút):
        Tìm các đơn hàng online đang pending/unpaid đã quá hạn hold_expires_at
        và tiến hành hủy đơn để giải phóng lượng tồn kho đã reserved (Release Stock).
        """
        now = fields.Datetime.now()
        expired_orders = self.search([
            ('web_payment_status', 'in', ['unpaid', 'pending']),
            ('hold_expires_at', '<=', now),
            ('state', 'in', ['draft', 'sale']),
        ])

        _logger.info(f"[ECOM-BRIDGE-CRON] Found {len(expired_orders)} expired web orders to release.")

        for order in expired_orders:
            try:
                # Hủy đơn hàng -> Odoo tự động hủy Picking và giải phóng Reserved Stock Quants
                order.action_cancel()
                order.write({
                    'web_payment_status': 'cancelled',
                })
                _logger.info(f"[ECOM-BRIDGE-CRON] Order {order.name} has expired. Cancelled and stock released.")
            except Exception as e:
                _logger.error(f"[ECOM-BRIDGE-CRON] Failed to cancel expired order {order.name}: {str(e)}")

        return True
