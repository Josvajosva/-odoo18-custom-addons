# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, Command


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'



    def _calc_operation_cost(self, opt):
        """ Calculate operation cost based on expected duration and workcenter cost. """
        duration_expected = opt.duration_expected or 0
        return (duration_expected / 60) * opt.workcenter_id.costs_hour




