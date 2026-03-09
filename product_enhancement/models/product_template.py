# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    type_master_id = fields.Many2one(
        'type.master',
        string='Type Master',
        help="Type master for this product"
    )

    def write(self, vals):
        res = super().write(vals)
        if 'categ_id' in vals:
            for template in self:
                if template.categ_id:
                    for product in template.product_variant_ids:
                        category = template.categ_id
                        next_code, used_number = category._get_next_product_code()
                        if next_code and used_number:
                            product.with_context(_assigning_default_code=True).default_code = next_code
                            category.write({'number': used_number + 1})
        return res

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Product Category'),
            'template': '/product_enhancement/static/xls/product.xlsx'
        }]