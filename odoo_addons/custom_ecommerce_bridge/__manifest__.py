# -*- coding: utf-8 -*-
{
    'name': 'Custom E-commerce Bridge & Atomic Stock Lock',
    'version': '18.0.1.0.0',
    'summary': 'Thin custom integration bridge for FastAPI & E-commerce with atomic stock reservation',
    'description': """
        Module tích hợp Odoo 18 cho Website E-commerce:
        - Tạo đơn hàng và khóa giữ tồn kho (Stock Reservation) trong 1 Transaction nguyên khối.
        - Tự động hủy đơn và giải phóng tồn kho khi quá hạn (15 phút) qua Cron Job.
        - Ghi nhận thanh toán từ Webhook vào đúng Payment Journal của từng cổng (VNPay, MoMo, VietQR).
        - Idempotency & an toàn dữ liệu kế toán VAS.
    """,
    'category': 'Sales/Integration',
    'author': 'ERP Architect Team',
    'website': 'https://github.com/retail-erp-vn',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
