from odoo import models, fields

class DealerCommissionWizard(models.TransientModel):
    _name = 'dealer.commission.wizard'
    _description = 'Dealer Commission Report Wizard'

    dealer_id = fields.Many2one('res.partner', string="Dealer", required=True)
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)

    def action_print_report(self):
        return self.env.ref('pipes_project.dealer_commission_report_action').report_action(self)

    def get_filtered_invoices(self):
        """Return invoices for the dealer based on Fund Credit Date or First Fund UTR Update Date"""
        all_invoices = self.env['account.move'].search([
            ('dealer_id', '=', self.dealer_id.id),
            ('move_type', '=', 'out_invoice'),
        ])

        filtered_invoices = all_invoices.filtered(lambda inv: (
            (
                inv.fund_credit_date and self.date_from <= inv.fund_credit_date <= self.date_to
            ) or (
                not inv.fund_credit_date and inv.first_fund_utr_skipped_date
                and self.date_from <= inv.first_fund_utr_skipped_date <= self.date_to
            )
        ))

        return filtered_invoices

    def get_work_status_label(self, work_status):
        """Map work_status technical values to human-readable labels"""
        status_mapping = {
            'issued_work_order': 'Issued Work Order',
            'work_completed': 'Work Completed',
            'work_completion_approved': 'Work Completion Approved',
            'fund_release_recommended_block': 'Fund Release Recommended by Block Office',
            'fund_release_recommended_district': 'Fund Release Recommended by District Office',
            'rectification_approved_block': 'Mi Company Rectification Approved By Block',
            'rectification_reverted_block': 'Mi Company Rectification Reverted By Block',
            'fund_release_approved_agri': 'First Fund Release Approved by State Agri',
            'fund_release_approved_horti': 'First Fund Release Approved by State Horticulture',
            'utr_skipped': 'First Fund UTR Updated',
            'joint_verification_completed': 'Joint Verification Completed',
            'fund_release_proceeding_completed': 'Fund Release Proceeding Completed',
            'fund_credited': 'Fund Credited (UTR Updated)',
        }
        return status_mapping.get(work_status, work_status or '')
