import psycopg2

from odoo.tests.common import TransactionCase


class TestTravelCore(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category_model = self.env['travel.category']
        self.amenity_model = self.env['travel.amenity']

    def test_category_creation_and_slug_generation(self):
        """Test category creation and slug generation."""
        category = self.category_model.create({
            'name': 'Scenic Nature & Lakes Test',
            'slug': 'test-scenic-nature-lakes',
            'icon': 'mountain',
        })
        self.assertEqual(category.name, 'Scenic Nature & Lakes Test')
        self.assertEqual(category.slug, 'test-scenic-nature-lakes')
        self.assertTrue(category.active)

    def test_category_slug_uniqueness(self):
        """Test category slug unique constraint."""
        self.category_model.create({
            'name': 'Historical Sites Test',
            'slug': 'test-historical-sites',
        })
        with self.assertRaises(psycopg2.IntegrityError), self.cr.savepoint():
            self.category_model.create({
                'name': 'Other Historical Sites Test',
                'slug': 'test-historical-sites',
            })

    def test_amenity_creation(self):
        """Test amenity creation and code uniqueness."""
        amenity = self.amenity_model.create({
            'name': 'Free High Speed Wi-Fi Test',
            'code': 'test_free_wifi',
            'category': 'general',
            'icon': 'wifi',
        })
        self.assertEqual(amenity.code, 'test_free_wifi')
        with self.assertRaises(psycopg2.IntegrityError), self.cr.savepoint():
            self.amenity_model.create({
                'name': 'Duplicate Wi-Fi Test',
                'code': 'test_free_wifi',
            })
