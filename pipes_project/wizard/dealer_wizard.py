from odoo import models, fields, api
import datetime
import io
import base64
from openpyxl import Workbook

class DealerCommissionWizard(models.TransientModel):
    _name = 'dealer.commission.wizard'
    _description = 'Dealer Commission Report Wizard'

    dealer_id = fields.Many2one('res.partner', string="Dealer", required=True)
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    line_ids = fields.One2many('dealer.commission.line', 'wizard_id', string="Report Lines")
    excel_file = fields.Binary("Excel File")
    excel_file_name = fields.Char("Excel Filename")
    total_material_value = fields.Float(string="Material Value", compute="_compute_totals")
    total_commission_amount = fields.Float(string="Commission Amount", compute="_compute_totals")
    total_first_fund = fields.Float(string="First Fund Commission", compute="_compute_totals")
    total_first_after_tds = fields.Float(string="First Fund after TDS", compute="_compute_totals")
    total_final_fund = fields.Float(string="Final Fund Commission", compute="_compute_totals")
    total_final_after_tds = fields.Float(string="Final Fund after TDS", compute="_compute_totals")
    total_deduction = fields.Float(string="Deduction", compute="_compute_totals")
    total_net_payable = fields.Float(string="Net Payable", compute="_compute_totals")
    
    application_id = fields.Char(string="Application ID")
    farmer_name = fields.Char(string="Farmer Name")
    material_value = fields.Float(string="Material Value")
    commission_amount = fields.Float(string="Commission Amount")
    first_fund_commission = fields.Float(string="First Fund Commission")
    first_after_tds = fields.Float(string="First Fund Commission after TDS")
    first_utr_date = fields.Date(string="First Fund UTR Date")
    final_fund_commission = fields.Float(string="Final Fund Commission")
    final_after_tds = fields.Float(string="Final Fund Commission after TDS")
    final_utr_date = fields.Date(string="Final Fund UTR Date")
    deduction_45 = fields.Float(string="Deduction > 45 Days")
    deduction_60 = fields.Float(string="Deduction > 60 Days")
    deduction_120 = fields.Float(string="Deduction > 120 Days")
    total_deduction = fields.Float(string="Total Deduction")
    net_payable = fields.Float(string="Net Payable")
    current_status = fields.Char(string="Current Status")

    @api.depends('line_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_material_value = sum(line.material_value for line in rec.line_ids)
            rec.total_commission_amount = sum(line.commission_amount for line in rec.line_ids)
            rec.total_first_fund = sum(line.first_fund_commission for line in rec.line_ids)
            rec.total_first_after_tds = sum(line.first_after_tds for line in rec.line_ids)
            rec.total_final_fund = sum(line.final_fund_commission for line in rec.line_ids)
            rec.total_final_after_tds = sum(line.final_after_tds for line in rec.line_ids)
            rec.total_deduction = sum(line.total_deduction for line in rec.line_ids)
            rec.total_net_payable = sum(line.net_payable for line in rec.line_ids)

    def action_print_report(self):
        return self.env.ref('pipes_project.dealer_commission_report_action').report_action(self)
    
    def get_filtered_invoices(self):
        """Return invoices for the dealer where either the First Fund or Final Fund date is within range"""
        all_invoices = self.env['account.move'].search([
            ('dealer_id', '=', self.dealer_id.id),
            ('move_type', '=', 'out_invoice'),
        ])

        filtered_invoices = all_invoices.filtered(lambda inv: (
            (inv.fund_credit_date and self.date_from <= inv.fund_credit_date <= self.date_to)
            or
            (inv.first_fund_utr_skipped_date and self.date_from <= inv.first_fund_utr_skipped_date <= self.date_to)
        ))

        return filtered_invoices

    def action_view_report(self):
        """Compute report lines and show them in form view (same logic as PDF)."""
        self.line_ids.unlink()
        invoices = self.get_filtered_invoices()
        deduction_cutoff = datetime.date(2025, 9, 1)
        utr_cutoff_date = datetime.date(2024, 10, 1)

        for inv in invoices:
            first_commission = 0.0
            first_after_tds = 0.0
            final_fund_commission = 0.0
            final_after_tds = 0.0

            if inv.first_fund_utr_skipped_date and (self.date_from <= inv.first_fund_utr_skipped_date <= self.date_to):
                first_commission = sum(inv.commission_history_ids.filtered(lambda h: h.rule_percentage == 8).mapped('commission'))
                tds_rate = 0.02 if inv.invoice_date >= utr_cutoff_date else 0.05
                first_after_tds = first_commission - (first_commission * tds_rate)

            deduction = inv.deduction if inv.invoice_date >= deduction_cutoff else 0
            second_commission = sum(inv.commission_history_ids.filtered(lambda h: h.rule_percentage == 12).mapped('commission'))
            second_after_deduction = second_commission - deduction

            if inv.fund_credit_date and (self.date_from <= inv.fund_credit_date <= self.date_to):
                tds_rate = 0.02 if inv.invoice_date >= utr_cutoff_date else 0.05
                final_fund_commission = second_after_deduction
                final_after_tds = second_after_deduction - (second_after_deduction * tds_rate)

            deduction_45 = sum(inv.commission_history_ids.filtered(lambda h: h.rule_max_days == 45).mapped('deduction')) if inv.invoice_date >= deduction_cutoff else 0
            deduction_60 = sum(inv.commission_history_ids.filtered(lambda h: h.rule_max_days == 60).mapped('deduction')) if inv.invoice_date >= deduction_cutoff else 0
            deduction_120 = sum(inv.commission_history_ids.filtered(lambda h: h.rule_max_days == 120).mapped('deduction')) if inv.invoice_date >= deduction_cutoff else 0

            self.env['dealer.commission.line'].create({
                'wizard_id': self.id,
                'application_id': inv.application_id,
                'farmer_name': inv.partner_id.name,
                'material_value': inv.amount_total,
                'commission_amount': inv.commission,
                'first_fund_commission': first_commission,
                'first_after_tds': first_after_tds,
                'first_utr_date': inv.first_fund_utr_skipped_date,
                'final_fund_commission': final_fund_commission,
                'final_after_tds': final_after_tds,
                'final_utr_date': inv.fund_credit_date,
                'deduction_45': deduction_45,
                'deduction_60': deduction_60,
                'deduction_120': deduction_120,
                'total_deduction': deduction,
                'net_payable': first_after_tds + final_after_tds,
                'current_status': self.get_work_status_label(inv.work_status),
            })

        return {
            'name': 'Dealer Commission Report',
            'type': 'ir.actions.act_window',
            'res_model': 'dealer.commission.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('pipes_project.view_dealer_commission_wizard_report').id,
            'target': 'current',
        }
    
    def action_export_excel(self):
        """Generate and download Excel version of the report with totals"""
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Dealer Commission Report"

        headers = [
            'Application ID', 'Farmer Name', 'Material Value', 'Commission Amount',
            'First Fund Commission', 'First Fund after TDS', 'First UTR Date',
            'Final Fund Commission', 'Final Fund after TDS', 'Final UTR Date',
            'Deduction > 45 Days', 'Deduction > 60 Days', 'Deduction > 120 Days',
            'Total Deduction', 'Net Payable', 'Current Status'
        ]
        sheet.append(headers)

        for line in self.line_ids:
            sheet.append([
                line.application_id or '',
                line.farmer_name or '',
                line.material_value or 0,
                line.commission_amount or 0,
                line.first_fund_commission or 0,
                line.first_after_tds or 0,
                str(line.first_utr_date or ''),
                line.final_fund_commission or 0,
                line.final_after_tds or 0,
                str(line.final_utr_date or ''),
                line.deduction_45 or 0,
                line.deduction_60 or 0,
                line.deduction_120 or 0,
                line.total_deduction or 0,
                line.net_payable or 0,
                line.current_status or '',
            ])

        if self.line_ids:
            sheet.append([])
            sheet.append([
                'GRAND TOTAL', '',
                self.total_material_value,
                self.total_commission_amount,
                self.total_first_fund,
                self.total_first_after_tds,
                '',
                self.total_final_fund,
                self.total_final_after_tds,
                '',
                '', '', '',
                self.total_deduction,
                self.total_net_payable,
                ''
            ])

        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        file_data = base64.b64encode(data)
        file_name = f"Dealer_Commission_Report_{self.dealer_id.name or 'Dealer'}_{self.date_from}_{self.date_to}.xlsx"

        self.write({
            'excel_file': file_data,
            'excel_file_name': file_name,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model=dealer.commission.wizard&id={self.id}&field=excel_file&filename_field=excel_file_name&download=true",
            'target': 'self',
        }

    # def get_work_status_label(self, work_status):
    #     """Map work_status technical values to human-readable labels"""
    #     status_mapping = {
    #         'issued_work_order': 'Issued Work Order',
    #         'work_completed': 'Work Completed',
    #         'work_completion_approved': 'Work Completion Approved',
    #         'fund_release_recommended_block': 'Fund Release Recommended by Block Office',
    #         'fund_release_recommended_district': 'Fund Release Recommended by District Office',
    #         'rectification_approved_block': 'Mi Company Rectification Approved By Block',
    #         'rectification_reverted_block': 'Mi Company Rectification Reverted By Block',
    #         'fund_release_approved_agri': 'First Fund Release Approved by State Agri',
    #         'fund_release_approved_horti': 'First Fund Release Approved by State Horticulture',
    #         'utr_skipped': 'District First Fund UTR Updated',
    #         'joint_verification_completed': 'Joint Verification Completed',
    #         'fund_release_proceeding_completed': 'Fund Release Proceeding Completed',
    #         'fund_credited': 'Final Fund UTR Updated',
    #     }
    #     return status_mapping.get(work_status, work_status or '')

    def get_work_status_label(self, work_status):
        mapping = {
            'application_received': 'Application Received',
            'approved_by_block': 'Approved by Block Officer',
            'dd_upload_skipped': 'DD Upload Skipped',
            'district_first_fund_credited': 'District First Fund Credited (UTR Updated)',
            'district_first_fund_proceeding_completed': 'District First Fund Proceeding Completed',
            'farmer_acceptance_uploaded': 'Farmer Acceptance Letter Uploaded',
            'fund_credited': 'Final Fund Credited (UTR Updated)',
            'final_fund_release_recommended_district': 'Final Fund Release Recommended by District Office',
            'first_fund_credited': 'First Fund Credited (UTR Updated)',
            'first_fund_proceeding_completed': 'First Fund Proceeding Completed',
            'fund_release_proceeding_completed': 'Fund Release Proceeding Completed',
            'fund_release_recommended_block': 'Fund Release Recommended by Block Office',
            'fund_release_recommended_district': 'Fund Release Recommended by District Office',
            'fund_release_approved_agri': 'Fund Release Verification by State Agriculture',
            'fund_release_approved_horti': 'Fund Release Verification by State Horticulture',
            'issued_work_order': 'Issued Work Order',
            'joint_verification_completed': 'Joint Verification Completed',
            'layout_image_uploaded': 'Layout Image and GPS Image Uploaded',
            'rectification_approved_block': 'Mi Company Rectification Approved By Block',
            'rectification_reverted_block': 'Mi Company Rectification Reverted By Block',
            'preinspection_revised_quotation': 'Pre Inspection - Request for Revised Quotation',
            'preinspection_approved': 'Pre Inspection Approved',
            'quotation_copy_uploaded': 'Quotation Copy Uploaded by MI Company',
            'quotation_prepared_mi': 'Quotation Prepared by MI Company',
            'reverted_rectified_by_block': 'Reverted Application Rectified By Block',
            'reverted_rectified_by_mi': 'Reverted Application Rectified By MI Company',
            'reverted_state_agri_horti': 'Reverted By State Agri / Horti',
            'reverted_state_agri_horti_block': 'Reverted by State Agri / Horti to Block',
            'work_completed': 'Work Completed',
            'work_completion_approved': 'Work Completion Approved',
        }
        return mapping.get(work_status, work_status or '')

class DealerCommissionLine(models.TransientModel):
    _name = 'dealer.commission.line'
    _description = 'Dealer Commission Report Line'
    _order = 'application_id'

    wizard_id = fields.Many2one('dealer.commission.wizard', ondelete='cascade')
    application_id = fields.Char(string="Application ID")
    farmer_name = fields.Char(string="Farmer Name")
    material_value = fields.Float(string="Material Value")
    commission_amount = fields.Float(string="Commission Amount")
    first_fund_commission = fields.Float(string="First Fund Commission")
    first_after_tds = fields.Float(string="First Fund Commission after TDS")
    first_utr_date = fields.Date(string="First Fund UTR Date")
    final_fund_commission = fields.Float(string="Final Fund Commission")
    final_after_tds = fields.Float(string="Final Fund Commission after TDS")
    final_utr_date = fields.Date(string="Final Fund UTR Date")
    deduction_45 = fields.Float(string="Deduction > 45 Days")
    deduction_60 = fields.Float(string="Deduction > 60 Days")
    deduction_120 = fields.Float(string="Deduction > 120 Days")
    total_deduction = fields.Float(string="Total Deduction")
    net_payable = fields.Float(string="Net Payable")
    current_status = fields.Char(string="Current Status")