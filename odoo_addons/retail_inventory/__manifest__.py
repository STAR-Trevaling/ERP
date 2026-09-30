# -*- coding: utf-8 -*-
{
    'name': "Retail Inventory & Stock Reservation",
    'version': '18.0.1.0.0',
    'category': 'Inventory/Retail',
    'summary': "Omnichannel Retail Inventory Management with 15-Minute Stock Reservation and Safety Buffer",
    'description': """
Omnichannel Retail Inventory Management for Odoo 18
====================================================
- Central DC vs Retail Stores multi-location support.
- 15-Minute soft stock reservation for online checkouts with PostgreSQL row-level locking (SELECT FOR UPDATE).
- Safety buffer percentages for retail stores to prevent cross-channel overselling.
- Automatic background release cron job for expired reservations.
- Single Source of Truth for inventory valuation adhering to Vietnamese Accounting Standards (VAS).
    """,
    'author': "Retail ERP Architect",
    'website': "https://github.com/huynguyen2k5/ERP",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'stock',
        'stock_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/stock_reservation_views.xml',
        'views/stock_location_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
