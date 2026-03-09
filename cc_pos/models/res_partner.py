from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class ResPartner(models.Model):
    _inherit = 'res.partner'

    whatsapp_number = fields.Char(string="WhatsApp Number")
    dob = fields.Date(string="Date of Birth")
    anniversary = fields.Date(string="Anniversary")

    loyalty_card_ids = fields.One2many('loyalty.card', 'partner_id', string="Loyalty Cards")

    points_earned = fields.Integer(
        compute='_compute_loyalty_points',
        store=True,
        string="Points Earned",
    )
    points_redeemed = fields.Integer(
        compute='_compute_loyalty_points',
        store=True,
        string="Points Redeemed",
    )
    available_points = fields.Integer(
        compute='_compute_loyalty_points',
        store=True,
        string="Available Points",
    )
    has_membership = fields.Boolean(string="Membership Activated", default=False)

    last_pos_order_date = fields.Date(
        string="Last POS Order Date",
        store=True,
    )

    @api.depends('loyalty_card_ids.history_ids.issued', 'loyalty_card_ids.history_ids.used')
    def _compute_loyalty_points(self):
        for partner in self:
            loyalty_cards = partner.sudo().loyalty_card_ids.filtered(
                lambda c: c.program_id.program_type == 'loyalty'
            )
            total_earned = sum(loyalty_cards.mapped('history_ids.issued') or [])
            total_redeemed = sum(loyalty_cards.mapped('history_ids.used') or [])

            partner.points_earned = int(total_earned)
            partner.points_redeemed = int(total_redeemed)
            partner.available_points = int(total_earned - total_redeemed)

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list += ['last_pos_order_date']
        return fields_list


    def action_add_joining_bonus(self):
        for partner in self:
            if partner.has_membership:
                raise UserError(_("Membership is already activated for %s.") % partner.name)

            partner.sudo().write({'has_membership': True})

            # If loyalty card exists, add bonus now (once per partner)
            # If no card yet, LoyaltyHistory.create will add it on first order
            loyalty_cards = self.env['loyalty.card'].sudo().search([
                ('partner_id', '=', partner.id),
                ('program_id.program_type', '=', 'loyalty'),
            ])
            if loyalty_cards:
                bonus_exists = self.env['loyalty.history'].sudo().search_count([
                    ('card_id', 'in', loyalty_cards.ids),
                    ('description', '=', 'Membership Bonus'),
                ])
                if not bonus_exists:
                    lc = loyalty_cards[0]
                    self.env['loyalty.history'].sudo().create({
                        'description': 'Membership Bonus',
                        'issued': 25,
                        'card_id': lc.id,
                    })
                    lc.sudo().points += 25


class LoyaltyPointLine(models.Model):
    _name = 'loyalty.point.line'
    _description = 'Loyalty Point History'

    partner_id = fields.Many2one('res.partner', required=True)
    points = fields.Integer()
    source = fields.Selection([
        ('joining', 'Joining Bonus'),
        ('bill', 'Bill'),
        ('weekly', 'Weekly Bonus'),
        ('milestone', 'Milestone Bonus'),
        ('streak', 'Streak Bonus'),
        ('redeem', 'Redeemed'),
    ])
    earned_date = fields.Date(default=fields.Date.today)
    expiry_date = fields.Date(compute='_compute_expiry', store=True)
    pos_order_id = fields.Many2one('pos.order')

    @api.depends('earned_date')
    def _compute_expiry(self):
        for rec in self:
            if rec.earned_date:
                rec.expiry_date = rec.earned_date + timedelta(days=180)


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    points_used = fields.Float(
        string="Points Used",
        # compute='_compute_points_used', josva
        store=False,
        help="Points redeemed in this order"
    )

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        for order in self:
            if order.partner_id:
                order.partner_id.sudo().write({
                    'last_pos_order_date': fields.Date.context_today(order),
                })
        return res

    @api.constrains('amount_total', 'config_id')
    def _check_stock_constraint(self):
        """
        This works EXACTLY like your _check_negative_billing_constraint method
        Will trigger when order is saved/updated
        """
        for order in self:
            config = order.config_id
            if not config.hide_out_of_stock_products:
                for line in order.lines:
                    product = line.product_id
                    if product.type != 'product':
                        continue
                    
                    # Get available quantity
                    available_qty = product.qty_available
                    
                    # Check if requested quantity exceeds available
                    if line.qty > available_qty:
                        raise ValidationError(_(
                            "STOCK ERROR.\n\n"
                            "Product: %(product)s\n"
                            "Requested: %(requested)s units\n"
                            "Available: %(available)s units\n\n"
                            "Please enable 'Hide Out-of-Stock Products' in POS settings\n"
                            "or adjust the quantity before proceeding."
                        ) % {
                            'product': product.display_name,
                            'requested': line.qty,
                            'available': max(available_qty, 0)
                        })
    
    @api.constrains('lines', 'state')
    def _check_stock_state(self):
        """Additional check when order state changes to paid - EXACTLY like your _check_negative_state"""
        for order in self:
            config = order.config_id
            if (not config.hide_out_of_stock_products and
                order.state == 'paid'):
                
                for line in order.lines:
                    product = line.product_id
                    if product.type != 'product':
                        continue
                    
                    # Get available quantity
                    available_qty = product.qty_available
                    
                    # Check if requested quantity exceeds available
                    if line.qty > available_qty:
                        order.write({'state': 'draft'})
                        raise ValidationError(_(
                            "Cannot mark order as paid.\n"
                            "Insufficient stock available."
                        ))

    # josva
    # def action_pos_order_paid(self):
    #     """Keep your existing logic but add stock constraint check - EXACTLY like your pattern"""
    #     self._check_stock_constraint()
    #
    #     res = super(PosOrder, self).action_pos_order_paid()
    #
    #     for order in self:
    #         partner = order.partner_id
    #         if not partner or not partner.has_membership:
    #             continue
    #
    #         self._track_points_earned(order, partner)
    #         self._track_points_redeemed_correct(order, partner)
    #
    #     return res
    #
    # def _track_points_earned(self, order, partner):
    #     """Track points earned from purchase"""
    #     total = order.amount_total
    #     if total < 100:
    #         return
    #
    #     today = order.date_order.date()
    #
    #     existing = self.env['loyalty.point.line'].sudo().search([
    #         ('pos_order_id', '=', order.id),
    #         ('points', '>', 0),
    #     ], limit=1)
    #     if existing:
    #         return
    #
    #     streak = False
    #     orders = self.env['pos.order'].sudo().search([
    #         ('partner_id', '=', partner.id),
    #         ('state', 'in', ['paid']),
    #     ], order='date_order desc')
    #
    #     unique_dates = []
    #     for o in orders:
    #         d = o.date_order.date()
    #         if d not in unique_dates:
    #             unique_dates.append(d)
    #         if len(unique_dates) == 27:
    #             break
    #
    #     if len(unique_dates) == 27:
    #         expected = today
    #         valid = True
    #
    #         for d in unique_dates:
    #             if d != expected:
    #                 valid = False
    #                 break
    #             expected -= timedelta(days=1)
    #
    #         if valid:
    #             streak = True
    #
    #     base_points = int(total // 100)
    #     points = base_points * 2 if streak else base_points
    #
    #     if points > 0:
    #         self.env['loyalty.point.line'].sudo().create({
    #             'partner_id': partner.id,
    #             'points': points,
    #             'source': 'streak' if streak else 'bill',
    #             'earned_date': today,
    #             'pos_order_id': order.id,
    #         })
    #
    #         partner.sudo().write({
    #             'points_earned': partner.points_earned + points
    #         })
    #
    #         previous_points = partner.points_earned - points
    #         new_total = previous_points + points
    #
    #         if previous_points < 250 and new_total >= 250:
    #             milestone_exists = self.env['loyalty.point.line'].sudo().search([
    #                 ('partner_id', '=', partner.id),
    #                 ('source', '=', 'milestone'),
    #             ], limit=1)
    #
    #             if not milestone_exists:
    #                 self.env['loyalty.point.line'].sudo().create({
    #                     'partner_id': partner.id,
    #                     'points': 25,
    #                     'source': 'milestone',
    #                 })
    #
    #                 partner.sudo().write({
    #                     'points_earned': partner.points_earned + 25
    #                 })
    #
    # def _track_points_redeemed_correct(self, order, partner):
    #     """CORRECT VERSION: Get actual points spent from loyalty system"""
    #
    #     loyalty_cards = self.env['loyalty.card'].search([
    #         ('partner_id', '=', partner.id),
    #         ('program_id.program_type', '=', 'loyalty'),
    #     ])
    #
    #     for card in loyalty_cards:
    #
    #         points_used = self._calculate_points_from_discount_logic(order)
    #
    #         if points_used > 0:
    #             partner._add_points_redeemed(
    #                 points=int(points_used),
    #                 order_id=order.id,
    #             )
    #             return
    #
    # def _calculate_points_from_discount_logic(self, order):
    #     """Calculate points based on discount and conversion rate"""
    #     discount_lines = order.lines.filtered(lambda line: line.price_unit < 0)
    #
    #     if not discount_lines:
    #         return 0
    #
    #     total_discount = abs(sum(line.price_subtotal_incl for line in discount_lines))
    #
    #     POINT_VALUE = 3.0
    #
    #     points_used = total_discount / POINT_VALUE
    #
    #     return int(points_used)
    #
    # def _compute_points_used(self):
    #     """Compute points used for display"""
    #     for order in self:
    #         order.points_used = self._calculate_points_from_discount_logic(order)


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'


class LoyaltyHistory(models.Model):
    _inherit = 'loyalty.history'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.description == 'Membership Bonus':
                continue
            partner = record.card_id.partner_id
            card = record.card_id
            if (partner and partner.has_membership
                    and card.program_id.program_type == 'loyalty'):
                # Check across ALL loyalty cards of this partner
                partner_cards = self.env['loyalty.card'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('program_id.program_type', '=', 'loyalty'),
                ])
                bonus_exists = self.sudo().search_count([
                    ('card_id', 'in', partner_cards.ids),
                    ('description', '=', 'Membership Bonus'),
                ])
                if not bonus_exists:
                    self.sudo().create({
                        'description': 'Membership Bonus',
                        'issued': 25,
                        'card_id': card.id,
                    })
                    card.sudo().points += 25
        return records
