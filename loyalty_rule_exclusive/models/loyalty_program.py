# -*- coding: utf-8 -*-
# Part of Hyperland. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    exclusive_rule_evaluation = fields.Boolean(
        string='Exclusive Rule Evaluation',
        default=False,
        help="When enabled, only ONE rule will be applied per order based on priority. "
             "Rules are evaluated in sequence order, and only the first matching rule "
             "(highest priority with lowest sequence number) will grant points. "
             "This ensures mutually exclusive rule application based on amount thresholds.\n\n"
             "Example: If you have two rules:\n"
             "- Rule 1: minimum_amount = 10, sequence = 20\n"
             "- Rule 2: minimum_amount = 50, sequence = 10\n\n"
             "An order of 60 will ONLY apply Rule 2 (not both rules)."
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Add exclusive_rule_evaluation to POS loaded fields."""
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list.append('exclusive_rule_evaluation')
        return fields_list
