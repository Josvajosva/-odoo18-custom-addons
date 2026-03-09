from odoo import models, fields, api

class PurchaseRequestConfirmWizard(models.TransientModel):
    _name = 'purchase.request.confirm.wizard'
    _description = 'Purchase Request Confirmation Wizard'

    sale_order_ids = fields.Many2many('sale.order', string='Selected Sale Orders', default=lambda self: self.env.context.get('default_sale_order_ids'))
    dummy_field = fields.Char()

    def action_confirm_pr(self):
        """Trigger PR creation from selected Sale Orders and close the wizard."""
        if self.sale_order_ids:
            self.sale_order_ids.with_context(from_confirm_wizard=True).create_pr_for_selected_so()

        return {'type': 'ir.actions.act_window_close'}  

    def action_cancel(self):
        """Cancel the operation and close the wizard."""
        return {'type': 'ir.actions.act_window_close'}  
