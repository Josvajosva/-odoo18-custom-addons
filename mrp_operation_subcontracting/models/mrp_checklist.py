from odoo import models, fields,api




class MrpBom(models.Model):
    _inherit = "mrp.bom"

    checklist_ids = fields.One2many('mrp.bom.checklist', 'bom_id', string="Checklist Items")


class MrpBomChecklist(models.Model):
    _name = "mrp.bom.checklist"
    _description = "BOM Checklist"

    name = fields.Char(string="Checklist Item", required=True)
    no_of_units = fields.Char(string="Number of Units")
    bom_id = fields.Many2one('mrp.bom', string="BOM Reference", ondelete='cascade')
    available = fields.Boolean(string="Is Available")
    remarks = fields.Text(string="Remarks")


class StockMoveChecklist(models.Model):
    _name = "stock.move.checklist"
    _description = "Stock Move Checklist"

    name = fields.Char(string="Checklist Item", required=True)
    no_of_units = fields.Char(string="Number of Units")
    available = fields.Boolean(string="Is Available")
    remarks = fields.Text(string="Remarks")
    move_id = fields.Many2one('stock.move', string="Stock Move", ondelete='cascade')



class StockMove(models.Model):
    _inherit = "stock.move"

    available = fields.Boolean(string="Is Available", store=True)
    remarks = fields.Text(string="Remarks")
    checklist_ids = fields.One2many(
        'stock.move.checklist', 'move_id', string="Checklist Items"
    )

    def action_open_checklist(self):
        self.ensure_one()
        if not self.checklist_ids:
            boms = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)
            ])

            checklist_items = []
            for bom in boms:
                for checklist in bom.checklist_ids:
                    checklist_items.append((0, 0, {
                        'name': checklist.name,
                        'no_of_units': checklist.no_of_units,
                        'available': True if checklist.name and checklist.no_of_units else False,
                        'remarks': '',
                    }))

            if checklist_items:
                self.checklist_ids = checklist_items

        return {
            'name': "Checklist",
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'form',
            'view_id': self.env.ref('mrp_operation_subcontracting.view_stock_move_checklist_form').id,
            'res_id': self.id,
            'target': 'new',
        }

    # def action_save_checklist(self):
    #     for move in self:
    #         move.write({
    #             'available': move.available,
    #             'remarks': move.remarks
    #         })
    #     return {'type': 'ir.actions.act_window_close'}

    def action_save_checklist(self):
        """Save checklist items' availability and remarks"""
        for move in self:
            for checklist in move.checklist_ids:
                checklist.write({
                    'available': checklist.available,
                    'remarks': checklist.remarks
                })
        return {'type': 'ir.actions.act_window_close'}


