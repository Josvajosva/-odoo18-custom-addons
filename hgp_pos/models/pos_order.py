from odoo import api, fields, models, tools, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    compare_value = fields.Monetary(string="Compare List Price", store=True)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    compare_value = fields.Monetary(string="Compare Value", related='product_id.compare_value', store=True)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['compare_value']
        return params


class ResCompany(models.Model):
    _inherit = 'res.company'

    pos_image = fields.Image('Pos Image', max_width=1024, max_height=1024)