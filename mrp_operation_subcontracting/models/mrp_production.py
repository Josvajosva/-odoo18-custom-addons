from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero
from odoo import Command
from datetime import datetime, timedelta
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby

class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _inherit = 'mrp.production'

    is_subcontract = fields.Boolean("Is Subcontract?", compute="_compute_subcontract_data", store=True)
    partner_id = fields.Many2one('res.partner', string="Vendor",
    tracking = True)
    workorder_ids = fields.One2many('mrp.workorder', 'production_id', string="Work Orders")

    source_location_start_id = fields.Many2one(
        'stock.location',
        string="Source Location",
        tracking=True, readonly=True, store=True
    )



    @api.onchange('partner_id')
    def _onchange_partner_id_set_location(self):
        for record in self:
            if record.is_subcontract and record.partner_id:
                if record.partner_id.property_stock_subcontractor:
                    record.source_location_start_id = record.partner_id.property_stock_subcontractor

    @api.onchange('product_id')
    def _onchange_product_id_set_location(self):
        for record in self:
            if not record.is_subcontract and record.product_id:
                if record.product_id.property_stock_production:
                    record.source_location_start_id = record.product_id.property_stock_production




    # def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
    #     """ Warning, any changes done to this method will need to be repeated for consistency in:
    #         - Manually added components, i.e. "default_" values in view
    #         - Moves from a copied MO, i.e. move.create
    #         - Existing moves during backorder creation """
    #     source_location = self.location_src_id
    #     # current_datetime = fields.Datetime.now()
    #     # confirm_date = self.confirm_date or fields.Datetime.now()
    #     data = {
    #         'sequence': bom_line.sequence if bom_line else 10,
    #         'name': _('New'),
    #         'date': self.date_start,
    #         # 'date': confirm_date,
    #         'date_deadline': self.date_start,
    #         'bom_line_id': bom_line.id if bom_line else False,
    #         'picking_type_id': self.picking_type_id.id,
    #         'product_id': product_id.id,
    #         'product_uom_qty': product_uom_qty,
    #         'product_uom': product_uom.id,
    #         'location_id': source_location.id,
    #         # 'location_dest_id': self.product_id.with_company(self.company_id).property_stock_production.id,
    #         'location_dest_id': self.source_location_start_id.id,
    #         'raw_material_production_id': self.id,
    #         'company_id': self.company_id.id,
    #         'operation_id': operation_id,
    #         'procure_method': 'make_to_stock',
    #         'origin': self._get_origin(),
    #         'state': 'draft',
    #         'warehouse_id': source_location.warehouse_id.id,
    #         'group_id': self.procurement_group_id.id,
    #         'propagate_cancel': self.propagate_cancel,
    #         'manual_consumption': self.env['stock.move']._determine_is_manual_consumption(product_id, self, bom_line),
    #     }
    #     return data




    # def _get_move_finished_values(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False, cost_share=0):
    #     group_orders = self.procurement_group_id.mrp_production_ids
    #     move_dest_ids = self.move_dest_ids
    #     if len(group_orders) > 1:
    #         move_dest_ids |= group_orders[0].move_finished_ids.filtered(lambda m: m.product_id == self.product_id).move_dest_ids
    #     return {
    #         'product_id': product_id,
    #         'product_uom_qty': product_uom_qty,
    #         'product_uom': product_uom,
    #         'operation_id': operation_id,
    #         'byproduct_id': byproduct_id,
    #         'name': _('New'),
    #         'date': self.date_finished,
    #         # 'date': self.date_start,
    #         'date_deadline': self.date_deadline,
    #         'picking_type_id': self.picking_type_id.id,
    #         # 'location_id': self.product_id.with_company(self.company_id).property_stock_production.id,
    #         'location_id': self.source_location_start_id.id,
    #         'location_dest_id': self.location_dest_id.id,
    #         'company_id': self.company_id.id,
    #         'production_id': self.id,
    #         'warehouse_id': self.location_dest_id.warehouse_id.id,
    #         'origin': self.product_id.partner_ref,
    #         'group_id': self.procurement_group_id.id,
    #         'propagate_cancel': self.propagate_cancel,
    #         'move_dest_ids': [(4, x.id) for x in self.move_dest_ids if not byproduct_id],
    #         'cost_share': cost_share,
    #     }

    def button_mark_done(self):
        """Override to skip raw material checks and directly mark production as done"""
        res = self.pre_button_mark_done()
        if res is not True:
            return res

        # Bypass raw material checks
        productions_not_to_backorder = self
        productions_to_backorder = self.env['mrp.production']

        self.workorder_ids.button_finish()

        # Skip backorder handling and directly set production as done
        productions_not_to_backorder._post_inventory(cancel_backorder=True)
        productions_to_backorder._post_inventory(cancel_backorder=True)

        # Mark all production moves as done
        (productions_not_to_backorder.move_raw_ids | productions_not_to_backorder.move_finished_ids).write({
            'state': 'done',
            'product_uom_qty': 0.0,
        })

        # Set production order to 'done' without checking components
        for production in self:
            production.write({
                'date_finished': fields.Datetime.now(),
                'priority': '0',
                'is_locked': True,
                'state': 'done',
            })

        return True


  # new
    @api.depends('product_id', 'company_id')
    def _compute_production_location(self):
        if not self.company_id:
            return
        location_by_company = self.env['stock.location']._read_group(
            domain=[
                ('company_id', 'in', self.company_id.ids),
                ('usage', '=', 'production')
            ],
            groupby=['company_id'],
            aggregates=['id:array_agg']
        )
        location_by_company = {company.id: ids for company, ids in location_by_company}
        for production in self:
            # if production.is_subcontract == True:
            prod_loc = production.source_location_start_id.id or production.product_id.with_company(production.company_id).property_stock_production
            comp_locs = location_by_company.get(production.company_id.id)
            production.production_location_id = prod_loc or (comp_locs and comp_locs[0])


    @api.depends('workorder_ids.workcenter_id', 'workorder_ids.workcenter_id.name')
    def _compute_subcontract_data(self):
        for production in self:
            subcontract_workcenters = production.workorder_ids.mapped('workcenter_id').filtered(
                lambda wc: any(wo.workcenter_id.name == wc.name for wo in production.workorder_ids)
            )
            if subcontract_workcenters:
                production.is_subcontract = any(subcontract_workcenters.mapped('is_subcontract'))
            else:
                production.is_subcontract = False


class MrpConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    scrap_approval_required = fields.Boolean(
        string="Scrap Approval Operation",
        config_parameter='mrp.scrap_approval_required'
    )
    scrap_approvers = fields.Many2many(
        'res.users',
        string="Scrap Approvers",
    )
    email_trigger = fields.Boolean(
        string="Send An Email Required",
        config_parameter='mrp.email_trigger'
    )
    send_selected_users = fields.Text(
        string="Send An Email Only SelectedUsers",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo()
        approver_str = param.get_param('mrp.scrap_approvers', '')
        if approver_str:
            ids = list(map(int, approver_str.split(',')))
            res.update({'scrap_approvers': [(6, 0, ids)]})
        res.update({
            'send_selected_users': param.get_param('mrp.send_selected_users', default=''),
        })
        return res

    def set_values(self):
        super().set_values()
        param = self.env['ir.config_parameter'].sudo()
        if self.scrap_approvers:
            approver_ids_str = ','.join(map(str, self.scrap_approvers.ids))
            param.set_param('mrp.scrap_approvers', approver_ids_str)
        else:
            param.set_param('mrp.scrap_approvers', '')
        param.set_param('mrp.send_selected_users', self.send_selected_users or '')



    # def action_swap(self):
    #     self.ensure_one()
    #
    #     # Find all matching SOs based on product
    #     matching_so_ids = self.env['sale.order.line'].search([
    #         ('product_id', '=', self.product_id.id),
    #         ('order_id.state', 'in', ['sale', 'done']),
    #     ]).mapped('order_id.id')
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Swapping',
    #         'res_model': 'customer.swaporder',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'view_id': self.env.ref('mrp_operation_subcontracting.view_swapping_order_form').id,
    #         'context': {
    #             'default_mrp_id': self.id,
    #             'sale_order_domain': [('id', 'in', matching_so_ids)],
    #         }
    #     }



