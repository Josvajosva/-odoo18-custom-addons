import math
from datetime import timedelta

from odoo import fields, models
from odoo.tools import float_round


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _program_check_compute_points(self, programs):
        """Override to apply floor-based points and repeat-purchase doubling."""
        result = super()._program_check_compute_points(programs)

        for program in programs:
            if program not in result or 'points' not in result[program]:
                continue
            if not program.use_floor_points and not program.double_points_days:
                continue

            # Recalculate points for floor-based programs
            if program.use_floor_points:
                recalculated_points = self._calculate_floor_points_sale(program)
                if recalculated_points is not None:
                    points_list = result[program]['points']
                    # points_list[0] is the main points, rest are split points
                    points_list[0] = recalculated_points

            # Apply repeat-purchase doubling
            if program.double_points_days and program.double_points_days > 0:
                partner = self.partner_id
                if partner and not partner.is_public:
                    if self._has_recent_purchase(partner, program.double_points_days):
                        points_list = result[program]['points']
                        points_list[0] = points_list[0] * 2

        return result

    def _calculate_floor_points_sale(self, program):
        """Calculate floor-based points for a sale order.

        For 'money' mode: floor(amount / minimum_amount) * reward_point_amount
        Other modes are left unchanged.
        """
        self.ensure_one()
        order_lines = self._get_not_rewarded_order_lines().filtered(
            lambda line: not line.combo_item_id
        )
        products = order_lines.product_id
        products_qties = dict.fromkeys(products, 0)
        for line in order_lines:
            products_qties[line.product_id] += line.product_uom_qty

        products_per_rule = program._get_valid_products(products)
        so_products_per_rule = program._get_valid_products(self.order_line.product_id)

        total_points = 0
        has_money_rule = False

        for rule in program.rule_ids:
            if rule.reward_point_mode != 'money':
                continue
            has_money_rule = True

            rule_amount = rule._compute_amount(self.currency_id)
            if rule_amount <= 0:
                continue

            # Calculate amount paid for matching products
            rule_products = so_products_per_rule.get(rule, [])
            amount_paid = 0.0
            for line in self.order_line - self._get_no_effect_on_threshold_lines():
                if line.combo_item_id or line.reward_id.program_id.program_type in [
                    'ewallet', 'gift_card', program.program_type
                ]:
                    continue
                if line.product_id in rule_products:
                    amount_paid += self._get_order_line_price(line, 'price_total')

            # Check minimum amount condition
            untaxed = sum(
                self._get_order_line_price(l, 'price_subtotal')
                for l in self.order_line - self._get_no_effect_on_threshold_lines()
                if not l.combo_item_id and l.product_id in rule_products
            )
            tax = sum(
                self._get_order_line_price(l, 'price_tax')
                for l in self.order_line - self._get_no_effect_on_threshold_lines()
                if not l.combo_item_id and l.product_id in rule_products
            )
            check_amount = (untaxed + tax) if rule.minimum_amount_tax_mode == 'incl' else untaxed
            if rule_amount > check_amount:
                continue

            # Floor-based calculation: floor(amount_paid / minimum_amount) * reward_point_amount
            multiples = math.floor(amount_paid / rule_amount)
            total_points += multiples * rule.reward_point_amount

        if has_money_rule:
            return float_round(total_points, precision_digits=2)
        return None

    def _has_recent_purchase(self, partner, days):
        """Check if the partner has a confirmed sale order or POS order within the given days."""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)

        # Check sale orders
        recent_sale = self.env['sale.order'].sudo().search_count([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', cutoff_date),
            ('id', '!=', self.id),
        ], limit=1)
        if recent_sale:
            return True

        # Check POS orders
        recent_pos = self.env['pos.order'].sudo().search_count([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('date_order', '>=', cutoff_date),
        ], limit=1)
        return bool(recent_pos)