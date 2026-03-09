from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    hide_out_of_stock_products = fields.Boolean(
        string='Hide Out-of-Stock Products',
        default=False,
        help="Don't show products with zero on-hand quantity in POS"
    )