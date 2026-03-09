from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
import base64

class CommissionReportWizard(models.TransientModel):
    _name = 'commission.report.wizard'
    _description = 'Commission Report Wizard'

    app_id = fields.Many2one(
        'account.move',
        string="Application ID",
        required=True,
    )

    def action_download_pdf(self):
        """Generate PDF report using QWeb template"""
        try:
            selected_app = self.app_id
            
            if selected_app.application_id:
                invoices = self.env['account.move'].search([
                    ('application_id', '=', selected_app.application_id),
                ])
            else:
                invoices = selected_app
            
            partner_id = selected_app.partner_id
            
            total_commission = sum(inv.commission or 0 for inv in invoices)
            total_material_value = sum(inv.amount_untaxed for inv in invoices)
            
            data = {
                'partner_id': partner_id,
                'application_id': selected_app.application_id or 'N/A',
                'invoices': invoices,
                'total_commission': total_commission,
                'total_material_value': total_material_value,
                'current_date': date.today().strftime('%Y-%m-%d'),
            }
            
            pdf_content = self.env['ir.actions.report']._render(
                'pipes_project.report_commission_template',
                invoices.ids,
                data=data
            )
            
            if pdf_content and pdf_content[0]:
                attachment = self.env['ir.attachment'].create({
                    'name': f'commission_report_{selected_app.application_id or selected_app.name}_{date.today()}.pdf',
                    'datas': base64.b64encode(pdf_content[0]),
                    'res_model': self._name,
                    'res_id': self.id,
                    'type': 'binary'
                })
                
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/web/content/{attachment.id}?download=true',
                    'target': 'new',
                }
            else:
                raise UserError("Could not generate PDF content")
            
        except Exception as e:
            raise UserError(f"Error generating report: {str(e)}")