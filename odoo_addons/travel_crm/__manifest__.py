# -*- coding: utf-8 -*-
{
    'name': "Star Travels - CRM & Inquiries",
    'version': '18.0.1.0.0',
    'category': 'Travel/CRM',
    'summary': "Multi-channel Travel Inquiry, Customer Deduplication & Lead Lifecycle for Star Travels",
    'description': """
Star Travels CRM & Inquiry Management
=====================================
- Extends standard Odoo CRM (crm.lead, res.partner, utm.source).
- Multi-channel source attribution: Website, Facebook, Zalo, Pancake, OTA, AI Assistant.
- Smart Customer Deduplication (Phone, Email, Public UUID).
- Inquiries linked directly to Destinations and Places of interest.
    """,
    'author': "Star Travels ERP Architect",
    'website': "https://star-travels.com",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'crm',
        'travel_core',
        'travel_cms',
    ],
    'data': [
        'views/crm_lead_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
