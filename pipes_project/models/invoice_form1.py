from odoo import models, fields, api
from odoo.osv import expression
import requests
from odoo.exceptions import UserError
import json
import re
from datetime import date 
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_farmer_type_crm = fields.Selection([
        ('70_percent', 'Micro Farmer (75% )'),
        ('100_percent', 'Small Scale Farmer (100%)'),
        ('other', 'Other')
    ], string="Farmer Type ")

    # work_status = fields.Selection([
    #     ('issued_work_order', 'Issued Work Order'),
    #     ('work_completed', 'Work Completed'),
    #     ('work_completion_approved', 'Work Completion Approved'),
    #     ('fund_release_recommended_block', 'Fund Release Recommended by Block Office'),
    #     ('fund_release_recommended_district', 'Fund Release Recommended by District Office'),
    #     ('rectification_approved_block', 'Mi Company Rectification Approved By Block'),
    #     ('rectification_reverted_block', 'Mi Company Rectification Reverted By Block'),
    #     ('fund_release_approved_agri', 'First Fund Release Approved by State Agri'),
    #     ('fund_release_approved_horti', 'First Fund Release Approved by State Horticulture'),
    #     ('utr_skipped', 'District First Fund UTR Updated'),
    #     ('joint_verification_completed', 'Joint Verification Completed'),
    #     ('fund_release_proceeding_completed', 'Fund Release Proceeding Completed'),
    #     ('fund_credited', 'Final Fund UTR Updated'),
    # ], string='Work Status')
    work_status = fields.Selection([
        ('application_received', 'Application Received'),
        ('approved_by_block', 'Approved by Block Officer'),
        ('dd_upload_skipped', 'DD Upload Skipped'),
        ('district_first_fund_credited', 'District First Fund Credited (UTR Updated)'),
        ('district_first_fund_proceeding_completed', 'District First Fund Proceeding Completed'),
        ('farmer_acceptance_uploaded', 'Farmer Acceptance Letter Uploaded'),
        ('fund_credited', 'Final Fund Credited (UTR Updated)'),
        ('final_fund_release_recommended_district', 'Final Fund Release Recommended by District Office'),
        ('first_fund_credited', 'First Fund Credited (UTR Updated)'),
        ('first_fund_proceeding_completed', 'First Fund Proceeding Completed'),
        ('fund_release_proceeding_completed', 'Fund Release Proceeding Completed'),
        ('fund_release_recommended_block', 'Fund Release Recommended by Block Office'),
        ('fund_release_recommended_district', 'Fund Release Recommended by District Office'),
        ('fund_release_approved_agri', 'Fund Release Verification by State Agriculture'),
        ('fund_release_approved_horti', 'Fund Release Verification by State Horticulture'),
        ('issued_work_order', 'Issued Work Order'),
        ('joint_verification_completed', 'Joint Verification Completed'),
        ('layout_image_uploaded', 'Layout Image and GPS Image Uploaded'),
        ('rectification_approved_block', 'Mi Company Rectification Approved By Block'),
        ('rectification_reverted_block', 'Mi Company Rectification Reverted By Block'),
        ('preinspection_revised_quotation', 'Pre Inspection - Request for Revised Quotation'),
        ('preinspection_approved', 'Pre Inspection Approved'),
        ('quotation_copy_uploaded', 'Quotation Copy Uploaded by MI Company'),
        ('quotation_prepared_mi', 'Quotation Prepared by MI Company'),
        ('reverted_rectified_by_block', 'Reverted Application Rectified By Block'),
        ('reverted_rectified_by_mi', 'Reverted Application Rectified By MI Company'),
        ('reverted_state_agri_horti', 'Reverted By State Agri / Horti'),
        ('reverted_state_agri_horti_block', 'Reverted by State Agri / Horti to Block'),
        ('work_completed', 'Work Completed'),
        ('work_completion_approved', 'Work Completion Approved'),
    ], string='Work Status')
    system_type = fields.Selection([
        ('inline', 'Inline System'),
        ('online', 'Online System'),
    ], string='System Type')
    
    work_date = fields.Date(string="Work Status Date")
    utr_number = fields.Char(string="UTR Number")


    fund_credit = fields.Monetary(
        string="Fund Credited  ",
        currency_field='currency_id',
        tracking=True
    )
    fund_credit_date = fields.Date(string="Final Fund Credit Date")

    eway_date = fields.Date(string="E Way Bill Date ")
    eway_number = fields.Char(string="E Way Bill Number")

    sale_latitude = fields.Float(string='Latitude', digits=(16, 6))
    sale_longitude = fields.Float(string='Longitude', digits=(16, 6))
    survey_number = fields.Char(string='Survey Number')
    sub_division_no = fields.Char(string='Sub-Division No')
    crop_name = fields.Char(string='Crop Name')
    spacing = fields.Float(string='Spacing', digits=(16, 2))
    pro_rata_spacing = fields.Float(string='Pro Rata Spacing', digits=(16, 2))
    mi_type = fields.Selection([
        ('drip_irrigation', 'Drip Irrigation'),
        ('sprinkler_irrigation', 'Sprinkler Irrigation'),
        ('rain_gun', 'Rain Gun'),
        ('micro_sprinkler', 'Micro Sprinkler'),
        ('bubbler_irrigation', 'Bubbler Irrigation'),
        ('drip_to_sprinkler', 'Drip to Sprinkler System'),
    ], string='MI Type')
    mi_area = fields.Float(string='MI Area ', digits=(16, 3))
    total_area = fields.Float(string='Total Area ', digits=(16, 3))
    application_id = fields.Char(string='Application ID', required=True, default='')
    department = fields.Char(string="Department")
    scheme = fields.Char(string="Scheme")
    applied_area = fields.Float(string="Applied Area ", digits=(16, 3))
    block = fields.Char(string="Block")
    sales_area = fields.Many2one('sales.manager', string='Area')
    sales_manager = fields.Many2one('res.partner', string='Sales Manager')
    government_contribution = fields.Monetary(
        string="Government Contribution",
        currency_field='currency_id'
    )

    farmer_contribution = fields.Monetary(
        string="Farmer Contribution",
        currency_field='currency_id'
    )

    farmer_dd_image = fields.Binary(string="Farmer DD Uploaded")
    farmer_image_filename = fields.Char(string="Layout File Name")

    payment_image = fields.Binary(string="Payment Uploaded")
    payment_image_filename = fields.Char(string="Payment File Name")

    farmer_acceptance_image = fields.Binary(string="Farmer Acceptance Letter Uploaded")
    farmer_acceptance_image_filename = fields.Char(string="Farmer Acceptance File Name")
    zoho_invoice_no = fields.Char(string="Tally Invoice No")

    @api.onchange('work_status')
    def _onchange_work_status(self):
        if self.work_status:
            self.work_date = date.today()


    # @api.onchange('work_status','fund_credit')
    # def _onchange_work_status(self):
    #     if self.work_status:
    #         self.work_date = date.today()
    #     if self.fund_credit:
    #         self.fund_credit_date = date.today()
    

    commission = fields.Float(string='Commission', compute='_compute_commission_deduction', store=True)
    deduction = fields.Float(string='Deduction', compute='_compute_commission_deduction', store=True)
    commission_payable = fields.Float(string='Payable', compute='_compute_commission_payable', store=True)
    commission_notes = fields.Text(string='Commission/Deduction Notes', compute='_compute_commission_deduction', store=True)

    # Add Work Status Dates fields if not already present
    issued_work_order_date = fields.Date(string='Issued Work Order Date')
    work_completion_approved_date = fields.Date(string='Work Completion Approved Date')
    first_fund_utr_skipped_date = fields.Date(string='First Fund UTR Update Date')
    joint_verification_completed_date = fields.Date(string='Joint Verification Completed Date')
    commission_history_ids = fields.One2many(
        'invoice.commission.history', 
        'invoice_id', 
        string="Commission History"
    )
    dealer_id = fields.Many2one('res.partner', string="Dealer")
    area_manager_id = fields.Many2one('hr.employee', string="Area Manager", related='dealer_id.staff_name')
    creation_date = fields.Date(
        string="Creation Date",
        default=fields.Date.context_today,
        readonly=True,
        copy=False
    )
    #first_fund = fields.Float(
    #    string='First Fund', 
    #    compute='_compute_fund_commissions', 
    #    store=True,
    #    readonly=True
    #)
    first_fund = fields.Monetary(
        string="First Fund",
        currency_field='currency_id',
        tracking=True
    )
    second_fund = fields.Float(
        string='Second Fund', 
        compute='_compute_fund_commissions', 
        store=True,
        readonly=True
    )

    def action_sync_invoice_date(self):
        """
        Sync invoice_date and date with eway_date using direct SQL.
        Works even for posted invoices (bypasses Odoo validations).
        """
        query = """
            UPDATE account_move
            SET 
                invoice_date = eway_date,
                date = eway_date
            WHERE 
                move_type = 'out_invoice'
                AND eway_date IS NOT NULL
                AND invoice_date <> eway_date;
        """
        self.env.cr.execute(query)
        self.env.cr.commit()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Invoice Dates Synced',
                'message': 'Invoice dates successfully updated using SQL!',
                'type': 'success',
                'sticky': False,
            }
        }

    # @api.onchange('dealer_id')
    # def _onchange_dealer_id(self):
    #     """Auto-fill area manager when a dealer is selected."""
    #     for record in self:
    #         record.area_manager_id = record.dealer_id.staff_name if record.dealer_id else False

    #@api.depends('commission_history_ids', 'commission_history_ids.rule_percentage', 
    #             'commission_history_ids.commission', 'commission_history_ids.rule_type')
    #def _compute_fund_commissions(self):
    #    for invoice in self:
    #        first_fund_records = invoice.commission_history_ids.filtered(
    #            lambda h: h.rule_type == 'commission' and h.rule_percentage == 8
    #        )
    #        invoice.first_fund = sum(first_fund_records.mapped('commission'))
    #        
    #        second_fund_records = invoice.commission_history_ids.filtered(
    #            lambda h: h.rule_type == 'commission' and h.rule_percentage == 12
    #        )
    #        invoice.second_fund = sum(second_fund_records.mapped('commission'))

    first_fund_payment_status = fields.Selection([
        ('paid', 'Paid'),
        ('not_paid', 'Not Paid')
    ], string="First Fund Payment Status", default='not_paid')

    second_fund_payment_status = fields.Selection([
        ('paid', 'Paid'),
        ('not_paid', 'Not Paid')
    ], string="Second Fund Payment Status", default='not_paid')

    @api.onchange('application_id')
    def _onchange_application_id(self):
        """Auto-fetch Area Manager from CRM when Application ID matches."""
        for record in self:
            if record.application_id:
                crm_record = self.env['crm.lead'].search([
                    ('application_id', '=', record.application_id)
                ], limit=1)
                record.area_manager_id = crm_record.area_manager_id.id if crm_record else False
            else:
                record.area_manager_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('creation_date'):
                vals['creation_date'] = fields.Date.context_today(self)
        return super().create(vals_list)

    @api.depends('issued_work_order_date', 'work_completion_approved_date',
                 'first_fund_utr_skipped_date', 'joint_verification_completed_date',
                 'eway_date','fund_credit_date', 'first_fund', 'fund_credit')
    def _compute_commission_deduction(self):
        CommissionRule = self.env['invoice.commission.rule']
        DeductionRule = self.env['invoice.deduction.rule']
        History = self.env['invoice.commission.history']
        
        for invoice in self:
            status_dates = {
                'issued_work_order': invoice.issued_work_order_date,
                'work_completed': invoice.work_completion_approved_date,
                'first_fund_utr_skipped': invoice.first_fund_utr_skipped_date,
                'joint_verification_completed': invoice.joint_verification_completed_date,
                'eway_bill': invoice.eway_date,
            }

            commission = 0.0
            deduction = 0.0
            release_penalty = False
            commission_per_catg = invoice.partner_id.commission_per_catg

            # --------------------
            # Commission Calculation
            # --------------------
            for rule in CommissionRule.search([('commission_per_catg','=',commission_per_catg)]):
                apply_value = getattr(invoice, rule.base_field, 0.0)
                condition_met = False
                notes = f"Commission Rule: {rule.name}"
                history_ids = []#History.search([('invoice_id','=',invoice.id),('rule_type','=','commission'),('condition_field','=',rule.condition_field)])

                if rule.base_field == 'first_fund' and invoice.first_fund_utr_skipped_date:
                    tax_1 = apply_value - (apply_value*0.12)
                    fitting = tax_1 - (tax_1*0.05)
                    commission = fitting*0.18

                elif rule.base_field == 'fund_credit' and invoice.fund_credit_date:
                    tax_1 = apply_value - (apply_value*0.12)
                    fitting = tax_1 - (tax_1*0.05)
                    commission += fitting*0.18

                if rule.condition_field == 'work_completion_days' and (invoice.system_type==rule.system_type): # and status_dates['eway_bill'] and status_dates['work_completed']
                    #days_diff = (status_dates['work_completed'] - status_dates['eway_bill']).days
                    #if rule.min_days <= days_diff <= rule.max_days:
                    condition_met = True
                    if not history_ids:
                        History.create({
                            'invoice_id': invoice.id,
                            'rule_type': 'commission',
                            'condition_field': rule.condition_field,
                            'rule_percentage': rule.percentage,
                            'commission': apply_value * (rule.percentage / 100.0),
                            'deduction': 0,
                            'rule_max_days': rule.max_days,
                            'system_type': rule.system_type,
                            'notes': notes,
                            'commission_per_catg': commission_per_catg
                        })
                    else:
                        for h in history_ids:
                            h.rule_percentage = rule.percentage
                            h.commission = apply_value * (rule.percentage / 100.0)
                            h.deduction = 0
                            h.notes = notes
                            h.rule_max_days = rule.max_days
                            h.system_type = rule.system_type
                            h.commission_per_catg = commission_per_catg

                if rule.condition_field == 'jvr_days' and (invoice.system_type==rule.system_type): # and status_dates['first_fund_utr_skipped'] and status_dates['joint_verification_completed']
                    #days_diff = (status_dates['joint_verification_completed'] - status_dates['first_fund_utr_skipped']).days
                    #if rule.min_days <= days_diff <= rule.max_days:
                    condition_met = True
                    if not history_ids:
                        History.create({
                            'invoice_id': invoice.id,
                            'rule_type': 'commission',
                            'condition_field': rule.condition_field,
                            'rule_percentage': rule.percentage,
                            'commission': apply_value * (rule.percentage / 100.0),
                            'deduction': 0,
                            'rule_max_days': rule.max_days,
                            'system_type': rule.system_type,
                            'notes': notes,
                            'commission_per_catg': commission_per_catg
                        })
                    else:
                        for h in history_ids:
                            h.rule_percentage = rule.percentage
                            h.commission = apply_value * (rule.percentage / 100.0)
                            h.deduction = 0
                            h.notes = notes
                            h.rule_max_days = rule.max_days
                            h.system_type = rule.system_type
                            h.commission_per_catg = commission_per_catg
                    if rule.release_penalty_on:
                        release_penalty = True

                if condition_met:
                    commission += apply_value * (rule.percentage / 100.0)

            # --------------------
            # Deduction Calculation
            # --------------------
            for rule in DeductionRule.search([]):
                apply_value = getattr(invoice, rule.base_field, 0.0)
                condition_met = False
                notes = f"Deduction Rule: {rule.name}"
                history_ids = History.search([('commission_per_catg','=',commission_per_catg),('invoice_id','=',invoice.id),('rule_type','=','deduction'),('condition_field','=',rule.condition_field),('rule_max_days','=',rule.max_days),('system_type','=',rule.system_type)])

                if rule.condition_field == 'work_completion_days' and status_dates['eway_bill'] and status_dates['work_completed'] and (invoice.system_type==rule.system_type):
                    days_diff = (status_dates['work_completed'] - status_dates['eway_bill']).days
                    if days_diff > rule.max_days:
                        condition_met = True
                        release_penalty = True
                        if not history_ids:
                            History.create({
                                'invoice_id': invoice.id,
                                'rule_type': 'deduction',
                                'condition_field': rule.condition_field, 
                                'rule_percentage': rule.percentage,
                                'rule_max_days': rule.max_days,
                                'commission': 0,
                                'deduction': apply_value * (rule.percentage / 100.0),
                                'system_type': rule.system_type,
                                'notes': notes,
                                'commission_per_catg': commission_per_catg
                            })
                        else:
                            for h in history_ids:
                                h.rule_percentage = rule.percentage
                                h.rule_max_days = rule.max_days
                                h.commission = 0
                                h.deduction = apply_value * (rule.percentage / 100.0)
                                h.notes = notes
                                h.system_type = rule.system_type
                                h.commission_per_catg = commission_per_catg

                elif rule.condition_field == 'jvr_days' and status_dates['first_fund_utr_skipped'] and status_dates['joint_verification_completed'] and (invoice.system_type==rule.system_type):
                    days_diff = (status_dates['joint_verification_completed'] - status_dates['first_fund_utr_skipped']).days
                    if days_diff > rule.max_days:
                        condition_met = True
                        release_penalty = True
                        if not history_ids:
                            History.create({
                                'invoice_id': invoice.id,
                                'rule_type': 'deduction',
                                'condition_field': rule.condition_field,
                                'rule_percentage': rule.percentage,
                                'rule_max_days': rule.max_days,
                                'commission': 0,
                                'deduction': apply_value * (rule.percentage / 100.0),
                                'system_type': rule.system_type,
                                'notes': notes,
                                'commission_per_catg': commission_per_catg
                            })
                        else:
                            for h in history_ids:
                                h.rule_percentage = rule.percentage
                                h.rule_max_days = rule.max_days
                                h.commission = 0
                                h.deduction = apply_value * (rule.percentage / 100.0)
                                h.notes = notes
                                h.system_type = rule.system_type
                                h.commission_per_catg = commission_per_catg

                elif rule.condition_field == 'material_to_jvr_months' and status_dates['work_completed'] and status_dates['joint_verification_completed'] and status_dates['eway_bill'] and (invoice.system_type==rule.system_type):
                    total_days = (status_dates['joint_verification_completed'] - status_dates['eway_bill']).days
                    if total_days > 120:
                        months_delay = (total_days - 120) // 30
                        if months_delay > 0:
                            condition_met = True
                            apply_value = apply_value * months_delay
                            release_penalty = True
                            if not history_ids:
                                History.create({
                                    'invoice_id': invoice.id,
                                    'rule_type': 'deduction',
                                    'condition_field': rule.condition_field,
                                    'rule_percentage': rule.percentage * months_delay,
                                    'rule_max_days': rule.max_days,
                                    'commission': 0,
                                    'deduction': apply_value * (rule.percentage / 100.0),
                                    'system_type': rule.system_type,
                                    'notes': notes,
                                    'commission_per_catg': commission_per_catg
                                })
                            else:
                                for h in history_ids:
                                    h.rule_percentage = rule.percentage * months_delay
                                    h.rule_max_days = rule.max_days
                                    h.commission = 0
                                    h.deduction = apply_value * (rule.percentage / 100.0)
                                    h.notes = notes
                                    h.system_type = rule.system_type
                                    h.commission_per_catg = commission_per_catg


                if condition_met and release_penalty:
                    deduction += apply_value * (rule.percentage / 100.0)

            # --------------------
            # Set computed fields
            # --------------------
            invoice.commission = commission
            invoice.deduction = deduction
            invoice.commission_notes = f"Commission: {commission:.2f}, Deduction: {deduction:.2f}"
            
    @api.depends('commission', 'deduction')
    def _compute_commission_payable(self):
        for invoice in self:
            invoice.commission_payable = invoice.commission - invoice.deduction
        
        
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            # combine search on name and application_id
            domain = ['|',
                      ('name', operator, name),
                      ('application_id', operator, name)]
        # combine with other args
        domain = expression.AND([domain, args])
        # call super or use search
        moves = self.search(domain, limit=limit)
        return moves.name_get()
           
    def name_get(self):
        """Show invoice number + customer reference in dropdown"""
        result = []
        for move in self:
            display_name = move.name or ''
            if move.application_id:
                display_name = f"{move.application_id}"
            result.append((move.id, display_name))
        return result
        
