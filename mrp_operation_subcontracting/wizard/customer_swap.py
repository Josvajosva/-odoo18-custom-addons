from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero

class CustomerSwap(models.TransientModel):
    _name = "customer.swaporder"

    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
        required=True,

    )
    allowed_sale_order_ids = fields.Many2many(
        'sale.order',
        string='Allowed Sale Orders',
        compute='_compute_allowed_sale_orders',
        store=False
    )

    @api.depends('sale_order_id')
    def _compute_allowed_sale_orders(self):
        for wizard in self:
            active_id = self.env.context.get('active_id')
            if not active_id:
                wizard.allowed_sale_order_ids = []
                continue

            mrp_order = self.env['mrp.production'].browse(active_id)
            product = mrp_order.product_id
            exclude_so_name = mrp_order.origin or ''

            matching_so_lines = self.env['sale.order.line'].search([
                ('product_id', '=', product.id),
                ('order_id.state', 'in', ['sale', 'done']),
                ('order_id.name', '!=', exclude_so_name),
            ])
            matching_so_ids = list(set(matching_so_lines.mapped('order_id.id')))
            wizard.allowed_sale_order_ids = self.env['sale.order'].browse(matching_so_ids)

    # def action_swap(self):
    #     active_id = self.env.context.get('active_id')
    #     if active_id:
    #         mrp_order = self.env['mrp.production'].browse(active_id)
    #         if mrp_order:
    #             if mrp_order.sale_order_id.id == self.sale_order_id.id:
    #                 raise ValidationError("The selected Sale Order is already assigned to this Manufacturing Order.")
    #             previous_sale_order = mrp_order.sale_order_id.name if mrp_order.sale_order_id else "None"
    #             mrp_order.write({
    #                 'sale_order_id': self.sale_order_id.id,
    #                 "is_swap": True
    #             })
    #
    #             message = _(
    #                 "Sale Order changed from %s to %s via Swap."
    #             ) % (previous_sale_order, self.sale_order_id.name)
    #
    #             mrp_order.message_post(body=message)

    def action_swap(self):
        active_id = self.env.context.get('active_id')
        if not active_id:
            return

        mrp_order = self.env['mrp.production'].browse(active_id)
        if not mrp_order:
            return

        if mrp_order.sale_order_id.id == self.sale_order_id.id:
            raise ValidationError("The selected Sale Order is already assigned to this Manufacturing Order.")

        original_sale_order = mrp_order.sale_order_id


        original_values = {
            'product_id': mrp_order.product_id.id,
            'product_qty': mrp_order.product_qty,
            'product_uom_id': mrp_order.product_uom_id.id,
            'bom_id': mrp_order.bom_id.id if mrp_order.bom_id else False,
            'sale_order_id': original_sale_order.id,
            'origin': mrp_order.sale_order_id.name,
            'source_location_start_id': mrp_order.source_location_start_id.id,
        }


        mrp_order.write({
            'sale_order_id': self.sale_order_id.id,
            'is_swap': True
        })

        message = _(
            "Sale Order changed from %s to %s via Swap."
        ) % (original_sale_order.name if original_sale_order else "None", self.sale_order_id.name)
        mrp_order.message_post(body=message)
        new_mo = self.env['mrp.production'].create(original_values)
        new_mo.write({'state': 'progress'})

        new_mo.message_post(body=_("This MO was recreated during a Sale Order swap from MO %s." % mrp_order.name))










