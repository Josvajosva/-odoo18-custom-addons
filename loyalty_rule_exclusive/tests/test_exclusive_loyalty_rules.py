# -*- coding: utf-8 -*-
# Part of Hyperland. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('post_install', '-at_install', 'loyalty_exclusive')
class TestExclusiveLoyaltyRules(TestSaleCouponCommon):
    """
    Test cases for mutually exclusive loyalty rule evaluation.
    
    Test Scenarios:
    - Order = 49 → Rule with min=10 applies (Rule with min=50 doesn't match)
    - Order = 50 → Rule with min=50 applies (not Rule with min=10)
    - Order = 100 → Rule with min=50 applies (not Rule with min=10)
    
    The key insight: rules are sorted by minimum_amount DESCENDING,
    so the highest threshold rule is checked first. This prevents
    lower threshold rules from matching when a higher one should apply.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create a product for testing
        cls.test_product = cls.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 1,  # 1 currency unit per item for easy calculation
            'sale_ok': True,
            'taxes_id': False,  # No taxes for simpler testing
        })
        
        # Create a loyalty program with two rules and exclusive evaluation
        cls.exclusive_loyalty_program = cls.env['loyalty.program'].create({
            'name': 'Exclusive Loyalty Program',
            'program_type': 'loyalty',
            'applies_on': 'both',
            'trigger': 'auto',
            'exclusive_rule_evaluation': True,  # Enable exclusive mode
            'rule_ids': [
                # Rule 1: Lower threshold (applies when amount >= 10 but < 50)
                Command.create({
                    'reward_point_amount': 1,
                    'reward_point_mode': 'money',  # 1 point per currency unit
                    'minimum_amount': 10,
                    'minimum_amount_tax_mode': 'incl',
                    'minimum_qty': 0,
                }),
                # Rule 2: Higher threshold (applies when amount >= 50)
                Command.create({
                    'reward_point_amount': 1,
                    'reward_point_mode': 'money',  # 1 point per currency unit
                    'minimum_amount': 50,
                    'minimum_amount_tax_mode': 'incl',
                    'minimum_qty': 0,
                }),
            ],
            'reward_ids': [
                Command.create({
                    'reward_type': 'discount',
                    'discount': 5,  # 5% discount
                    'discount_mode': 'percent',
                    'discount_applicability': 'order',
                    'required_points': 200,
                }),
            ],
        })
        
        # Create a similar program WITHOUT exclusive mode for comparison
        cls.standard_loyalty_program = cls.env['loyalty.program'].create({
            'name': 'Standard Loyalty Program (Non-Exclusive)',
            'program_type': 'loyalty',
            'applies_on': 'both',
            'trigger': 'auto',
            'exclusive_rule_evaluation': False,  # Standard mode
            'rule_ids': [
                # Rule 1: Lower threshold
                Command.create({
                    'reward_point_amount': 1,
                    'reward_point_mode': 'money',
                    'minimum_amount': 10,
                    'minimum_amount_tax_mode': 'incl',
                    'minimum_qty': 0,
                }),
                # Rule 2: Higher threshold
                Command.create({
                    'reward_point_amount': 1,
                    'reward_point_mode': 'money',
                    'minimum_amount': 50,
                    'minimum_amount_tax_mode': 'incl',
                    'minimum_qty': 0,
                }),
            ],
            'reward_ids': [
                Command.create({
                    'reward_type': 'discount',
                    'discount': 5,
                    'discount_mode': 'percent',
                    'discount_applicability': 'order',
                    'required_points': 200,
                }),
            ],
        })

    def _create_order_with_amount(self, amount, program=None):
        """Helper to create a sale order with a specific amount."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.test_product.id,
                    'product_uom_qty': amount,  # Since product is 1 unit = 1 currency
                }),
            ],
        })
        return order

    def test_01_order_amount_49_exclusive(self):
        """
        Test Case 1: Order amount = 49 (< 50)
        Expected: Only Rule with min=10 applies
        
        In exclusive mode:
        - Rule with min=50 is checked first (higher threshold)
        - Rule doesn't match (49 < 50), skip
        - Rule with min=10 is checked next
        - Rule matches (49 >= 10), apply and stop
        Result: Only lower threshold rule points are awarded
        """
        order = self._create_order_with_amount(49)
        
        # Check program applicability
        result = order._program_check_compute_points(self.exclusive_loyalty_program)
        
        self.assertIn(self.exclusive_loyalty_program, result)
        program_result = result[self.exclusive_loyalty_program]
        
        # Should not have an error
        self.assertNotIn('error', program_result, 
            f"Unexpected error: {program_result.get('error')}")
        
        # Should have points from Rule with min=10 only
        self.assertIn('points', program_result)
        points = program_result['points'][0]
        
        # Points should be 49 (1 point per currency unit from one rule only)
        self.assertEqual(points, 49, 
            f"Expected 49 points from one rule only, got {points}")

    def test_02_order_amount_50_exclusive(self):
        """
        Test Case 2: Order amount = 50 (>= 50)
        Expected: Only Rule with min=50 applies (NOT both rules!)
        
        In exclusive mode:
        - Rule with min=50 is checked first (higher threshold)
        - Rule matches (50 >= 50), apply and STOP
        - Rule with min=10 is never checked
        Result: Only higher threshold rule points are awarded
        """
        order = self._create_order_with_amount(50)
        
        result = order._program_check_compute_points(self.exclusive_loyalty_program)
        
        self.assertIn(self.exclusive_loyalty_program, result)
        program_result = result[self.exclusive_loyalty_program]
        
        self.assertNotIn('error', program_result,
            f"Unexpected error: {program_result.get('error')}")
        
        self.assertIn('points', program_result)
        points = program_result['points'][0]
        
        # Points should be 50 (from one rule only, NOT 100 from both rules)
        self.assertEqual(points, 50,
            f"Expected 50 points from one rule only, got {points}")

    def test_03_order_amount_100_exclusive(self):
        """
        Test Case 3: Order amount = 100 (>> 50)
        Expected: Only Rule with min=50 applies (NOT both rules!)
        
        Even though both rules would match, in exclusive mode only the
        highest threshold matching rule (min=50) applies.
        """
        order = self._create_order_with_amount(100)
        
        result = order._program_check_compute_points(self.exclusive_loyalty_program)
        
        self.assertIn(self.exclusive_loyalty_program, result)
        program_result = result[self.exclusive_loyalty_program]
        
        self.assertNotIn('error', program_result,
            f"Unexpected error: {program_result.get('error')}")
        
        self.assertIn('points', program_result)
        points = program_result['points'][0]
        
        # Points should be 100 (from one rule only, NOT 200 from both rules)
        self.assertEqual(points, 100,
            f"Expected 100 points from one rule only, got {points}")

    def test_04_compare_exclusive_vs_standard(self):
        """
        Test Case 4: Compare exclusive vs standard mode for same order
        
        For an order of 100:
        - Exclusive mode: Only Rule with min=50 applies → 100 points
        - Standard mode: Both rules apply → 200 points (100 + 100)
        """
        order = self._create_order_with_amount(100)
        
        # Test exclusive program
        exclusive_result = order._program_check_compute_points(
            self.exclusive_loyalty_program
        )
        exclusive_points = exclusive_result[self.exclusive_loyalty_program]['points'][0]
        
        # Test standard program
        standard_result = order._program_check_compute_points(
            self.standard_loyalty_program
        )
        standard_points = standard_result[self.standard_loyalty_program]['points'][0]
        
        # Exclusive should give 100 points (one rule)
        self.assertEqual(exclusive_points, 100,
            f"Exclusive mode should give 100 points, got {exclusive_points}")
        
        # Standard should give 200 points (both rules)
        self.assertEqual(standard_points, 200,
            f"Standard mode should give 200 points, got {standard_points}")
        
        # Verify the difference
        self.assertNotEqual(exclusive_points, standard_points,
            "Exclusive and standard modes should give different points")

    def test_05_order_below_minimum(self):
        """
        Test Case 5: Order amount = 5 (below both thresholds)
        Expected: No rules match, program returns error
        """
        order = self._create_order_with_amount(5)
        
        result = order._program_check_compute_points(self.exclusive_loyalty_program)
        
        self.assertIn(self.exclusive_loyalty_program, result)
        program_result = result[self.exclusive_loyalty_program]
        
        # Should have an error because no rules match
        self.assertIn('error', program_result,
            "Expected error for order below minimum threshold")

    def test_06_rule_sorting(self):
        """
        Test Case 6: Verify rule sorting for exclusive evaluation
        
        Rules should be sorted by minimum_amount descending
        (higher amount = checked first)
        """
        rules = self.exclusive_loyalty_program.rule_ids
        
        sorted_rules = self.env['loyalty.rule']._get_sorted_rules_for_exclusive_evaluation(
            rules
        )
        
        # First rule should be the one with higher minimum_amount
        self.assertEqual(sorted_rules[0].minimum_amount, 50,
            "First rule should have highest minimum_amount")
        
        # Second rule should be the one with lower minimum_amount
        self.assertEqual(sorted_rules[1].minimum_amount, 10,
            "Second rule should have lower minimum_amount")

    def test_07_toggle_exclusive_mode(self):
        """
        Test Case 7: Verify toggling exclusive mode changes behavior
        """
        order = self._create_order_with_amount(100)
        
        # First, test with exclusive mode ON
        self.exclusive_loyalty_program.exclusive_rule_evaluation = True
        result_exclusive = order._program_check_compute_points(
            self.exclusive_loyalty_program
        )
        points_exclusive = result_exclusive[self.exclusive_loyalty_program]['points'][0]
        
        # Then, test with exclusive mode OFF
        self.exclusive_loyalty_program.exclusive_rule_evaluation = False
        result_standard = order._program_check_compute_points(
            self.exclusive_loyalty_program
        )
        points_standard = result_standard[self.exclusive_loyalty_program]['points'][0]
        
        # Reset to original state
        self.exclusive_loyalty_program.exclusive_rule_evaluation = True
        
        # Exclusive should give 100, standard should give 200
        self.assertEqual(points_exclusive, 100,
            "Exclusive mode should give 100 points")
        self.assertEqual(points_standard, 200,
            "Standard mode should give 200 points")
