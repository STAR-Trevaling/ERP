from odoo.tests.common import TransactionCase


class TestTravelCRM(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner_model = self.env['res.partner']
        self.lead_model = self.env['crm.lead']
        self.destination = self.env['travel.destination'].create({
            'name': 'Da Lat Test',
            'slug': 'test-da-lat',
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
                'destination_slug': 'test-da-lat',
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

    def test_create_from_inquiry_with_marketing_utm_attribution(self):
        """Test inquiry creation with full marketing UTM parameters and ad click IDs."""
        payload = {
            'source': 'website',
            'inquiry_type': 'consultation',
            'message': 'Can you advice tour to Da Lat?',
            'customer': {
                'name': 'Pham Thi D',
                'phone': '0901234567',
                'email': 'd.pham@travel.vn',
            },
            'interest': {
                'destination_slug': 'test-da-lat',
            },
            'marketing': {
                'channel': 'website',
                'utm_source': 'google_ads',
                'utm_medium': 'cpc',
                'utm_campaign': 'autumn_promotion_2026',
                'utm_term': 'du lich da lat 3 ngay 2 dem',
                'utm_content': 'search_ad_v2',
                'gclid': 'Cj0KCQjwx_test_gclid_123',
                'fbclid': 'IwAR3_test_fbclid_456',
                'landing_page': 'https://startravels.vn/destinations/da-lat',
                'referrer': 'https://www.google.com.vn/',
            },
        }

        lead = self.lead_model.create_from_inquiry_payload(payload)

        self.assertTrue(lead)
        self.assertEqual(lead.source_id.name.lower(), 'google_ads')
        self.assertEqual(lead.medium_id.name.lower(), 'cpc')
        self.assertEqual(lead.campaign_id.name.lower(), 'autumn_promotion_2026')
        self.assertEqual(lead.utm_term, 'du lich da lat 3 ngay 2 dem')
        self.assertEqual(lead.utm_content, 'search_ad_v2')
        self.assertEqual(lead.gclid, 'Cj0KCQjwx_test_gclid_123')
        self.assertEqual(lead.fbclid, 'IwAR3_test_fbclid_456')
        self.assertEqual(lead.landing_page_url, 'https://startravels.vn/destinations/da-lat')
        self.assertEqual(lead.referrer_url, 'https://www.google.com.vn/')

    def test_utm_auto_discovery_deduplicates_existing_records(self):
        """Test case-insensitive UTM auto-discovery reuses existing record without duplication."""
        existing_campaign = self.env['utm.campaign'].create({'name': 'Winter_Wonderland_2026'})

        payload = {
            'customer': {'name': 'Vu Van E', 'phone': '0977112233'},
            'marketing': {
                'utm_campaign': 'winter_wonderland_2026',  # lowercase variation
                'utm_source': 'facebook_ads',
            },
        }

        lead = self.lead_model.create_from_inquiry_payload(payload)
        self.assertEqual(lead.campaign_id.id, existing_campaign.id, "Must match existing campaign ignoring case")
