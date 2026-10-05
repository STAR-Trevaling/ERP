# -*- coding: utf-8 -*-
{
    'name': "Star Travels - Luxury Admin Theme",
    'version': '18.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': "Modern Star Travels Design System for Odoo 18 (Plus Jakarta Sans, Indigo & Teal Palette, Rounded Cards)",
    'description': """
Star Travels Luxury Admin Theme
===============================
- Mirrors the visual language of the Star Travels Admin Portal.
- Color Tokens: Indigo Primary (#5932EA), Brand Teal (#0098A2), Canvas (#FAFBFF), Text (#292D32).
- Typography: Plus Jakarta Sans / Poppins font integration.
- UI Enhancements: Rounded luxury cards (24px radius), soft shadows, pill status badges, modern form sheets.
    """,
    'author': "Star Travels ERP Architect",
    'website': "https://star-travels.com",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'travel_core',
    ],
    'data': [
        'views/webclient_templates.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
}
