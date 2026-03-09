from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import clean_context, OrderedSet, groupby





class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    # state = fields.Selection(selection_add=[('ready', 'Ready')], ondelete={'ready': 'set draft'})

    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('done', 'Done'),
    ], string="Status", default='draft', tracking=True)



    def do_scrap(self):
        self._check_company()
        self = self.with_context(clean_context(self.env.context))
        for scrap in self:
            scrap.name = self.env['ir.sequence'].next_by_code('stock.scrap') or _('New')
            move = self.env['stock.move'].create(scrap._prepare_move_values())
            # master: replace context by cancel_backorder
            move.with_context(is_scrap=True)._action_done()
            scrap.write({'state': 'ready'})
            scrap.date_done = fields.Datetime.now()
            if scrap.should_replenish:
                scrap.do_replenish()
        return True



    def action_approve(self):
        """Override approve action to check if approval is required and restrict non-approvers."""
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval_required = IrConfigParam.get_param('mrp.scrap_approval_required', default=False)

        if approval_required:
            approver_ids_str = IrConfigParam.get_param('mrp.scrap_approvers', '')
            approver_ids = [int(uid) for uid in approver_ids_str.split(',') if uid.isdigit()]

            if not approver_ids or self.env.user.id not in approver_ids:
                raise exceptions.UserError(_('You are not authorized to approve scrap operations.'))

        self.write({'state': 'done'})