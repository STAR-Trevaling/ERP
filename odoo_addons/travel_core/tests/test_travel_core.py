# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
import psycopg2


class TestTravelCore(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category_model = self.env['travel.category']
        self.amenity_model = self.env['travel.amenity']

    def test_category_creation_and_slug_generation(self):
        """Test category creation and slug generation."""
        category = self.category_model.create({
            'name': 'Scenic Nature & Lakes',
            'slug': 'scenic-nature-lakes',
            'icon': 'mountain',
        })
        self.assertEqual(category.name, 'Scenic Nature & Lakes')
        self.assertEqual(category.slug, 'scenic-nature-lakes')
        self.assertTrue(category.active)

    def test_category_slug_uniqueness(self):
        """Test category slug unique constraint."""
        self.category_model.create({
            'name': 'Historical Sites',
            'slug': 'historical-sites',
        })
        with self.assertRaises(psycopg2.IntegrityError):
            with self.cr.savepoint():
                self.category_model.create({
                    'name': 'Other Historical Sites',
                    'slug': 'historical-sites',
                })

    def test_amenity_creation(self):
        """Test amenity creation and code uniqueness."""
        amenity = self.amenity_model.create({
            'name': 'Free High Speed Wi-Fi',
            'code': 'free_wifi',
            'category': 'general',
            'icon': 'wifi',
        })
        self.assertEqual(amenity.code, 'free_wifi')
        with self.assertRaises(psycopg2.IntegrityError):
            with self.cr.savepoint():
                self.amenity_model.create({
                    'name': 'Duplicate Wi-Fi',
                    'code': 'free_wifi',
                })
