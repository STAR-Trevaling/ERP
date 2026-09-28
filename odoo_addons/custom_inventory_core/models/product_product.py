# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def action_get_omnichannel_stock(self, sku: str, mode: str = 'online', location_id: int = None):
        """
        API JSON-RPC phục vụ Backend Middleware & POS:
        Hỗ trợ đa chế độ nghiệp vụ (Multi-Mode Strategy):
        - 'online': E-commerce (lọc is_omnichannel_enabled, trừ safety_stock_buffer, ưu tiên Kho Tổng).
        - 'pos': Bán tại quầy (ưu tiên location_id chỉ định lên đầu, KHÔNG trừ buffer tại quầy hiện tại).
        - 'b2b': Bán buôn (chỉ lấy Kho Tổng / DC, không trừ buffer).
        - 'audit': Kế toán / Kiểm kê (toàn bộ kho nội bộ, xem số liệu thô on_hand, reserved, free_qty).
        """
        clean_sku = sku.strip().upper() if sku else ''
        product = self.search([('default_code', '=', clean_sku)], limit=1)
        if not product:
            return {
                'status': 'error',
                'message': f'SKU {sku} không tồn tại trong hệ thống',
                'mode': mode,
                'data': []
            }

        domain = [
            ('product_id', '=', product.id),
            ('location_id.usage', '=', 'internal')
        ]

        if mode == 'online':
            domain.append(('location_id.is_omnichannel_enabled', '=', True))
        elif mode == 'b2b':
            domain.append(('location_id.warehouse_type', '=', 'central_dc'))

        quants = self.env['stock.quant'].search(domain)

        stock_data = []
        for q in quants:
            loc = q.location_id
            free_qty = max(0.0, q.quantity - q.reserved_quantity)

            # Tính toán lượng khả dụng theo mode
            if mode == 'pos':
                # Tại quầy POS: Nếu là chính cửa hàng hiện tại, được bán hết (buffer = 0)
                is_current_pos = bool(location_id and loc.id == location_id)
                buffer = 0.0 if is_current_pos else (loc.safety_stock_buffer or 0.0)
                priority = 0 if is_current_pos else (loc.allocation_priority or 10)
            elif mode == 'online':
                buffer = loc.safety_stock_buffer or 0.0
                priority = loc.allocation_priority or 10
            elif mode == 'b2b':
                buffer = 0.0
                priority = 1
            else:  # 'audit'
                buffer = 0.0
                priority = loc.id

            avail_qty = max(0.0, free_qty - buffer)

            stock_data.append({
                'location_id': loc.id,
                'location_code': loc.complete_name or loc.name,
                'location_name': loc.name,
                'warehouse_type': loc.warehouse_type or 'retail_store',
                'priority': priority,
                'safety_stock_buffer': buffer,
                'on_hand_qty': q.quantity,
                'reserved_qty': q.reserved_quantity,
                'free_qty': free_qty,
                'available_qty': avail_qty,
                'available_for_online': avail_qty,  # Backward compatibility
            })

        # Sắp xếp: Kho ưu tiên nhỏ nhất trước, sau đó đến available_qty giảm dần
        stock_data.sort(key=lambda x: (x['priority'], -x['available_qty']))

        total_avail = sum(item['available_qty'] for item in stock_data)

        return {
            'status': 'success',
            'mode': mode,
            'product_id': product.id,
            'sku': product.default_code,
            'name': product.display_name,
            'total_available_qty': total_avail,
            'total_available_online': total_avail,
            'data': stock_data
        }

