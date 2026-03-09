from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class InventoryReverseAdjustment(models.Model):
    _name = 'inventory.reverse.adjustment'
    _description = 'Inventory Reverse Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    creation_date = fields.Date(string='Creation Date', default=fields.Date.today)
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[]"
    )
    qty = fields.Float(string='Quantity', required=True, default=1.0)
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('confirm', 'Confirmed')],
        string="Status",
        default='draft',
        tracking=True
    )

    def action_view_moves(self):
        self.ensure_one()
        moves = self.env['stock.move'].search([('origin', '=', self.name)])
        
        if not moves:
            raise UserWarning(_("No stock moves found for adjustment %s. Please confirm the adjustment first.") % self.name)
        
        move_line_ids = moves.mapped('move_line_ids').ids
        
        if not move_line_ids:
            raise UserWarning(_("No move lines found for the stock moves."))
        
        return {
            'name': _('Stock Move Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_line_ids)],
            'context': {'create': False},
            'views': [
                [self.env.ref('stock.view_move_line_tree').id, 'tree'],
                [self.env.ref('stock.view_move_line_form').id, 'form']
            ],
        }

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('inventory.reverse.adjustment') or _('New')
        return super(InventoryReverseAdjustment, self).create(vals)

    def action_confirm(self):
        for rec in self:
            bom = self.env['mrp.bom'].search(
                [('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)],
                limit=1
            )
            if not bom:
                raise ValidationError(_("Still BoM is not configured for this selected product"))

            available_qty = rec.product_id.qty_available
            if rec.qty > available_qty:
                raise ValidationError(_(
                    "Not enough stock to do reverse adjustment for product %s.\n"
                    "On hand: %s, Entered: %s"
                ) % (rec.product_id.display_name, available_qty, rec.qty))

            source_location = self.env.ref('stock.stock_location_stock')
            dest_location = self.env['stock.location'].search([('name', '=', 'Reverse Adjustment')], limit=1)
            if not dest_location:
                dest_location = self.env['stock.location'].create({
                    'name': 'Reverse Adjustment',
                    'usage': 'inventory',
                })

            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('sequence_code', '=', 'RINT')
            ], limit=1)
            if not picking_type:
                raise ValidationError(_("No picking type found for internal transfers."))

            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'origin': rec.name,
            })

            move = self.env['stock.move'].create({
                'name': rec.name,
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.qty,
                'product_uom': rec.product_id.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'picking_id': picking.id,
                'origin': rec.name,
            })

            picking.action_confirm()
            
            picking.action_assign()
            
            for move_line in move.move_line_ids:
                move_line.quantity = rec.qty
            
            picking.button_validate()

            rec.state = 'confirm'