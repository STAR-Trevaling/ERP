# -*- coding: utf-8 -*-
{
    'name': "Star Travels - Integration Backbone",
    'version': '18.0.1.0.0',
    'category': 'Travel/Integration',
    'summary': "REST Inbound Webhooks, HMAC-SHA256 Security, Transactional Outbox & Idempotent Event Log",
    'description': """
Star Travels Integration Backbone Module
========================================
- REST Inbound Controller (/api/v1/travel/inquiry, /partner-application, /health).
- Timing-safe HMAC-SHA256 signature verification & Bearer API Key authentication.
- Strict Inbound Idempotency tracking (travel.integration.event) preventing duplicate leads.
- Transactional Outbox pattern (travel.integration.outbox) with exponential backoff retries.
- Background worker scheduled action for outbox webhook dispatching.
- Internal Operations Monitoring Dashboard with manual retry triggers.
    """,
    'author': "Star Travels ERP Architect",
    'website': "https://star-travels.com",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'travel_core',
        'travel_crm',
        'travel_cms',
        'travel_partner',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/integration_event_views.xml',
        'views/integration_outbox_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
