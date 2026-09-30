# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestStockReservation(TransactionCase):
    """
    Test suite for retail stock reservation, locking, and VAS accounting integration.
    Follows strict TDD Red-Green-Refactor cycle.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Reservation = cls.env['retail.stock.reservation']
        cls.Quant = cls.env['stock.quant']
        cls.Location = cls.env['stock.location']
        cls.Product = cls.env['product.product']

        # Setup standard retail stock location
        cls.stock_location = cls.Location.create({
            'name': 'Retail Test Floor',
            'usage': 'internal',
            'is_retail_store': True,
            'safety_buffer_pct': 10.0,  # 10% safety buffer
        })

        # Setup product
        cls.product = cls.Product.create({
            'name': 'Test Retail Polo Shirt',
            'type': 'consu',  # Odoo 18 uses 'consu' with is_storable=True if storable
            'is_storable': True,
            'default_code': 'POLO-TEST-001',
            'list_price': 350000.0,
            'standard_price': 180000.0,
        })

        # Add 10 units to stock location
        cls.Quant.create({
            'product_id': cls.product.id,
            'location_id': cls.stock_location.id,
            'quantity': 10.0,
        })

    def test_01_successful_reservation(self):
        """Test reserving stock within available limits succeeds with active state"""
        reservation = self.Reservation.create_reservation(
            product_id=self.product.id,
            location_id=self.stock_location.id,
            quantity=3.0,
            order_reference='ORD-ONLINE-001',
            duration_minutes=15,
        )

        self.assertTrue(reservation)
        self.assertEqual(reservation.state, 'active')
        self.assertEqual(reservation.quantity, 3.0)
        self.assertTrue(reservation.reserved_until > fields.Datetime.now())

    def test_02_oversell_rejection(self):
        """Test attempting to reserve more than available physical stock raises ValidationError"""
        with self.assertRaises(ValidationError):
            self.Reservation.create_reservation(
                product_id=self.product.id,
                location_id=self.stock_location.id,
                quantity=15.0,  # Only 10 available
                order_reference='ORD-OVERSELL-001',
                duration_minutes=15,
            )

    def test_03_safety_buffer_protection(self):
        """
        Total stock: 10 units. Safety buffer: 10% (= 1 unit).
        Maximum reservable online: 9 units.
        Attempting to reserve 9.5 units must be rejected.
        """
        with self.assertRaises(ValidationError):
            self.Reservation.create_reservation(
                product_id=self.product.id,
                location_id=self.stock_location.id,
                quantity=9.5,
                order_reference='ORD-BUFFER-001',
                duration_minutes=15,
            )

    def test_04_cron_release_expired_reservation(self):
        """Test periodic cron automatically releases reservations that exceed the 15-minute window"""
        past_time = fields.Datetime.now() - timedelta(minutes=20)
        reservation = self.Reservation.create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 2.0,
            'order_reference': 'ORD-EXPIRED-001',
            'reserved_until': past_time,
            'state': 'active',
        })

        # Run cron method
        self.Reservation._cron_release_expired_reservations()

        reservation.invalidate_recordset()
        self.assertEqual(reservation.state, 'released', "Expired reservation should be transitioned to 'released'")

    def test_05_consume_reservation(self):
        """Test consuming an active reservation when checkout is confirmed"""
        reservation = self.Reservation.create_reservation(
            product_id=self.product.id,
            location_id=self.stock_location.id,
            quantity=2.0,
            order_reference='ORD-PAID-001',
            duration_minutes=15,
        )

        reservation.action_consume()
        self.assertEqual(reservation.state, 'consumed')
