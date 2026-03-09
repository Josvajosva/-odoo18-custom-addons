# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _

class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    is_subcontract = fields.Boolean("Is Subcontract?")
    partner_id = fields.Many2one('res.partner', 
        string='Vendor', #states=READONLY_STATES, 
        change_default=True, tracking=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", 
        help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
