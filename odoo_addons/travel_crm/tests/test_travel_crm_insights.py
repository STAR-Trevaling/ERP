from odoo.tests.common import TransactionCase


class TestTravelCrmInsights(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lead_model = cls.env['crm.lead']
        cls.report_model = cls.env['travel.crm.insight.report']
        cls.destination_model = cls.env['travel.destination']
        cls.stage_model = cls.env['crm.stage']
        cls.campaign_model = cls.env['utm.campaign']
        cls.source_model = cls.env['utm.source']
        cls.medium_model = cls.env['utm.medium']

        # Setup Test Master Data
        cls.dest_halong = cls.destination_model.create({
            'name': 'Vịnh Hạ Long',
            'slug': 'test-vinh-ha-long',
            'latitude': 20.9101,
            'longitude': 107.1839,
        })
        cls.dest_phuquoc = cls.destination_model.create({
            'name': 'Đảo Phú Quốc',
            'slug': 'test-phu-quoc',
            'latitude': 10.2899,
            'longitude': 103.9840,
        })

        cls.campaign_summer = cls.campaign_model.create({'name': 'He Ruc Ro 2026'})
        cls.source_fb_ads = cls.source_model.create({'name': 'Facebook_Ads'})
        cls.source_google = cls.source_model.create({'name': 'Google_Search'})
        cls.medium_cpc = cls.medium_model.create({'name': 'cpc'})

        # Stages
        cls.stage_won = cls.stage_model.search([('is_won', '=', True)], limit=1)
        if not cls.stage_won:
            cls.stage_won = cls.stage_model.create({
                'name': 'Thành công (Won)',
                'is_won': True,
                'sequence': 99,
            })

        cls.stage_new = cls.stage_model.search([('is_won', '=', False)], limit=1)
        if not cls.stage_new:
            cls.stage_new = cls.stage_model.create({
                'name': 'Mới tiếp nhận',
                'is_won': False,
                'sequence': 1,
            })

    def test_01_insight_report_channel_and_won_aggregation(self):
        """Test report accurately captures omni-channel leads, revenue and won conversions."""
        # 1. Lead from Website (Won)
        lead_won = self.lead_model.create({
            'name': '[WEB] Tour Hạ Long 3N2D VIP',
            'source_system': 'website',
            'inquiry_type': 'tour_booking',
            'destination_interest_id': self.dest_halong.id,
            'traveler_count': 4,
            'expected_revenue': 20000000.0,
            'probability': 100.0,
            'stage_id': self.stage_won.id,
            'campaign_id': self.campaign_summer.id,
            'source_id': self.source_google.id,
            'medium_id': self.medium_cpc.id,
            'gclid': 'GCLID_TEST_12345',
        })

        # 2. Lead from Facebook (In Progress)
        lead_open = self.lead_model.create({
            'name': '[FB] Tư vấn combo Phú Quốc 4N3D',
            'source_system': 'facebook',
            'inquiry_type': 'consultation',
            'destination_interest_id': self.dest_phuquoc.id,
            'traveler_count': 2,
            'expected_revenue': 12000000.0,
            'probability': 50.0,
            'stage_id': self.stage_new.id,
            'campaign_id': self.campaign_summer.id,
            'source_id': self.source_fb_ads.id,
            'medium_id': self.medium_cpc.id,
            'fbclid': 'FBCLID_TEST_67890',
        })

        # Search report records for these leads
        report_won = self.report_model.search([('lead_id', '=', lead_won.id)])
        self.assertTrue(report_won.exists(), "Report view must reflect the created won lead")
        self.assertEqual(report_won.source_system, 'website')
        self.assertTrue(report_won.is_won, "Report record must be marked as Won")
        self.assertEqual(report_won.won_revenue, 20000000.0, "Won revenue must match expected revenue for won lead")
        self.assertEqual(report_won.traveler_count, 4)
        self.assertEqual(report_won.revenue_per_traveler, 5000000.0, "Revenue per traveler = 20M / 4 pax = 5M")
        self.assertTrue(report_won.has_gclid, "Must detect Google Ads click ID")
        self.assertEqual(report_won.ad_network, 'google')

        report_open = self.report_model.search([('lead_id', '=', lead_open.id)])
        self.assertTrue(report_open.exists(), "Report view must reflect the created open lead")
        self.assertEqual(report_open.source_system, 'facebook')
        self.assertFalse(report_open.is_won, "Open lead must not be marked as Won")
        self.assertEqual(report_open.won_revenue, 0.0, "Won revenue must be 0 for open lead")
        self.assertEqual(report_open.expected_revenue, 12000000.0)
        self.assertEqual(report_open.traveler_count, 2)
        self.assertEqual(report_open.revenue_per_traveler, 6000000.0)
        self.assertTrue(report_open.has_fbclid, "Must detect Facebook Ads click ID")
        self.assertEqual(report_open.ad_network, 'facebook')

    def test_02_destination_demand_and_grouping(self):
        """Test destination demand distribution across different destinations."""
        self.lead_model.create({
            'name': '[ZALO] Tour Hạ Long Khách Đoàn',
            'source_system': 'zalo',
            'inquiry_type': 'tour_booking',
            'destination_interest_id': self.dest_halong.id,
            'traveler_count': 10,
            'expected_revenue': 50000000.0,
            'stage_id': self.stage_new.id,
        })

        reports_halong = self.report_model.search([('destination_interest_id', '=', self.dest_halong.id)])
        total_pax = sum(reports_halong.mapped('traveler_count'))
        self.assertGreaterEqual(total_pax, 10, "Total traveler count for Ha Long must aggregate correctly")

    def test_03_read_access_for_sales_users(self):
        """Verify report model is accessible by internal users for read."""
        has_read = self.report_model.has_access('read')
        self.assertTrue(has_read, "Sales / internal users must have read access to the insight report")
