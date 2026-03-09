from odoo import models, fields

class CommissionRule(models.Model):
    _name = 'invoice.commission.rule'
    _description = 'Commission Rules Configuration'

    name = fields.Char(string='Rule Name', required=True)
    base_field = fields.Selection([('amount_total', 'Invoice Total'), ('amount_untaxed', 'Invoice Untaxed Amount'), ('first_fund', 'First Fund'), ('fund_credit', 'Final Fund')],
                                  string='Apply On', default='amount_untaxed')
    percentage = fields.Float(string='Percentage', required=True)
    condition_field = fields.Selection([
        ('first_fund', 'First Fund'),
        ('fund_credit', 'Final Fund'),
        ('work_completion_days', 'Project Completion Days'),
        ('jvr_days', 'JVR Submission Days')
    ], string='Condition Field')
    max_days = fields.Integer(string='Maximum Days Allowed')
    min_days = fields.Integer(string='Minimum Days Allowed', default=0)
    release_penalty_on = fields.Boolean(string='Release Penalty Only When This Rule Applied', default=False)
    system_type = fields.Selection([
        ('inline', 'Inline System'),
        ('online', 'Online System'),
    ], string='System Type')
    commission_per_catg = fields.Float(string="Commission % Category", default=20)


class DeductionRule(models.Model):
    _name = 'invoice.deduction.rule'
    _description = 'Deduction Rules Configuration'

    name = fields.Char(string='Rule Name', required=True)
    base_field = fields.Selection([('amount_total', 'Invoice Total'), ('amount_untaxed', 'Invoice Untaxed Amount')],
                                  string='Apply On', default='amount_untaxed')
    percentage = fields.Float(string='Percentage', required=True)
    condition_field = fields.Selection([
        ('work_completion_days', 'Project Completion Days'),
        ('jvr_days', 'JVR Submission Days'),
        ('material_to_jvr_months', 'Delay in Months Beyond 120 Days')
    ], string='Condition Field')
    max_days = fields.Integer(string='Maximum Days Allowed', default=0)
    min_days = fields.Integer(string='Minimum Days Allowed', default=0)
    system_type = fields.Selection([
        ('inline', 'Inline System'),
        ('online', 'Online System'),
    ], string='System Type')
    commission_per_catg = fields.Float(string="Commission % Category", default=20)

