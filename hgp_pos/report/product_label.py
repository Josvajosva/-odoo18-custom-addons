from odoo import _, models
from odoo.addons.product.report.product_label_report import _prepare_data


class ReportProductTemplateLabel3x1(models.AbstractModel):
    _name = 'report.hgp_pos.report_producttemplatelabel3x1'
    _description = 'Product Label Report 3x1'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)