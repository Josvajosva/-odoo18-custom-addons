from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    village = fields.Char(string="Village")
    district = fields.Char(string="District")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string="Gender")
    caste = fields.Selection([
        ('bc', 'BC'),
        ('mbc', 'MBC'),
        ('sc', 'SC'),
        ('st', 'ST'),
        ('oc', 'OC'),
        ('other', 'Other'),
    ], string="Caste")
    father_name = fields.Char(string="Father Name")
    department = fields.Char(string="Department")
    application_id = fields.Char(string="Application ID")
    commission_per_catg = fields.Float(string="Commission % Category", default=20)
    region = fields.Char(string="Region")
    staff_name = fields.Many2one('hr.employee', string="Staff Name")


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    region = fields.Char(string="Region")




