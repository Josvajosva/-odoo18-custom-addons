from odoo import fields, models

class InvoiceCommissionHistory(models.Model):
    _name = 'invoice.commission.history'
    _description = 'Invoice Commission and Deduction History'

    invoice_id = fields.Many2one('account.move', string='Invoice')
    rule_percentage = fields.Float(string='Rule Percentage')
    rule_max_days = fields.Integer(string='Rule Max Days')
    rule_type = fields.Selection([
        ('commission', 'Commission'),
        ('deduction', 'Deduction')
    ], string='Rule Type')
    condition_field = fields.Selection([
        ('first_fund', 'First Fund'),
        ('fund_credit', 'Final Fund'),
        ('work_completion_days', 'Project Completion Days'),
        ('jvr_days', 'JVR Submission Days'),
        ('material_to_jvr_months', 'Delay in Months Beyond 120 Days')
    ], string='Condition Field')
    commission = fields.Float(string='Commission')
    deduction = fields.Float(string='Deduction')
    log_date = fields.Datetime(string='Log Date', default=fields.Datetime.now)
    system_type = fields.Selection([
        ('inline', 'Inline System'),
        ('online', 'Online System'),
    ], string='System Type')
    commission_per_catg = fields.Float(string="Commission % Category", default=20)
    notes = fields.Text(string='Notes')

