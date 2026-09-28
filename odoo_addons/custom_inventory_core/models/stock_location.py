# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    warehouse_type = fields.Selection(
        selection=[
            ('central_dc', 'Kho Tổng Phân Phối (Central DC)'),
            ('retail_store', 'Cửa hàng Bán lẻ (Retail Store / POS)'),
            ('transit', 'Kho Trung chuyển'),
        ],
        string="Phân loại Kho Omnichannel",
        default='retail_store',
        help="Kho Tổng ưu tiên số 1 cho đơn Website; Cửa hàng phục vụ khách quầy POS."
    )
    is_omnichannel_enabled = fields.Boolean(
        string="Cho phép bán Online",
        default=True,
        help="Nếu bật, tồn kho tại địa điểm này được phép cộng vào tồn khả dụng trên Website"
    )
    safety_stock_buffer = fields.Float(
        string="Lượng đệm an toàn (Safety Buffer)",
        default=0.0,
        help="Số lượng giữ lại tại cửa hàng cho khách mua trực tiếp, không đưa lên Web bán"
    )
    allocation_priority = fields.Integer(
        string="Độ ưu tiên xuất kho",
        default=10,
        help="Số càng nhỏ độ ưu tiên càng cao (Kho Tổng = 1, Cửa hàng = 10)"
    )
