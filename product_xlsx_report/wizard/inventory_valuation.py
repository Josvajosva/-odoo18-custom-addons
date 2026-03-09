# -*- coding: utf-8 -*-
from odoo import models,fields,api,_
from collections import defaultdict
from odoo.exceptions import ValidationError
from datetime import date, timedelta,datetime
import io
import xlsxwriter
import base64


class InventoryValuationReport(models.TransientModel):
    _name = 'inventory.valuation.report'
    _description = 'Inventory Valuation Report'

    from_date = fields.Date(string = 'From Date', required = True)
    to_date = fields.Date(string = 'To Date', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        'res.company',
        'companies_inventory_valuation_report_rel',
        'inventory_valuation_report_id',
        'company_id',
        string="Companies",
        default=lambda self: self.env.company,
    )
    xls_file = fields.Binary(string="XLS file")
    xls_filename = fields.Char()

    @api.model
    def default_get(self, fields):
        context = self._context
        res = super().default_get(fields)
        res.update({
            'company_ids': [(6, 0, context.get('allowed_company_ids', [self.env.company.id]))],
            'company_id': context.get('allowed_company_ids', [self.env.company.id])[0],
        })
        return res
   
    @api.constrains('from_date', 'to_date')
    def _check_date_range(self):
        for record in self:
            if record.to_date < record.from_date:
                raise ValidationError("To Date cannot be earlier than From Date.")
   
    def _verify_data_exists(
            self,
            formatted_from_date,
            formatted_to_date
    ):
        inventory_move_lines = self.env['stock.move.line'].search([
            ('state', '=', 'done'),
            ('date', '>=', formatted_from_date),
            ('date', '<=', formatted_to_date),
            ('is_inventory', '=', True),
            ('company_id', 'in', self.company_ids.ids),
        ])
        
        if not inventory_move_lines:
            raise ValidationError(
                _("No inventory adjustments found for the selected date range.\n"
                  "From Date: %s\n"
                  "To Date: %s\n\n"
                  "Please select a date range that contains inventory adjustment records.") % 
                (self.from_date.strftime('%Y-%m-%d'), self.to_date.strftime('%Y-%m-%d'))
            )
        
        return inventory_move_lines

    def _prepare_report_data(self):
        formatted_from_date = datetime.combine(self.from_date, datetime.min.time())
        formatted_to_date = datetime.combine(self.to_date, datetime.max.time())

        inventory_move_lines = self._verify_data_exists(
            formatted_from_date,
            formatted_to_date
        )

        product_ids = inventory_move_lines.mapped('product_id').ids
        
        product_data = defaultdict(lambda: {
            'name': '',
            'on_hand_qty_at_to_date': 0.0,
            'physical_qty': 0.0,
            'from_location': '',
            'to_location': '',
            'product_category': '',
            'uom_id': '',
            'sales_price': 0.0,
        })
        
        products = self.env['product.product'].with_context(
            to_date=formatted_to_date,
            allowed_company_ids=self.company_ids.ids,
        ).browse(product_ids)
        
        for product in products:
            product_category = product.categ_id.display_name if product.categ_id else ''
            uom_id = product.uom_id.name if product.uom_id else ''
            sales_price = product.list_price if product.list_price else 0.0
            
            on_hand_qty = product.qty_available
            
            product_data[product.id]['name'] = product.display_name
            product_data[product.id]['on_hand_qty_at_to_date'] = on_hand_qty
            product_data[product.id]['product_category'] = product_category
            product_data[product.id]['uom_id'] = uom_id
            product_data[product.id]['sales_price'] = sales_price
        
        location_map = {}
        for move_line in inventory_move_lines:
            product_id = move_line.product_id.id
            location_from = move_line.location_id.display_name
            location_to = move_line.location_dest_id.display_name
            
            product_data[product_id]['physical_qty'] += move_line.qty_done
            
            if product_id not in location_map:
                location_map[product_id] = {
                    'from_location': location_from,
                    'to_location': location_to
                }
            else:
                if location_from and location_from not in location_map[product_id]['from_location']:
                    if location_map[product_id]['from_location']:
                        location_map[product_id]['from_location'] += ', ' + location_from
                    else:
                        location_map[product_id]['from_location'] = location_from
                if location_to and location_to not in location_map[product_id]['to_location']:
                    if location_map[product_id]['to_location']:
                        location_map[product_id]['to_location'] += ', ' + location_to
                    else:
                        location_map[product_id]['to_location'] = location_to
        
        for product_id, loc_data in location_map.items():
            product_data[product_id]['from_location'] = loc_data['from_location']
            product_data[product_id]['to_location'] = loc_data['to_location']
        
        return product_data

    def action_print_xlsx(self):
        product_data = self._prepare_report_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Stock Variance')
        style_highlight = workbook.add_format({'bold': True, 'bg_color': '#E0E0E0', 'align': 'center', 'text_wrap': True, 'valign': 'vcenter'})
        style_highlight_left = workbook.add_format({'bold': True, 'bg_color': '#E0E0E0', 'align': 'left', 'text_wrap': True, 'valign': 'vcenter'})
        style_normal = workbook.add_format({'align': 'center', 'text_wrap': True, 'valign': 'vcenter'})
        style_normal_left = workbook.add_format({'align': 'left', 'text_wrap': True, 'valign': 'vcenter'})
        style_title = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center', 'text_wrap': True, 'valign': 'vcenter'})

        headers = [
            "S.no",
            'From Location',
            'To Location',
            "Product name",
            "Product Category(parent)",
            "UOM",
            "Sales price",
            "Book Stock(On Hand Qty)",
            "Physical Stock(Counted Qty)",
            "Variance In Qty",
            "Book Stock Value",
            "Physical Stock Value",
            "Variance In Value",
            "Variance in(%)"
        ]

        row = 1
        col = 0
        worksheet.merge_range(f'A{row}:N{row}', 'Stock Variance Report', style_highlight)
        row += 1
        worksheet.write(row, 0, "From Date", style_title)
        worksheet.write(row, 1, self.from_date.strftime('%Y-%m-%d'), style_normal)
        worksheet.write(row, 3, "To Date", style_title)
        worksheet.write(row, 4, self.to_date.strftime('%Y-%m-%d'), style_normal)

        row += 1
        col = 0
        column_widths = [
            12,   # S.no
            25,  # From Location
            25,  # To Location
            40,  # Product name
            28,  # Product Category(parent)
            10,  # UOM
            12,  # Sales price
            20,  # Book Stock(On Hand Qty)
            22,  # Physical Stock(Counted Qty)
            15,  # Variance In Qty
            18,  # Book Stock Value
            20,  # Physical Stock Value
            18,  # Variance In Value
            15,  # Variance in(%)
        ]
        
        for header in headers:
            worksheet.write(row, col, header, style_highlight)
            worksheet.set_column(col, col, column_widths[col])
            col += 1
        
        worksheet.set_row(row, 30)

        row += 1
        count = 1

        for prod_id, data in product_data.items():
            book_stock = data['on_hand_qty_at_to_date']

            physical_stock = data['physical_qty']

            variance_in_qty = book_stock - physical_stock

            book_stock_value = book_stock * data['sales_price']
            physical_stock_value = physical_stock * data['sales_price']
            variance_in_value = variance_in_qty * data['sales_price']

            variance_in_percentage = (variance_in_qty / book_stock * 100) if book_stock != 0 else (100 if physical_stock > 0 else 0)

            worksheet.write(row, 0, count, style_normal)
            worksheet.write(row, 1, data['from_location'], style_normal_left)
            worksheet.write(row, 2, data['to_location'], style_normal_left)
            worksheet.write(row, 3, data['name'], style_normal_left)
            worksheet.write(row, 4, data['product_category'], style_normal)
            worksheet.write(row, 5, data['uom_id'], style_normal)
            worksheet.write(row, 6, "{:.2f}".format(data['sales_price']), style_normal)
            worksheet.write(row, 7, "{:.2f}".format(book_stock), style_normal)
            worksheet.write(row, 8, "{:.2f}".format(physical_stock), style_normal)
            worksheet.write(row, 9, "{:.2f}".format(variance_in_qty), style_normal)
            worksheet.write(row, 10, "{:.2f}".format(book_stock_value), style_normal)
            worksheet.write(row, 11, "{:.2f}".format(physical_stock_value), style_normal)
            worksheet.write(row, 12, "{:.2f}".format(variance_in_value), style_normal)
            worksheet.write(row, 13, "{:.2f}".format(variance_in_percentage), style_normal)

            row += 1
            count += 1

        workbook.close()
        xlsx_data = output.getvalue()
        output.close()
        self.xls_file = base64.encodebytes(xlsx_data)
        self.xls_filename = "stock_variance_report.xlsx"

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }