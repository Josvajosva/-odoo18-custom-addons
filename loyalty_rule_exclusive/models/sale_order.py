# -*- coding: utf-8 -*-
# Part of Hyperland. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import _, models
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _program_check_compute_points(self, programs):
        """
        Override to implement exclusive rule evaluation when enabled on the program.
        
        When `exclusive_rule_evaluation` is True on a program:
        - Rules are sorted by minimum_amount (descending) - higher threshold first
        - Only the FIRST matching rule is applied
        - Other rules are skipped even if they would match
        
        This ensures mutually exclusive rule application:
        - Order < 50 → Only lower threshold rule applies
        - Order >= 50 → Only higher threshold rule applies (not both)
        """
        self.ensure_one()

        # Prepare quantities (same as original)
        order_lines = self._get_not_rewarded_order_lines().filtered(
            lambda line: not line.combo_item_id
        )
        products = order_lines.product_id
        products_qties = dict.fromkeys(products, 0)
        for line in order_lines:
            products_qties[line.product_id] += line.product_uom_qty
        
        # Contains the products that can be applied per rule
        products_per_rule = programs._get_valid_products(products)

        # Prepare amounts (same as original)
        so_products_per_rule = programs._get_valid_products(self.order_line.product_id)
        lines_per_rule = defaultdict(lambda: self.env['sale.order.line'])
        
        for line in self.order_line - self._get_no_effect_on_threshold_lines():
            is_discount = line.reward_id.reward_type == 'discount'
            reward_program = line.reward_id.program_id
            if (is_discount and reward_program.trigger == 'auto') or line.combo_item_id:
                continue
            for program in programs:
                if is_discount and reward_program == program:
                    continue
                for rule in program.rule_ids:
                    if line.product_id in so_products_per_rule.get(rule, []):
                        lines_per_rule[rule] |= line._get_lines_with_price()

        result = {}
        for program in programs:
            # Check if this program has exclusive rule evaluation enabled
            use_exclusive = getattr(program, 'exclusive_rule_evaluation', False)
            
            if use_exclusive:
                # Use exclusive rule evaluation logic
                program_result = self._compute_points_exclusive_rules(
                    program, products_qties, products_per_rule, 
                    so_products_per_rule, lines_per_rule
                )
            else:
                # Use standard Odoo logic
                program_result = self._compute_points_standard_rules(
                    program, products_qties, products_per_rule,
                    so_products_per_rule, lines_per_rule
                )
            
            result[program] = program_result
        
        return result

    def _compute_points_exclusive_rules(self, program, products_qties, products_per_rule,
                                         so_products_per_rule, lines_per_rule):
        """
        Compute points with exclusive rule evaluation.
        Only the first matching rule (sorted by priority) is applied.
        
        :param program: loyalty.program record
        :param products_qties: dict of product -> quantity
        :param products_per_rule: dict of rule -> products that match
        :param so_products_per_rule: dict of rule -> order products that match
        :param lines_per_rule: dict of rule -> order lines that match
        :return: dict with 'error' or 'points' key
        """
        program_result = {}
        
        # Sort rules by minimum_amount descending (higher threshold first)
        sorted_rules = self.env['loyalty.rule']._get_sorted_rules_for_exclusive_evaluation(
            program.rule_ids
        )
        
        code_matched = not bool(program.rule_ids) and program.applies_on == 'current'
        minimum_amount_matched = code_matched
        product_qty_matched = code_matched
        
        applied_rule = None
        points = 0
        rule_points = []
        
        _logger.info(
            "=== Exclusive Rule Evaluation for Program '%s' (ID: %s) ===",
            program.name, program.id
        )
        _logger.info("Order Total: %s %s", self.amount_total, self.currency_id.name)
        _logger.info("Evaluating %d rules in priority order...", len(sorted_rules))
        
        for rule in sorted_rules:
            # Prevent bottomless ewallet spending
            if program.program_type == 'ewallet' and not program.trigger_product_ids:
                _logger.debug("Rule %s skipped: eWallet without trigger products", rule.id)
                break
            
            if rule.mode == 'with_code' and rule not in self.code_enabled_rule_ids:
                _logger.debug(
                    "Rule %s (min_amount=%s) skipped: requires code",
                    rule.id, rule.minimum_amount
                )
                continue
            
            code_matched = True
            rule_amount = rule._compute_amount(self.currency_id)
            untaxed_amount = sum(lines_per_rule[rule].mapped('price_subtotal'))
            tax_amount = sum(lines_per_rule[rule].mapped('price_tax'))
            
            # Calculate the amount to compare based on tax mode
            compare_amount = (
                untaxed_amount + tax_amount 
                if rule.minimum_amount_tax_mode == 'incl' 
                else untaxed_amount
            )
            
            _logger.info(
                "Checking Rule %s: min_amount=%s, order_amount=%s (tax_%s)",
                rule.id, rule_amount, compare_amount, 
                rule.minimum_amount_tax_mode
            )
            
            # Check minimum amount threshold
            if rule_amount > compare_amount:
                _logger.info(
                    "  → Rule %s: SKIPPED (amount %s < minimum %s)",
                    rule.id, compare_amount, rule_amount
                )
                continue
            
            minimum_amount_matched = True
            
            # Check product requirements
            if not products_per_rule.get(rule):
                _logger.debug("  → Rule %s: No matching products", rule.id)
                continue
            
            rule_products = products_per_rule[rule]
            ordered_rule_products_qty = sum(
                products_qties[product] for product in rule_products
            )
            
            if ordered_rule_products_qty < rule.minimum_qty or not rule_products:
                _logger.info(
                    "  → Rule %s: SKIPPED (qty %s < minimum %s)",
                    rule.id, ordered_rule_products_qty, rule.minimum_qty
                )
                continue
            
            product_qty_matched = True
            
            # This rule matches! Since we're in exclusive mode, apply only this rule
            applied_rule = rule
            
            _logger.info(
                "  ★ Rule %s: MATCHED AND APPLIED (exclusive mode)",
                rule.id
            )
            
            if not rule.reward_point_amount:
                _logger.info("  → Rule %s: No points to award (reward_point_amount=0)", rule.id)
                break
            
            # Calculate points for this rule
            points, rule_points = self._calculate_rule_points(
                program, rule, ordered_rule_products_qty,
                so_products_per_rule, lines_per_rule
            )
            
            _logger.info(
                "  → Rule %s: Awarded %s points (mode: %s)",
                rule.id, points, rule.reward_point_mode
            )
            
            # IMPORTANT: Break after first matching rule in exclusive mode
            break
        
        # Final logging summary
        if applied_rule:
            _logger.info(
                "=== RESULT: Rule %s applied exclusively (min_amount=%s) ===",
                applied_rule.id, applied_rule.minimum_amount
            )
        else:
            _logger.info("=== RESULT: No rules matched for program '%s' ===", program.name)
        
        # Set error messages if applicable
        if not program.is_nominative:
            if not code_matched:
                program_result['error'] = _("This program requires a code to be applied.")
            elif not minimum_amount_matched:
                program_result['error'] = _(
                    'A minimum of %(amount)s %(currency)s should be purchased to get the reward',
                    amount=min(program.rule_ids.mapped('minimum_amount')),
                    currency=program.currency_id.name,
                )
            elif not product_qty_matched:
                program_result['error'] = _(
                    "You don't have the required product quantities on your sales order."
                )
        elif self.partner_id.is_public and not self._allow_nominative_programs():
            program_result['error'] = _("This program is not available for public users.")
        
        if 'error' not in program_result:
            points_result = [points] + rule_points
            program_result['points'] = points_result
        
        return program_result

    def _compute_points_standard_rules(self, program, products_qties, products_per_rule,
                                        so_products_per_rule, lines_per_rule):
        """
        Standard Odoo rule evaluation logic (non-exclusive).
        All matching rules contribute their points.
        
        This is essentially the original _program_check_compute_points logic
        extracted for a single program.
        """
        program_result = {}
        
        code_matched = not bool(program.rule_ids) and program.applies_on == 'current'
        minimum_amount_matched = code_matched
        product_qty_matched = code_matched
        points = 0
        rule_points = []
        
        for rule in program.rule_ids:
            # Prevent bottomless ewallet spending
            if program.program_type == 'ewallet' and not program.trigger_product_ids:
                break
            
            if rule.mode == 'with_code' and rule not in self.code_enabled_rule_ids:
                continue
            
            code_matched = True
            rule_amount = rule._compute_amount(self.currency_id)
            untaxed_amount = sum(lines_per_rule[rule].mapped('price_subtotal'))
            tax_amount = sum(lines_per_rule[rule].mapped('price_tax'))
            
            if rule_amount > (
                rule.minimum_amount_tax_mode == 'incl' and (untaxed_amount + tax_amount) 
                or untaxed_amount
            ):
                continue
            
            minimum_amount_matched = True
            
            if not products_per_rule.get(rule):
                continue
            
            rule_products = products_per_rule[rule]
            ordered_rule_products_qty = sum(
                products_qties[product] for product in rule_products
            )
            
            if ordered_rule_products_qty < rule.minimum_qty or not rule_products:
                continue
            
            product_qty_matched = True
            
            if not rule.reward_point_amount:
                continue
            
            # Calculate and add points for this rule
            rule_pts, extra_rule_points = self._calculate_rule_points(
                program, rule, ordered_rule_products_qty,
                so_products_per_rule, lines_per_rule
            )
            points += rule_pts
            rule_points.extend(extra_rule_points)
        
        # Set error messages
        if not program.is_nominative:
            if not code_matched:
                program_result['error'] = _("This program requires a code to be applied.")
            elif not minimum_amount_matched:
                program_result['error'] = _(
                    'A minimum of %(amount)s %(currency)s should be purchased to get the reward',
                    amount=min(program.rule_ids.mapped('minimum_amount')),
                    currency=program.currency_id.name,
                )
            elif not product_qty_matched:
                program_result['error'] = _(
                    "You don't have the required product quantities on your sales order."
                )
        elif self.partner_id.is_public and not self._allow_nominative_programs():
            program_result['error'] = _("This program is not available for public users.")
        
        if 'error' not in program_result:
            points_result = [points] + rule_points
            program_result['points'] = points_result
        
        return program_result

    def _calculate_rule_points(self, program, rule, ordered_rule_products_qty,
                               so_products_per_rule, lines_per_rule):
        """
        Calculate points for a specific rule.
        
        :param program: loyalty.program record
        :param rule: loyalty.rule record
        :param ordered_rule_products_qty: total quantity of matching products
        :param so_products_per_rule: dict of rule -> order products
        :param lines_per_rule: dict of rule -> order lines
        :return: tuple (points, rule_points_list)
        """
        points = 0
        rule_points = []
        
        # Split points handling for 'future' programs
        if program.applies_on == 'future' and rule.reward_point_split and rule.reward_point_mode != 'order':
            if rule.reward_point_mode == 'unit':
                rule_points.extend(
                    rule.reward_point_amount 
                    for _ in range(int(ordered_rule_products_qty))
                )
            elif rule.reward_point_mode == 'money':
                rule_products = so_products_per_rule.get(rule, [])
                for line in self.order_line:
                    if (
                        line.is_reward_line
                        or line.combo_item_id
                        or line.product_id not in rule_products
                        or line.product_uom_qty <= 0
                    ):
                        continue
                    line_price_total = self._get_order_line_price(line, 'price_total')
                    points_per_unit = float_round(
                        (rule.reward_point_amount * line_price_total / line.product_uom_qty),
                        precision_digits=2, rounding_method='DOWN'
                    )
                    if not points_per_unit:
                        continue
                    rule_points.extend([points_per_unit] * int(line.product_uom_qty))
        else:
            # Standard points calculation
            if rule.reward_point_mode == 'order':
                points = rule.reward_point_amount
            elif rule.reward_point_mode == 'money':
                amount_paid = 0.0
                rule_products = so_products_per_rule.get(rule, [])
                for line in self.order_line - self._get_no_effect_on_threshold_lines():
                    if line.combo_item_id or line.reward_id.program_id.program_type in [
                        'ewallet', 'gift_card', program.program_type
                    ]:
                        continue
                    line_price_total = self._get_order_line_price(line, 'price_total')
                    amount_paid += (
                        line_price_total if line.product_id in rule_products
                        else 0.0
                    )
                points = float_round(
                    rule.reward_point_amount * amount_paid, 
                    precision_digits=2, 
                    rounding_method='DOWN'
                )
            elif rule.reward_point_mode == 'unit':
                points = rule.reward_point_amount * ordered_rule_products_qty
        
        return points, rule_points
