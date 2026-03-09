from odoo import models, fields, api



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    is_auto_created = fields.Boolean(
        string='Auto Created',
        default=False,
        help='Indicates if this purchase order was automatically created from orderpoint by cron'
    )