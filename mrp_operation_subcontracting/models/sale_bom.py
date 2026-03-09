from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import re


class SaleOrder(models.Model):
    _inherit = "sale.order"


    product_done_count = fields.Integer(
        string="Product Done",
        compute="_compute_product_done_count",
    )
    customer_preferred_date = fields.Date(string="Customer Preferred Date")
    customer_deadline_date = fields.Date(string="Deadline Date")
    status_so = fields.Selection([
        ('yet_to_start', 'Yet to Start'),
        ('processing', 'Processing'),
        ('partially_ready', 'Partially Ready'),
        ('ready', 'Ready'),
        ('invoiced', 'Invoiced')
    ], string='SO Status', compute="_compute_status_so", store=True)
    mrp_production_ids = fields.One2many(
        'mrp.production', 'sale_order_id', string='Manufacturing Orders')

    # status_so_stored = fields.Selection([
    #     ('yet_to_start', 'Yet to Start'),
    #     ('processing', 'Processing'),
    #     ('partially_ready', 'Partially Ready'),
    #     ('ready', 'Ready')
    # ], string='SO Status (Searchable)', compute="_compute_status_so_stored", store=True)

    name = fields.Char()
    color = fields.Integer('Color')

    processing_count = fields.Integer(compute='_compute_status_so_counts')
    yet_to_start_count = fields.Integer(compute='_compute_status_so_counts')
    partially_ready_count = fields.Integer(compute='_compute_status_so_counts')
    ready_count = fields.Integer(compute='_compute_status_so_counts')
    invoiced_count = fields.Integer(compute='_compute_status_so_counts')
    is_invoiced_custom = fields.Boolean(string='Custom Invoiced', default=False)
    

    def action_yet_to_start_orders(self):
        tree_view_id = self.env.ref('mrp_operation_subcontracting.view_sale_order_status_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Yet to Start Orders',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(tree_view_id, 'list'), (False, 'form')],
            'domain': [('status_so', '=', 'yet_to_start')],
        }

    def action_processing_orders(self):
        tree_view_id = self.env.ref('mrp_operation_subcontracting.view_sale_order_status_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Processing',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(tree_view_id, 'list'), (False, 'form')],
            'domain': [('status_so', '=', 'processing')],
        }

    def action_partially_ready_orders(self):
        tree_view_id = self.env.ref('mrp_operation_subcontracting.view_sale_order_status_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Partially Ready',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(tree_view_id, 'list'), (False, 'form')],
            'domain': [('status_so', '=', 'partially_ready')],
        }

    def action_ready_orders(self):
        tree_view_id = self.env.ref('mrp_operation_subcontracting.view_sale_order_status_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ready',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(tree_view_id, 'list'), (False, 'form')],
            'domain': [('status_so', '=', 'ready')],
        }
    
    def action_invoiced_orders(self):
        tree_view_id = self.env.ref('mrp_operation_subcontracting.view_sale_order_status_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoiced Orders',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(tree_view_id, 'list'), (False, 'form')],
            'domain': [('is_invoiced_custom', '=', True)],
        }
    
    def action_created_invoice(self):
        for order in self:
            order.is_invoiced_custom = True
            order._compute_status_so()
        return True
    
    @api.depends()
    def _compute_status_so_counts(self):
        SaleOrder = self.env['sale.order']
        processing = SaleOrder.search_count([('status_so', '=', 'processing')])
        yet_to_start = SaleOrder.search_count([('status_so', '=', 'yet_to_start')])
        partially_ready = SaleOrder.search_count([('status_so', '=', 'partially_ready')])
        ready = SaleOrder.search_count([('status_so', '=', 'ready')])
        invoiced = SaleOrder.search_count([('status_so', '=', 'invoiced')])

        for rec in self:
            rec.processing_count = processing
            rec.yet_to_start_count = yet_to_start
            rec.partially_ready_count = partially_ready
            rec.ready_count = ready
            rec.invoiced_count = invoiced


    def _compute_product_done_count(self):
        for order in self:

            count = self.env['mrp.production'].search_count([
                ('sale_order_id', '=', order.id),


            ])
            order.product_done_count = count



    # @api.depends('order_line', 'order_line.product_id')
    # def _compute_status_so(self):
    #     for order in self:
    #         # Get all MOs linked to this sale order
    #         mo_list = self.env['mrp.production'].search([
    #             ('sale_order_id', '=', order.id)
    #         ])
    #         total_mos = len(mo_list)
    #         done_mos = len(mo_list.filtered(lambda mo: mo.state == 'done'))
    #         in_progress_mos = len(mo_list.filtered(lambda mo: mo.state in ['confirmed', 'progress', 'to_close']))
    #
    #         # Set status based on counts
    #         if total_mos == 0:
    #             order.status_so = 'yet_to_start'
    #         elif done_mos == total_mos:
    #             order.status_so = 'ready'
    #         elif done_mos > 0 and done_mos < total_mos:
    #             order.status_so = 'partially_ready'
    #         elif in_progress_mos > 0:
    #             order.status_so = 'processing'
    #         else:
    #             order.status_so = 'yet_to_start'

    @api.depends('mrp_production_ids.state', 'is_invoiced_custom')
    def _compute_status_so(self):
        for order in self:
            if order.is_invoiced_custom:
                order.status_so = 'invoiced'
                continue
            mo_list = self.env['mrp.production'].search([
                ('sale_order_id', '=', order.id)
            ])
            total_mos = len(mo_list)
            done_mos = len(mo_list.filtered(lambda mo: mo.state == 'done'))
            in_progress_mos = len(mo_list.filtered(lambda mo: mo.state in ['confirmed', 'progress', 'to_close']))

            if total_mos == 0:
                order.status_so = 'yet_to_start'
            elif done_mos == total_mos:
                order.status_so = 'ready'
            elif done_mos > 0:
                order.status_so = 'partially_ready'
            elif in_progress_mos > 0:
                order.status_so = 'processing'
            else:
                order.status_so = 'yet_to_start'

    def action_recompute_status(self):
        for order in self:
            order._compute_status_so()




    def action_view_done_mrp_orders(self):

        return {
            'name': 'Related MOs',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'create': False},
        }





    def check_and_send_done_email(self):
        config = self.env['ir.config_parameter'].sudo()
        email_trigger = config.get_param('mrp.email_trigger') == 'True'
        email_list_raw = config.get_param('mrp.send_selected_users', '')
        if not email_trigger:
            return

        email_list = [email.strip() for email in email_list_raw.split(';') if email.strip()]
        for order in self:
            all_lines_done = True
            for line in order.order_line:
                mo_done = self.env['mrp.production'].search_count([
                    ('sale_order_id', '=', order.id),
                    ('product_id', '=', line.product_id.id),
                    ('state', '=', 'done'),
                ])
                if mo_done == 0:
                    all_lines_done = False
                    break
            if all_lines_done:
                template = self.env.ref('mrp_operation_subcontracting.mail_template_all_so_complete',
                                        raise_if_not_found=False)
                if template:
                    for email in email_list:
                        print('Sending email to:', email)
                        template.send_mail(order.id, email_values={'email_to': email}, force_send=True)




    # def action_confirm(self):
    #     for order in self:
    #         for line in order.order_line:
    #             product = line.product_id
    #             is_component = self.env["mrp.bom.line"].search_count([("product_id", "=", product.id)]) > 0
    #             has_bom = self.env["mrp.bom"].search_count([("product_tmpl_id", "=", product.product_tmpl_id.id)]) > 0
    #             if not has_bom and not is_component:
    #                 raise UserError(
    #                     f"The product '{product.name}' has no Bill of Materials. Please create a BoM before confirming the order."
    #                 )

    #     return super(SaleOrder, self).action_confirm()

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        domain=[('state', 'in', ['sale', 'done'])]
    )
    status_so = fields.Selection([
        ('yet_to_start', 'Yet to Start'),
        ('processing', 'Processing'),
        ('partially_ready', 'Partially Ready'),
        ('ready', 'Ready'),
        ('invoiced', 'Invoiced')
    ], string='SO Status', compute='_compute_status_so_mo')

    sale_order_date = fields.Datetime(
        string="Sale Order Date", compute="_compute_sale_order_date", store=True, readonly=True
    )
    is_swap = fields.Boolean(string='Swap SO',store=True,readonly=True)
    product_domain = fields.Many2many(
        'product.product', compute="_compute_product_domain", store=False
    )

    @api.depends('origin')
    def _compute_status_so_mo(self):
        for record in self:
            if record.origin:
                sale_order = self.env['sale.order'].search(
                    [('name', '=', record.origin)], limit=1
                )
                record.status_so = sale_order.status_so if sale_order else False
            else:
                record.status_so = False

    @api.depends('sale_order_id')
    def _compute_sale_order_date(self):
        for record in self:
            record.sale_order_date = record.sale_order_id.create_date if record.sale_order_id else False

    @api.depends('sale_order_id')
    def _compute_product_domain(self):
        for record in self:
            if not record.sale_order_id:
                record.product_domain = self.env['product.product'].search([])
                continue

            # Get products from the selected Sale Order
            sale_order_products = record.sale_order_id.order_line.mapped('product_id')

            # Get existing MOs only for THIS Sale Order
            existing_mos = self.env['mrp.production'].search([
                ('sale_order_id', '=', record.sale_order_id.id),
                ('state', 'not in', ['cancel'])
            ])

            # Get products already used in MOs of this Sale Order
            used_product_ids = existing_mos.mapped('product_id')

            # Filter available products: Only Sale Order products that are not in other MOs
            available_products = sale_order_products - used_product_ids
            print(f"Sale Order Products: {sale_order_products.ids}")
            print(f"Used Products in MOs: {used_product_ids.ids}")
            print(f"Filtered Available Products: {available_products.ids}")

            record.product_domain = available_products

    def action_open_swap_wizard(self):
        pass
        # self.ensure_one()
        # matching_so_ids = self.env['sale.order.line'].search([
        #     ('product_id', '=', self.product_id.id),
        #     ('order_id.state', 'in', ['sale', 'done']),
        # ]).mapped('order_id.id')
        #
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Related Swap Sale Order',
        #     'res_model': 'related.swapso',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'view_id': self.env.ref('mrp_operation_subcontracting.view_related_so_swap').id,
        #     'context': {
        #         'default_mrp_id': self.id,
        #         'sale_order_domain': [('id', 'in', matching_so_ids)],
        #     }
        # }

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        if self.sale_order_id:
            self.origin = self.sale_order_id.name
        else:
            self.origin = False
        self.product_id = False
        self.product_qty = 0
        self._compute_sale_order_date()
        self._compute_product_domain()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.sale_order_id and self.product_id:
            order_line = self.sale_order_id.order_line.filtered(
                lambda l: l.product_id == self.product_id
            )
            if order_line:
                self.product_qty = order_line[0].product_uom_qty


    def write(self, vals):
        if 'sale_order_id' in vals:
            sale_order = self.env['sale.order'].browse(vals['sale_order_id'])
            vals['origin'] = sale_order.name if sale_order else False
        result = super().write(vals)
        if 'state' in vals and vals['state'] == 'done':
            sale_orders = self.mapped('sale_order_id')
            sale_orders.check_and_send_done_email()
        return result






class SaleStatus(models.Model):
    _name = 'sale.status'
    _description = 'Sale Orders Status'

    origin = fields.Char(string='Sale Order')
    state = fields.Selection([
        ('progress', 'In Progress'),
        ('done', 'Done'),
    ],string='Status', readonly=True)
#
#
#
#     @api.model
#     def update_sale_status_records(self):
#         sale_orders = self.env['sale.order'].search([])
#
#         for order in sale_orders:
#             order_lines = order.order_line.filtered(lambda l: l.product_id.type == 'product')
#
#             all_products_done = True
#
#             for line in order_lines:
#
#                 mos = self.env['mrp.production'].search([
#                     ('sale_order_id', '=', order.id),
#                     ('product_id', '=', line.product_id.id)
#                 ])
#                 if not mos or any(mo.state != 'done' for mo in mos):
#                     all_products_done = False
#                     break
#             state = 'done' if all_products_done else 'progress'
#             status = self.search([('origin', '=', order.name)], limit=1)
#             if status:
#                 status.write({'state': state})
#             else:
#                 self.create({
#                     'origin': order.name,
#                     'state': state
#                 })
# #
#
#     def action_view_related_mos(self):
#         self.ensure_one()
#         sale_order = self.env['sale.order'].search([('name', '=', self.origin)])
#
#         if not sale_order:
#             return {'type': 'ir.actions.act_window_close'}
#
#         # Search all MOs related to this sale order
#         mos = self.env['mrp.production'].search([('sale_order_id', '=', sale_order.id)])
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Manufacturing Orders',
#             'res_model': 'mrp.production',
#             'view_mode': 'list,form',
#             'domain': [('id', 'in', mos.ids)],
#             'context': dict(self.env.context),
#             'target': 'current',
#         }
#
#













