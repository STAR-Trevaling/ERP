# -*- coding: utf-8 -*-
{
    'name': 'Custom Inventory Core (Omnichannel & Variant Matrix)',
    'version': '18.0.1.0.0',
    'summary': 'Quản trị Tồn kho Đa điểm Omnichannel và Biến thể Sản phẩm Thời trang Odoo 18',
    'description': """
        Phân hệ Quản trị Tồn kho Đa điểm cho Bán lẻ Đa kênh (Omnichannel Retail):
        - Cấu trúc Kho Tổng (Central DC) ↔ Cửa hàng POS (Retail Stores).
        - Thiết lập mức tồn an toàn (Safety Stock Buffer) tại quầy tránh xung đột bán tại quầy và online.
        - API truy vấn tồn kho đa điểm và giữ tồn trực tiếp theo từng địa điểm chỉ định.
        - Khởi tạo danh mục Biến thể Thuộc tính (Màu sắc, Kích thước) chuẩn thời trang / gia dụng.
    """,
    'category': 'Inventory/Inventory',
    'author': 'ERP Architect Team',
    'website': 'https://github.com/retail-erp-vn',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'stock',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/stock_warehouse_data.xml',
        'data/product_attribute_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
