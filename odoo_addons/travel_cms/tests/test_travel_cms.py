# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestTravelCMS(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category = self.env['travel.category'].create({
            'name': 'Natural Landscapes',
            'slug': 'natural-landscapes',
        })
        self.destination_model = self.env['travel.destination']
        self.place_model = self.env['travel.place']
        self.article_model = self.env['travel.article']

    def test_destination_lifecycle_workflow(self):
        """Test Destination Draft -> In Review -> Approved -> Published state machine."""
        dest = self.destination_model.create({
            'name': 'Da Nang City',
            'slug': 'da-nang-city',
            'latitude': 16.0544,
            'longitude': 108.2022,
        })
        self.assertEqual(dest.state, 'draft')
        self.assertEqual(dest.version, 1)

        # Cannot publish from draft directly
        with self.assertRaises(UserError):
            dest.action_publish()

        # Submit review
        dest.action_submit_review()
        self.assertEqual(dest.state, 'in_review')

        # Approve
        dest.action_approve()
        self.assertEqual(dest.state, 'approved')
        self.assertEqual(dest.reviewer_id, self.env.user)

        # Publish
        dest.action_publish()
        self.assertEqual(dest.state, 'published')
        self.assertEqual(dest.version, 2)
        self.assertTrue(dest.published_at)

    def test_place_lifecycle_and_relationships(self):
        """Test Place creation linked to destination and category."""
        dest = self.destination_model.create({
            'name': 'Ha Long Bay',
            'slug': 'ha-long-bay',
            'latitude': 20.9101,
            'longitude': 107.1839,
        })
        place = self.place_model.create({
            'name': 'Ti Top Island',
            'slug': 'ti-top-island',
            'destination_id': dest.id,
            'category_id': self.category.id,
            'latitude': 20.8587,
            'longitude': 107.0805,
        })
        self.assertEqual(place.destination_id.name, 'Ha Long Bay')
        self.assertEqual(place.state, 'draft')

        # Test place count on destination
        self.assertEqual(dest.place_count, 1)

        # Transition place
        place.action_submit_review()
        place.action_approve()
        place.action_publish()
        self.assertEqual(place.state, 'published')
        self.assertEqual(place.version, 2)

    def test_article_lifecycle(self):
        """Test Article authoring and publishing."""
        dest = self.destination_model.create({
            'name': 'Ninh Binh',
            'slug': 'ninh-binh',
            'latitude': 20.2506,
            'longitude': 105.9745,
        })
        article = self.article_model.create({
            'title': 'Trang An Boat Tour Guide',
            'slug': 'trang-an-boat-tour-guide',
            'destination_id': dest.id,
            'body': '<p>Everything you need to know about Trang An.</p>',
        })
        self.assertEqual(article.state, 'draft')
        article.action_submit_review()
        article.action_approve()
        article.action_publish()
        self.assertEqual(article.state, 'published')
        self.assertEqual(article.version, 2)
