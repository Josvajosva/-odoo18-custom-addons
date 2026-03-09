import math
from datetime import timedelta

from odoo import fields, models
from odoo.tools import float_round


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def confirm_coupon_programs(self, coupon_data):
        """Override to recalculate points using floor logic and apply doubling before storing."""
        # Modify coupon_data in-place before passing to super
        self._apply_custom_loyalty_points(coupon_data)
        return super().confirm_coupon_programs(coupon_data)

    def _apply_custom_loyalty_points(self, coupon_data):
        """Recalculate points for programs with floor-based or doubling enabled."""
        partner = self.partner_id

        for coupon_id, coupon_vals in coupon_data.items():
            program_id = coupon_vals.get('program_id')
            if not program_id:
                continue
            program = self.env['loyalty.program'].browse(int(program_id))
            if not program.exists():
                continue
            if not program.use_floor_points and not program.double_points_days:
                continue

            # Recalculate floor-based points
            if program.use_floor_points:
                new_points = self._calculate_floor_points_pos(program)
                if new_points is not None:
                    # Preserve sign: positive = earned, negative = spent
                    if coupon_vals['points'] >= 0:
                        coupon_vals['points'] = new_points
                    # If points were negative (spent), don't modify

            # Apply repeat-purchase doubling
            if program.double_points_days and program.double_points_days > 0:
                if partner and coupon_vals['points'] > 0:
                    if self._has_recent_purchase_pos(partner, program.double_points_days):
                        coupon_vals['points'] = coupon_vals['points'] * 2

    def _calculate_floor_points_pos(self, program):
        """Calculate floor-based points for a POS order.

        For each 'money' mode rule: floor(amount / minimum_amount) * reward_point_amount
        """
        total_points = 0
        has_money_rule = False

        # Calculate amount from non-reward order lines
        product_lines = self.lines.filtered(lambda l: not l.is_reward_line)
        total_amount_incl = sum(l.price_subtotal_incl for l in product_lines)

        for rule in program.rule_ids:
            if rule.reward_point_mode != 'money':
                continue
            has_money_rule = True

            rule_amount = rule._compute_amount(self.currency_id or self.company_id.currency_id)
            if rule_amount <= 0:
                continue

            # Calculate amount for matching products
            valid_products = rule._get_valid_products()
            if valid_products:
                amount_paid = sum(
                    l.price_subtotal_incl for l in product_lines
                    if l.product_id in valid_products
                )
            else:
                # No product filter = all products qualify
                amount_paid = total_amount_incl

            # Check minimum amount condition
            check_amount = amount_paid
            if rule.minimum_amount_tax_mode == 'excl':
                if valid_products:
                    check_amount = sum(
                        l.price_subtotal for l in product_lines
                        if l.product_id in valid_products
                    )
                else:
                    check_amount = sum(l.price_subtotal for l in product_lines)

            if rule_amount > check_amount:
                continue

            # Floor-based: floor(amount / minimum_amount) * reward_point_amount
            multiples = math.floor(amount_paid / rule_amount)
            total_points += multiples * rule.reward_point_amount

        if has_money_rule:
            return float_round(total_points, precision_digits=2)
        return None

    def _has_recent_purchase_pos(self, partner, days):
        """Check if partner has a recent order (POS or Sale) within given days."""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)

        # Check POS orders
        recent_pos = self.env['pos.order'].sudo().search_count([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('date_order', '>=', cutoff_date),
            ('id', '!=', self.id),
        ], limit=1)
        if recent_pos:
            return True

        # Check sale orders
        recent_sale = self.env['sale.order'].sudo().search_count([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', cutoff_date),
        ], limit=1)
        return bool(recent_sale)