from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(selection_add=[
        ('pre_inspection', 'Pre Inspection '),
    ])

    farmer_type_crm = fields.Selection([
        ('70_percent', 'Micro Farmer (75% )'),
        ('100_percent', 'Small Scale Farmer (100%)'),
        ('other', 'Other')
    ], related='opportunity_id.farmer_type', store=True, string="Farmer Type ")

    government_contribution = fields.Monetary(
        string="Government Contribution",
        currency_field='currency_id',
        compute='_compute_contributions',
        store=True,
    )

    farmer_contribution = fields.Monetary(
        string="Farmer Contribution",
        currency_field='currency_id',
        compute='_compute_contributions',
        store=True,
    )

    farmer_dd_image = fields.Binary(string="Farmer DD Uploaded")
    farmer_image_filename = fields.Char(string="Layout File Name")
    payment_image = fields.Binary(string="Payment Uploaded")
    payment_image_filename = fields.Char(string="Payment File Name")
    farmer_Acceptance_image = fields.Binary(string=" Farmer Acceptance Letter Uploaded")
    farmer_Acceptance_image_filename = fields.Char(string="Farmer Acceptance File Name")
    approve_active = fields.Boolean('Approve', default=False)
    pre_approve_active = fields.Boolean('Pre Approve', default=False)
    sale_latitude = fields.Float(string='Latitude', digits=(16, 6), related='opportunity_id.latitude')
    sale_longitude = fields.Float(string='Longitude', digits=(16, 6), related='opportunity_id.longitude')
    mi_type = fields.Selection([
        ('drip_irrigation', 'Drip Irrigation'),
        ('sprinkler_irrigation', 'Sprinkler Irrigation'),
        ('rain_gun', 'Rain Gun'),
        ('micro_sprinkler', 'Micro Sprinkler'),
        ('bubbler_irrigation', 'Bubbler Irrigation'),
        ('drip_to_sprinkler', 'Drip to Sprinkler System'),
    ], string='MI Type', related='opportunity_id.mi_type', store=True, )
    mi_area = fields.Float(string='MI Area ', related='opportunity_id.mi_area', digits=(16, 3))
    total_area = fields.Float(string='Total Area', related='opportunity_id.total_area', digits=(16, 3))
    survey_number = fields.Char(string='Survey Number', related='opportunity_id.survey_number')
    sub_division_no = fields.Char(string='Sub-Division No', related='opportunity_id.sub_division_no')
    crop_name = fields.Char(string='Crop Name', related='opportunity_id.crop_name')
    spacing = fields.Float(string='Spacing', digits=(16, 2), related='opportunity_id.spacing')
    pro_rata_spacing = fields.Float(string='Pro Rata Spacing', digits=(16, 2),
                                    related='opportunity_id.pro_rata_spacing')
    sales_area = fields.Many2one(
        'sales.manager',
        string='Area',
        related='opportunity_id.sales_manager_area_id',
        store=True,
        readonly=True
    )
    sales_manager = fields.Many2one(
        'res.partner',
        string='Sales Manager',
        related='opportunity_id.sales_manager_id',
        store=True,
        readonly=True
    )
    application_id = fields.Char(string='Application ID', related='opportunity_id.application_id')
    department = fields.Char(string="Department", related='opportunity_id.department')
    scheme = fields.Char(string="Scheme", related='opportunity_id.scheme')
    applied_area = fields.Float(string="Applied Area ", digits=(16, 3), related='opportunity_id.applied_area')
    block = fields.Char(string="Block", related='opportunity_id.block')
    dealer_id = fields.Many2one('res.partner', string="Dealer")

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'invoice_farmer_type_crm': self.farmer_type_crm,
            'farmer_contribution': self.farmer_contribution,
            'government_contribution': self.government_contribution,
            'application_id': self.application_id,
            'sale_latitude': self.sale_latitude,
            'sale_longitude': self.sale_longitude,
            'survey_number': self.survey_number,
            'sub_division_no': self.sub_division_no,
            'crop_name': self.crop_name,
            'spacing': self.spacing,
            'pro_rata_spacing': self.pro_rata_spacing,
            'mi_type': self.mi_type,
            'mi_area': self.mi_area,
            'total_area': self.total_area,
            'department': self.department,
            'scheme': self.scheme,
            'applied_area': self.applied_area,
            'block': self.block,
            'sales_area': self.sales_area.id if self.sales_area else False,
            'sales_manager': self.sales_manager.id if self.sales_manager else False,
            'farmer_dd_image': self.farmer_dd_image,
            'farmer_image_filename': self.farmer_image_filename,
            'payment_image': self.payment_image,
            'payment_image_filename': self.payment_image_filename,
            'farmer_acceptance_image': self.farmer_Acceptance_image,
            'farmer_acceptance_image_filename': self.farmer_Acceptance_image_filename,
            'dealer_id': self.dealer_id.id if self.dealer_id else False,
        })
        return invoice_vals

    def action_mark_preinspection_approved(self):
        for order in self:
            order.state = 'pre_inspection'
            order.pre_approve_active = True

    def action_mark_approved(self):
        for order in self:
            order.state = 'draft'
            order.approve_active = True

    @api.depends('farmer_type_crm', 'amount_untaxed')
    def _compute_contributions(self):
        for order in self:
            if order.farmer_type_crm == '70_percent':
                order.government_contribution = order.amount_untaxed * 0.75
                order.farmer_contribution = order.amount_untaxed * 0.25
            elif order.farmer_type_crm == '100_percent':
                order.government_contribution = order.amount_untaxed
                order.farmer_contribution = 0
            else:
                order.government_contribution = 0
                order.farmer_contribution = 0

    # @api.depends('farmer_type_crm', 'amount_total')
    # def _compute_contributions(self):
    #     for order in self:
    #         if order.farmer_type_crm == '70_percent':
    #             # 75% government, 25% farmer
    #             order.government_contribution = int(order.amount_total * 0.75)
    #             order.farmer_contribution = int(order.amount_total * 0.25)
    #         elif order.farmer_type_crm == '100_percent':
    #             # 100% government, 0% farmer
    #             order.government_contribution = int(order.amount_total)
    #             order.farmer_contribution = 0
    #         else:
    #             # Default case if no farmer type is selected
    #             order.government_contribution = 0
    #             order.farmer_contribution = 0


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields):
        """Override default_get to set amount from invoice's fund_credit"""
        result = super(AccountPaymentRegister, self).default_get(fields)

        # Get the active invoice
        active_id = self._context.get('active_id')
        if active_id:
            invoice = self.env['account.move'].browse(active_id)
            if invoice.fund_credit:
                result['amount'] = invoice.fund_credit
                result['payment_date'] = invoice.fund_credit_date

        return result
