# -*- coding: utf-8 -*-

import io
import base64
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.misc import xlsxwriter
from datetime import datetime, timedelta

def get_dates_between(date_from, date_to):

    dates = []
    current_date = date_from

    while current_date <= date_to:
        dates.append(current_date)
        current_date += timedelta(days=1)

    return dates



class DealerStatementReportWizard(models.TransientModel):
    _name = 'dealer.statement.report.wizard'
    _description = 'Dealer Statement Report Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    dealer_id = fields.Many2one('res.partner', string='Dealer', required=True, domain=[('supplier_rank', '>', 0)])
    dealer_code = fields.Char(string='Dealer Code')
    download = fields.Binary(string='Download', readonly=True)
    filename = fields.Char(string='Filename', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_from > record.date_to:
                    raise ValidationError('Date From must be less than or equal to Date To.')

    def get_report_values(self):
        return self.env['account.payment'].sudo().search([
            ('payment_type', '=', 'outbound'),
            ('partner_type', '=', 'supplier'),
            ('memo', 'in', ['Advance', 'Commission']),
            ('partner_id', '=', self.dealer_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ])

    def action_generate_report(self):
        """Generate the vendor invoice XLSX report"""
        self.ensure_one()

        report_values = self.get_report_values()
        if not report_values:
            raise ValidationError('Data not found.')

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Dealer Statement')

        # Define formats
        header_label_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'font_size': 11,
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11,
        })

        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })

        text_format_no_border = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
        })

        date_format = workbook.add_format({
            'num_format': 'dd-mm-yyyy',
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })

        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
        })

        text_format_center = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        footer_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'bg_color': '#E6E6E6',
        })

        footer_label_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#E6E6E6',
        })

        worksheet.set_column(0, 0, 12)
        worksheet.set_column(1, 1, 25)
        worksheet.set_column(2, 2, 25)
        worksheet.set_column(3, 3, 20)
        worksheet.set_column(4, 4, 20)
        worksheet.set_column(5, 5, 20)

        worksheet.write(0, 0, 'Dealer Name:', header_label_format)
        worksheet.write(0, 1, self.dealer_id.name or '', text_format_no_border)
        worksheet.write(0, 4, 'Date From:', header_label_format)
        worksheet.write(0, 5, self.date_from.strftime('%d-%m-%Y'), text_format_no_border)

        worksheet.write(1, 0, 'Dealer Code:', header_label_format)
        worksheet.write(1, 1, self.dealer_code or '', text_format_no_border)
        worksheet.write(1, 4, 'Date To:', header_label_format)
        worksheet.write(1, 5, self.date_to.strftime('%d-%m-%Y'), text_format_no_border)

        header = [
            'Date',
            'Transaction',
            'Type',
            'Amount',
            'Payment',
            'Balance'
        ]

        row = 3
        col = 0
        for h in header:
            worksheet.write(row, col, h, header_format)
            col += 1

        dates = get_dates_between(self.date_from, self.date_to)

        total = 0
        def write_row(row, date, col1='', col2='', col3=0, col4=0, col5=''):
            worksheet.write(row, 0, date.strftime('%d-%m-%Y'), date_format)
            worksheet.write(row, 1, col1, text_format)
            worksheet.write(row, 2, col2, text_format_center)
            worksheet.write(row, 3, col3, currency_format)
            worksheet.write(row, 4, col4, currency_format)
            balance = col4 - col3
            worksheet.write(row, 5, balance, currency_format)
            return balance


        row = 4
        opening_written = False
        first_date = dates[0] if dates else None

        if first_date:
            total += write_row(row, first_date, 'Opening Balance')
            row += 1
            opening_written = True

        for date in dates:
            vals = report_values.filtered(lambda r: r.date == date)
            for rec in vals:
                total += write_row(row, date, 'Dealer Payment', rec.memo, 0, rec.amount, 0)
                row += 1

        footer_row = row
        worksheet.write(footer_row, 0, '', footer_label_format)
        worksheet.write(footer_row, 1, '', footer_label_format)
        worksheet.write(footer_row, 2, '', footer_label_format)
        worksheet.write(footer_row, 3, '', footer_label_format)
        worksheet.write(footer_row, 4, 'Balance', footer_label_format)
        worksheet.write(footer_row, 5, total, footer_format)


        workbook.close()
        output.seek(0)
        xlsx_data = output.read()
        output.close()

        filename = 'Dealer_Statement_Report_%s_%s.xlsx' % (
            self.date_from.strftime('%Y%m%d'),
            self.date_to.strftime('%Y%m%d')
        )

        self.write({
            'download': base64.b64encode(xlsx_data),
            'filename': filename,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=%s&id=%s&filename_field=filename&field=download&filename=%s&download=true' % (
                self._name, self.id, filename
            ),
            'target': 'self',
        }



