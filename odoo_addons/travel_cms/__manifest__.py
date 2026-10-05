# -*- coding: utf-8 -*-
{
    'name': "Star Travels - CMS Content Authoring",
    'version': '18.0.1.0.0',
    'category': 'Travel/CMS',
    'summary': "Content Authoring, Editorial Workflow & Publishing Engine for Destinations, Places & Articles",
    'description': """
Star Travels CMS Content Authoring Module
=========================================
- Editorial workflow for Destinations, Places, and Travel Articles.
- 5-stage lifecycle: Draft -> In Review -> Approved -> Published -> Archived.
- Content versioning and revision tracking.
- Outbox event trigger on publication to sync with public serving platform.
    """,
    'author': "Star Travels ERP Architect",
    'website': "https://star-travels.com",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'travel_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/travel_destination_views.xml',
        'views/travel_place_views.xml',
        'views/travel_article_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
