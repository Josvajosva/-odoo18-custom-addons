# -*- coding: utf-8 -*-
# Part of Hyperland. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    @api.model
    def _get_sorted_rules_for_exclusive_evaluation(self, rules):
        """
        Sort rules for exclusive evaluation.
        
        Rules are sorted by minimum_amount descending (higher threshold first).
        This ensures that more specific rules (higher thresholds) are evaluated
        first, preventing lower threshold rules from matching when a higher
        threshold rule should apply.

        Example:
        - Rule A: minimum_amount = 50 (checked first)
        - Rule B: minimum_amount = 10 (checked second)
        
        For an order of 60:
        - Rule A matches (60 >= 50) → applied, stop
        - Rule B never checked
        
        For an order of 30:
        - Rule A doesn't match (30 < 50) → skip
        - Rule B matches (30 >= 10) → applied

        :param rules: loyalty.rule recordset
        :return: sorted list of rules
        """
        return sorted(
            rules,
            key=lambda r: -r.minimum_amount,  # Descending: higher threshold first
        )
