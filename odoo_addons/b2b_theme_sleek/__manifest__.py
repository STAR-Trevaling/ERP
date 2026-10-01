# -*- coding: utf-8 -*-
{
    'name': "B2B Manufacturing Sleek Theme",
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': "Modern, Smooth & Ultra-clean UI/UX for B2B Manufacturing (Zero AI-Slop, Plus Jakarta Sans, Bento Grid)",
    'description': """
B2B Manufacturing Sleek Theme for Odoo 18
=========================================
- Typography: Plus Jakarta Sans & JetBrains Mono for manufacturing data.
- Refined Color Palette: Slate 900 & Indigo 600 with clean, breathable card sheets.
- Modern Controls: Pill-shaped search bar, elevated buttons with smooth lift, sticky table headers.
- Enhanced App Drawer: Premium glassmorphic backdrop blur and smooth icon animations.
- Eliminates AI-slop: High information density with zero clutter.
    """,
    'author': "B2B ERP Architect",
    'license': 'LGPL-3',
    'depends': [
        'web',
        'web_responsive',
    ],
    'data': [
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'b2b_theme_sleek/static/src/scss/variables.scss',
            'b2b_theme_sleek/static/src/scss/theme.scss',
            'b2b_theme_sleek/static/src/scss/app_drawer.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
