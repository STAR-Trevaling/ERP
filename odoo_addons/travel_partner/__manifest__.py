# -*- coding: utf-8 -*-
{
    'name': "Star Travels - Partner Operations",
    'version': '18.0.1.0.0',
    'category': 'Travel/Partner',
    'summary': "Partner Onboarding Applications, Verification & Approval Workflow",
    'description': """
Star Travels Partner Operations Module
======================================
- Partner Application State Machine: Submitted -> Under Review -> Approved / Rejected.
- Staff verification, document review, and internal notes.
- Automatic creation of res.partner organization upon approval.
- Emits partner.approved outbox event to activate partner profile on the public platform.
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
        'views/partner_application_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
