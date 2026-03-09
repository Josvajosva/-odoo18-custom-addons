from odoo import models, fields, api
import datetime
import io
import base64
from openpyxl import Workbook

class DealerwiseCommissionWizard(models.TransientModel):
    _name = 'dealerwise.commission.wizard'
    _description = 'Dealerwise Commission Report Wizard'

    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)
    line_ids = fields.One2many('dealerwise.commission.line', 'wizard_id', string="Dealerwise Lines")
    excel_file = fields.Binary("Excel File")
    excel_file_name = fields.Char("Excel Filename")
    total_invoice_count = fields.Integer(string="Total Invoices", compute="_compute_totals")
    total_first_commission = fields.Float(string="Total First Fund", compute="_compute_totals")
    total_second_commission = fields.Float(string="Total Final Fund", compute="_compute_totals")
    total_commission = fields.Float(string="Grand Total", compute="_compute_totals")

    dealer_name = fields.Char(string="Dealer Name")
    invoice_count = fields.Integer(string="No. of Invoices")
    first_fund_commission = fields.Float(string="First Fund Commission")
    second_fund_commission = fields.Float(string="Final Fund Commission")
    total_commission = fields.Float(string="Total Commission")

    @api.depends('line_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_invoice_count = sum(line.invoice_count for line in rec.line_ids)
            rec.total_first_commission = sum(line.first_fund_commission for line in rec.line_ids)
            rec.total_second_commission = sum(line.second_fund_commission for line in rec.line_ids)
            rec.total_commission = sum(line.total_commission for line in rec.line_ids)

    def action_print_commission_report(self):
        return self.env.ref('pipes_project.dealerwise_commission_report_action').report_action(self)

    def get_dealer_summary_data(self):
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('dealer_id', '!=', False),
        ])

        filtered_invoices = invoices.filtered(lambda inv: (
            (inv.fund_credit_date and self.date_from <= inv.fund_credit_date <= self.date_to)
            or
            (inv.first_fund_utr_skipped_date and self.date_from <= inv.first_fund_utr_skipped_date <= self.date_to)
        ))

        utr_cutoff_date = datetime.date(2024, 10, 1)
        dealer_data = {}

        for inv in filtered_invoices:
            dealer = inv.dealer_id
            if not dealer:
                continue

            if dealer.id not in dealer_data:
                dealer_data[dealer.id] = {
                    'dealer': dealer,
                    'invoice_count': 0,
                    'total_first_commission': 0.0,
                    'total_second_commission': 0.0,
                }

            first_commission_after_tds = 0.0
            second_commission_after_tds = 0.0

            tds_rate = 0.02 if inv.invoice_date >= utr_cutoff_date else 0.05

            if inv.first_fund_utr_skipped_date and (self.date_from <= inv.first_fund_utr_skipped_date <= self.date_to):
                first_commission = sum(inv.commission_history_ids.filtered(lambda h: h.rule_percentage == 8).mapped('commission'))
                first_commission_after_tds = first_commission - (first_commission * tds_rate)

            if inv.fund_credit_date and (self.date_from <= inv.fund_credit_date <= self.date_to):
                second_commission = sum(inv.commission_history_ids.filtered(lambda h: h.rule_percentage == 12).mapped('commission'))
                second_commission_after_tds = second_commission - (second_commission * tds_rate)

            dealer_data[dealer.id]['total_first_commission'] += first_commission_after_tds
            dealer_data[dealer.id]['total_second_commission'] += second_commission_after_tds
            dealer_data[dealer.id]['invoice_count'] += 1

        return dealer_data

    def action_view_report(self):
        self.line_ids.unlink()
        dealer_data = self.get_dealer_summary_data()

        for dealer in dealer_data.values():
            total_first = dealer.get('total_first_commission', 0.0)
            total_second = dealer.get('total_second_commission', 0.0)
            self.env['dealerwise.commission.line'].create({
                'wizard_id': self.id,
                'dealer_name': dealer['dealer'].name,
                'invoice_count': dealer.get('invoice_count', 0),
                'first_fund_commission': total_first,
                'second_fund_commission': total_second,
                'total_commission': total_first + total_second,
            })

        return {
            'name': 'Dealerwise Commission Report',
            'type': 'ir.actions.act_window',
            'res_model': 'dealerwise.commission.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('pipes_project.view_dealerwise_commission_report_form').id,
            'target': 'current',
        }

    def action_export_excel(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Dealerwise Commission Report"

        headers = ['Dealer Name', 'No. of Invoices', 'First Fund Commission',
                   'Final Fund Commission', 'Total Commission']
        sheet.append(headers)

        for line in self.line_ids:
            sheet.append([
                line.dealer_name or '',
                line.invoice_count or 0,
                line.first_fund_commission or 0,
                line.second_fund_commission or 0,
                line.total_commission or 0,
            ])

        if self.line_ids:
            sheet.append([])
            sheet.append([
                "GRAND TOTAL",
                self.total_invoice_count,
                self.total_first_commission,
                self.total_second_commission,
                self.total_commission,
            ])

        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        file_data = base64.b64encode(data)
        file_name = f"Dealerwise_Commission_Report_{self.date_from}_{self.date_to}.xlsx"

        self.write({
            'excel_file': file_data,
            'excel_file_name': file_name,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model=dealerwise.commission.wizard&id={self.id}&field=excel_file&filename_field=excel_file_name&download=true",
            'target': 'self',
        }

    def action_open_payment_report(self):
        """Open payment wizard pre-filled with same dealers"""
        payment_wizard = self.env['dealerwise.commission.payment.wizard'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        return payment_wizard.action_view_payment_report()

class DealerwiseCommissionLine(models.TransientModel):
    _name = 'dealerwise.commission.line'
    _description = 'Dealerwise Commission Report Line'

    wizard_id = fields.Many2one('dealerwise.commission.wizard', ondelete='cascade')
    dealer_name = fields.Char(string="Dealer Name")
    invoice_count = fields.Integer(string="No. of Invoices")
    first_fund_commission = fields.Float(string="First Fund Commission")
    second_fund_commission = fields.Float(string="Final Fund Commission")
    total_commission = fields.Float(string="Total Commission")

class DealerwiseCommissionPaymentWizard(models.TransientModel):
    _name = 'dealerwise.commission.payment.wizard'
    _description = 'Dealerwise Commission Payment Wizard'

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")
    line_ids = fields.One2many('dealerwise.commission.payment.line', 'wizard_id', string="Dealer Payment Lines")

    dealer_name = fields.Char(string="Dealer Name")
    invoice_count = fields.Integer(string="No. of Invoices", readonly=True)
    total_commission = fields.Float(string="Total Commission", readonly=True)
    payment_date = fields.Date(string="Payment Date")
    payment_amount = fields.Float(string="Payment Amount")
    balance = fields.Float(string="Balance", compute="_compute_balance", store=True)

    def action_view_payment_report(self):
        """Load dealers from the dealerwise.commission.wizard"""
        dealerwise = self.env['dealerwise.commission.wizard'].browse(self.env.context.get('active_id'))
        self.date_from = dealerwise.date_from
        self.date_to = dealerwise.date_to

        self.line_ids.unlink()
        for line in dealerwise.line_ids:
            self.env['dealerwise.commission.payment.line'].create({
                'wizard_id': self.id,
                'dealer_name': line.dealer_name,
                'invoice_count': line.invoice_count,
                'total_commission': line.total_commission,
            })

        return {
            'name': 'Dealerwise Payment Report',
            'type': 'ir.actions.act_window',
            'res_model': 'dealerwise.commission.payment.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('pipes_project.view_dealerwise_commission_payment_form').id,
            'target': 'current',
        }


class DealerwiseCommissionPaymentLine(models.TransientModel):
    _name = 'dealerwise.commission.payment.line'
    _description = 'Dealerwise Commission Payment Report Line'

    wizard_id = fields.Many2one('dealerwise.commission.payment.wizard', ondelete='cascade')
    dealer_name = fields.Char(string="Dealer Name")
    invoice_count = fields.Integer(string="No. of Invoices", readonly=True)
    total_commission = fields.Float(string="Total Commission", readonly=True)
    payment_date = fields.Date(string="Payment Date")
    payment_amount = fields.Float(string="Payment Amount")
    balance = fields.Float(string="Balance", compute="_compute_balance", store=True)

    @api.depends('payment_amount', 'total_commission')
    def _compute_balance(self):
        """Auto calculate balance"""
        for rec in self:
            rec.balance = (rec.total_commission or 0.0) - (rec.payment_amount or 0.0)