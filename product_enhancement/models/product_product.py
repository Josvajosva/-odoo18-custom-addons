# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate default_code when creating variants with category.
        Skip sequence for the first auto-created variant if the template
        has attribute lines (variants will be recreated later).
        """
        for vals in vals_list:
            if not vals.get('default_code'):
                product_tmpl_id = vals.get('product_tmpl_id')
                if product_tmpl_id:
                    template = self.env['product.template'].browse(product_tmpl_id)
                    has_attributes = vals.get('product_template_attribute_value_ids')
                    if template.attribute_line_ids and not has_attributes:
                        continue
                    if template.categ_id:
                        category = template.categ_id
                        next_code, used_number = category._get_next_product_code()
                        if next_code and used_number:
                            vals['default_code'] = next_code
                            next_sequence = used_number + 1
                            category.write({'number': next_sequence})
        return super().create(vals_list)

    # def write(self, vals):
    #     """Assign default_code to existing products that don't have one."""
    #     res = super().write(vals)
    #     if self.env.context.get('_assigning_default_code'):
    #         return res
    #     for product in self:
    #         if not product.categ_id or not product.categ_id.prefix:
    #             continue
    #         category = product.categ_id
    #         next_code, used_number = category._get_next_product_code()
    #         if next_code and used_number:
    #             product.with_context(_assigning_default_code=True).default_code = next_code
    #             category.write({'number': used_number + 1})
    #     return res