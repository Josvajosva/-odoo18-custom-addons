from odoo import fields, models

class Company(models.Model):
    _inherit = 'res.company'

    mi_id = fields.Char(string="MI ID")