# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestTravelCRM(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner_model = self.env['res.partner']
        self.lead_model = self.env['crm.lead']
        self.destination = self.env['travel.destination'].create({
            'name': 'Da Lat',
            'slug': 'da-lat',
            'latitude': 11.9404,
            'longitude': 108.4583,
        })

    def test_traveler_deduplication_by_phone(self):
        """Test deduplication matches existing customer by phone number variations (+84, 0, spaces)."""
        p1 = self.partner_model.find_or_create_traveler(
            name="Tran Van B",
            phone="0912345678",
            email="tran.b@example.com",
            provider="website"
        )

        # Same customer submits from Facebook with +84 formatting
        p2 = self.partner_model.find_or_create_traveler(
            name="Tran Van B",
            phone="+84 912 345 678",
            email="tran.b.work@example.com",
            provider="facebook"
        )
        self.assertEqual(p1.id, p2.id, "Deduplication must match same partner by normalized phone")

    def test_traveler_deduplication_by_email(self):
        """Test deduplication matches existing customer by case-insensitive email."""
        p1 = self.partner_model.find_or_create_traveler(
            name="Le Thi C",
            email="lethic@travel.vn",
            provider="website"
        )
        p2 = self.partner_model.find_or_create_traveler(
            name="Le C",
            email="  LETHIC@TRAVEL.VN  ",
            provider="zalo"
        )
        self.assertEqual(p1.id, p2.id, "Deduplication must match same partner by case-insensitive email")

    def test_create_from_inquiry_payload(self):
        """Test full inquiry creation into CRM Lead with destination interest and channel attribution."""
        payload = {
            'source': 'facebook',
            'inquiry_type': 'tour_booking',
            'message': 'I would like to book a 3-day tour in Da Lat for my family.',
            'customer': {
                'name': 'Nguyen Hoang',
                'phone': '0988776655',
                'email': 'hoang.nguyen@test.com',
                'identity_provider': 'facebook',
                'public_customer_id': 'f7d2f9a2-4a4b-4f9e-8c31-9f2257d90391'
            },
            'interest': {
                'destination_slug': 'da-lat',
                'travel_date': '2026-11-20',
                'traveler_count': 4,
            },
            'source_metadata': {
                'channel': 'facebook',
                'external_lead_id': 'fb_msg_10928374',
            }
        }

        lead = self.lead_model.create_from_inquiry_payload(payload)

        self.assertTrue(lead)
        self.assertEqual(lead.partner_id.name, 'Nguyen Hoang')
        self.assertEqual(lead.partner_id.public_customer_id, 'f7d2f9a2-4a4b-4f9e-8c31-9f2257d90391')
        self.assertEqual(lead.source_system, 'facebook')
        self.assertEqual(lead.inquiry_type, 'tour_booking')
        self.assertEqual(lead.destination_interest_id, self.destination)
        self.assertEqual(lead.traveler_count, 4)
        self.assertEqual(lead.external_lead_id, 'fb_msg_10928374')
