from odoo import models, api
from odoo.exceptions import UserError
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        for order in self:
            for line in order.order_line:
                product = line.product_id
                is_component = self.env["mrp.bom.line"].search_count([("product_id", "=", product.id)]) > 0
                has_bom = self.env["mrp.bom"].search_count([("product_tmpl_id", "=", product.product_tmpl_id.id)]) > 0
                if not has_bom and not is_component:
                    raise UserError(
                        f"The product '{product.name}' has no Bill of Materials. Please create a BoM before confirming the order."
                    )

        return super(SaleOrder, self).action_confirm()

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        domain=[('state', 'in', ['sale', 'done'])]
    )

    sale_order_date = fields.Datetime(
        string="Sale Order Date", compute="_compute_sale_order_date", store=True, readonly=True
    )
    product_domain = fields.Many2many(
        'product.product', compute="_compute_product_domain", store=False
    )

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
                ('state', 'not in', ['cancel', 'done'])
            ])

            # Get products already used in MOs of this Sale Order
            used_product_ids = existing_mos.mapped('product_id')

            # Filter available products: Only Sale Order products that are not in other MOs
            available_products = sale_order_products - used_product_ids
            print(f"Sale Order Products: {sale_order_products.ids}")
            print(f"Used Products in MOs: {used_product_ids.ids}")
            print(f"Filtered Available Products: {available_products.ids}")

            #Apply the computed domain
            record.product_domain = available_products

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        self.product_id = False
        self._compute_sale_order_date()
        self._compute_product_domain()














