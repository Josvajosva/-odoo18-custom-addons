from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero
from odoo import Command

class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _inherit = 'mrp.production'

    partner_id = fields.Many2one('res.partner', string="Customer/Vendor")
    # workorder_ids = fields.One2many('mrp.workorder', 'production_id', string="Work Orders")
    # purchase_order_id = fields.Many2one(
    #     'purchase.order',
    #     string="Purchase Order",
    #     compute="_compute_purchase_order_id",
    #     store=True
    # )
    vendor_mo_bill_count = fields.Integer(compute="_compute_vendor_mo_bill_count", string="Vendor Bills")

    def _compute_vendor_mo_bill_count(self):
        """Compute the number of vendor bills linked to this MO"""
        for record in self:
            vendor_bills = self.env['account.move'].search_count([
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),('ref', '=', record.name)  # Link by MO reference
            ])
            record.vendor_mo_bill_count = vendor_bills

    def action_view_vendor_bills(self):
        """Show related Vendor Bills"""
        self.ensure_one()
        vendor_bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),('ref', '=', self.name),
            ('state', '=', 'posted'),
        ])
        return {
            'name': "Vendor Bills",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', vendor_bills.ids)],
            'context': {'default_move_type': 'in_invoice'},
        }


    def action_create_vendor_bill(self):
        """Manually create a Vendor Bill for this MO when clicking the button"""
        self.ensure_one()
        return self._create_vendor_bill()


   ## new
    def _create_vendor_bill(self):
        """Create a bill (account.move) from the Manufacturing Order lines."""
        self.ensure_one()

        # Ensure the Manufacturing Order is in a valid state
        if self.state != 'done':
            raise UserError(_("You can only create a bill for a Manufacturing Order in 'Done' state."))

        # Create a new account.move (bill)
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',  # Supplier Bill
             'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'ref': self.name,
        })

        # Add lines to the bill based on the Manufacturing Order lines
        for line in self.move_raw_ids:
            self.env['account.move.line'].create({
                'move_id': bill.id,
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.product_id.standard_price,  # Use the product's cost price
                'account_id': line.product_id.categ_id.property_account_expense_categ_id.id,  # Expense account
            })

        # Open the created bill
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }















