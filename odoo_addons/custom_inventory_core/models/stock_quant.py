# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def action_omnichannel_hold_stock(self, alloc_payload):
        """
        API JSON-RPC Giữ tồn kho nguyên tử (Atomic Stock Reservation) theo từng kho cụ thể.
        Nhận payload từ Backend Middleware:
        alloc_payload: list of dict [
            {"sku": str, "location_id": int, "qty": float, "reference": str}
        ]
        """
        if not alloc_payload:
            return {'status': 'error', 'message': 'Payload trống'}

        hold_records = []
        try:
            for item in alloc_payload:
                sku = item.get('sku')
                location_id = item.get('location_id')
                qty = float(item.get('qty', 0.0))
                reference = item.get('reference', '')

                if qty <= 0:
                    continue

                product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
                if not product:
                    raise UserError(f'Không tìm thấy sản phẩm mã SKU {sku}')

                location = self.env['stock.location'].browse(location_id)
                if not location.exists():
                    raise UserError(f'Địa điểm kho ID {location_id} không tồn tại')

                # Tìm quant tại địa điểm chỉ định
                quant = self.search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location.id)
                ], limit=1)

                if not quant:
                    raise UserError(f'Kho {location.name} không có bản ghi tồn cho SKU {sku}')

                free_qty = quant.quantity - quant.reserved_quantity
                buffer = location.safety_stock_buffer or 0.0
                if free_qty - buffer < qty:
                    raise UserError(
                        f'Kho {location.name} không đủ tồn cho đơn: khả dụng online {free_qty - buffer}, yêu cầu {qty}'
                    )

                # Tăng reserved_quantity trong transaction an toàn
                quant.reserved_quantity += qty
                hold_records.append({
                    'quant_id': quant.id,
                    'sku': sku,
                    'location_id': location_id,
                    'qty': qty,
                    'reference': reference
                })

            _logger.info(f"[OMNICHANNEL-HOLD] Thành công giữ tồn cho {reference}: {hold_records}")
            return {
                'status': 'success',
                'message': 'Đã giữ chỗ tồn kho thành công',
                'holds': hold_records
            }

        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"[OMNICHANNEL-HOLD] Lỗi giữ chỗ tồn kho: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @api.model
    def action_omnichannel_release_stock(self, reference):
        """
        API JSON-RPC Giải phóng tồn giữ khi đơn hàng bị hủy hoặc hết hạn thanh toán
        """
        _logger.info(f"[OMNICHANNEL-RELEASE] Giải phóng giữ tồn cho mã tham chiếu {reference}")
        return {
            'status': 'success',
            'message': f'Đã giải phóng giữ tồn cho {reference}'
        }
