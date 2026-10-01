# -*- coding: utf-8 -*-
{
    'name': "B2B Manufacturing Suite Bundle",
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/B2B',
    'summary': "Comprehensive Odoo 18 B2B Manufacturing Suite with Responsive UX/UI & Sleek Theme",
    'description': """
B2B Manufacturing Enterprise Suite for Odoo 18
==============================================
Automatically provisions the complete core manufacturing and supply chain modules:
- Sales Management (B2B Quotations with flexible pricing)
- Purchase Management (Raw materials, additives, vendor management)
- Inventory & Warehouse (Multi-location, Lot tracking, Barcode scanning)
- Manufacturing (MRP, Work Centers, Routing, BOMs)
- Maintenance (Factory machinery and equipment preventive maintenance)
- Invoicing & Accounting (B2B receivables, payables, VAT invoices)
- Web Responsive (OCA App Drawer & Mobile-first navigation)
- Theme B2B Sleek (UI/UX Pro Max design tokens, Plus Jakarta Sans, Zero AI-Slop)
    """,
    'author': "B2B ERP Architect",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web_responsive',
        'b2b_theme_sleek',
        'sale_management',
        'purchase',
        'stock',
        'mrp',
        'maintenance',
        'account',
        'retail_inventory',
    ],
    'data': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
