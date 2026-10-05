# -*- coding: utf-8 -*-
{
    'name': "Star Travels - Core Foundation",
    'version': '18.0.1.0.0',
    'category': 'Travel/Core',
    'summary': "Foundational models, taxonomy, and integration settings for Star Travels ERP",
    'description': """
Star Travels Core Foundation Module
===================================
- Master categories, taxonomy, and amenities for travel entities.
- Top-level Star Travels navigation menus.
- System-wide integration settings (Public API URLs, Webhook Secrets, API Keys).
    """,
    'author': "Star Travels ERP Architect",
    'website': "https://star-travels.com",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/travel_security.xml',
        'security/ir.model.access.csv',
        'views/travel_menus.xml',
        'views/travel_category_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
