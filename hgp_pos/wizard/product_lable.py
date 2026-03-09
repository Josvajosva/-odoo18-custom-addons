from odoo import _, api, fields, models
from odoo.exceptions import UserError

class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'
    _description = 'Choose the sheet layout to print the labels'

    print_format = fields.Selection(selection_add=[
        ('3x1xprice', '3 x 1 with price'),
    ], ondelete={'3x1xprice': 'set default'}, default='3x1xprice')
    cvm_formate = fields.Char(string='Formate', default='3x1xprice')


    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise UserError(_('You need to set a positive quantity.'))

        # Get layout grid
        if self.print_format == 'dymo':
            xml_id = 'product.report_product_template_label_dymo'
        elif 'x' in self.print_format:
            xml_id = 'product.report_product_template_label_%sx%s' % (self.columns, self.rows)
            if self.print_format == '3x1xprice':
                xml_id = 'hgp_pos.report_product_template_label_%sx%s' % (self.columns, self.rows)
            if 'xprice' not in self.print_format:
                xml_id += '_noprice'
        else:
            xml_id = ''

        active_model = ''
        if self.product_tmpl_ids:
            products = self.product_tmpl_ids.ids
            active_model = 'product.template'
        elif self.product_ids:
            products = self.product_ids.ids
            active_model = 'product.product'
        else:
            raise UserError(_("No product to print, if the product is archived please unarchive it before printing its label."))

        # Build data to pass to the report
        data = {
            'active_model': active_model,
            'quantity_by_product': {p: self.custom_quantity for p in products},
            'layout_wizard': self.id,
            'price_included': 'xprice' in self.print_format,
        }
        return xml_id, data
