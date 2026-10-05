# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestTravelPartner(TransactionCase):

    def setUp(self):
        super().setUp()
        self.app_model = self.env['travel.partner.application']

    def test_partner_application_approval_lifecycle(self):
        """Test submitted -> under_review -> approved transitions and partner creation."""
        app = self.app_model.create({
            'business_name': 'Hoi An Eco River Resort',
            'email': 'contact@hoianecoresort.vn',
            'phone': '0905112233',
            'website': 'https://hoianecoresort.vn',
            'message': 'We operate boutique eco-lodges along the Thu Bon River.',
        })
        self.assertEqual(app.state, 'submitted')

        # Cannot approve from submitted directly
        with self.assertRaises(UserError):
            app.action_approve()

        # Start review
        app.action_start_review()
        self.assertEqual(app.state, 'under_review')

        # Approve
        app.action_approve()
        self.assertEqual(app.state, 'approved')
        self.assertEqual(app.reviewed_by_id, self.env.user)
        self.assertTrue(app.partner_id)
        self.assertEqual(app.partner_id.name, 'Hoi An Eco River Resort')
        self.assertTrue(app.partner_id.is_company)
        self.assertEqual(app.organization_slug, 'hoi-an-eco-river-resort')

    def test_partner_application_rejection(self):
        """Test rejection requires reason and marks state as rejected."""
        app = self.app_model.create({
            'business_name': 'Suspicious Fake Hotel',
            'email': 'fake@example.com',
        })
        app.action_start_review()

        # Cannot reject without rejection_reason
        with self.assertRaises(UserError):
            app.action_reject()

        app.rejection_reason = "Unable to verify business registration documents."
        app.action_reject()
        self.assertEqual(app.state, 'rejected')
        self.assertEqual(app.rejection_reason, "Unable to verify business registration documents.")
