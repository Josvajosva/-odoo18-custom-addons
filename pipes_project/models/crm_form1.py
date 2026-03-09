from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
import json
import re
from odoo.exceptions import UserError, ValidationError
from datetime import date



class CrmLead(models.Model):
    _inherit = 'crm.lead'

    farmer_type = fields.Selection([
        ('70_percent', 'Micro Farmer (75% )'),
        ('100_percent', 'Small Scale Farmer (100%)'),
        ('other', 'Other')
    ], string='Farmer Type', default='70_percent')
    layout_image = fields.Binary(string="Layout Image")
    layout_image_filename = fields.Char(string="Layout File Name")
    gps_image = fields.Binary(string="Gps Image")
    gps_image_filename = fields.Char(string="Gps File Name")
    stage_name = fields.Char(related='stage_id.name', store=True)
    latitude = fields.Float(string='Latitude', digits=(16, 6))
    longitude = fields.Float(string='Longitude', digits=(16, 6))
    mi_type = fields.Selection([
        ('drip_irrigation', 'Drip Irrigation'),
        ('sprinkler_irrigation', 'Sprinkler Irrigation'),
        ('rain_gun', 'Rain Gun'),
        ('micro_sprinkler', 'Micro Sprinkler'),
        ('bubbler_irrigation', 'Bubbler Irrigation'),
        ('drip_to_sprinkler', 'Drip to Sprinkler System'),
    ], string='MI Type')

    mi_area = fields.Float(string='MI Area ', digits=(16, 3))
    total_area = fields.Float(string='Total Area ', digits=(16, 3))
    survey_number = fields.Char(string='Survey Number')
    sub_division_no = fields.Char(string='Sub-Division No')
    crop_name = fields.Char(string='Crop Name')
    spacing = fields.Float(string='Spacing', digits=(16, 2))
    pro_rata_spacing = fields.Float(string='Pro Rata Spacing', digits=(16, 2))
    sales_manager_area_id = fields.Many2one(
        'sales.manager',
        string="Area"
    )
    sales_manager_id = fields.Many2one(
        'res.partner',
        string="Sales Manager",
        domain="[('id', 'in', allowed_manager_ids)]"
    )

    allowed_manager_ids = fields.Many2many(
        'res.partner',
        compute="_compute_allowed_managers",
        string="Allowed Managers",
        store=False
    )

    application_id = fields.Char(
        string="Application Id",
        readonly=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('crm.lead.application')
    )

    father_name = fields.Char(string="Father Name")
    caste = fields.Selection([
        ('bc', 'BC'),
        ('mbc', 'MBC'),
        ('sc', 'SC'),
        ('st', 'ST'),
        ('oc', 'OC'),
        ('other', 'Other'),
    ], string="Caste")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string="Gender")

    district = fields.Char(string="District")
    block = fields.Char(string="Block")
    village = fields.Char(string="Village")
    department = fields.Char(string="Department")
    scheme = fields.Char(string="Scheme")
    applied_area = fields.Float(string="Applied Area ", digits=(16, 3))

    @api.model
    def create(self, vals):
        lead = super(CrmLead, self).create(vals)
        if not lead.partner_id:
            partner = self.env['res.partner'].create({
                'name': lead.partner_name or lead.contact_name or "Unknown Farmer",
                'village': lead.village,
                'district': lead.district,
                'gender': lead.gender,
                'caste': lead.caste,
                'father_name': lead.father_name,
                'department': lead.department,
                'application_id': lead.application_id,
            })
            lead.partner_id = partner.id

        return lead

    def write(self, vals):
        res = super(CrmLead, self).write(vals)
        for lead in self:
            if lead.partner_id:
                lead.partner_id.write({
                    'village': lead.village,
                    'district': lead.district,
                    'gender': lead.gender,
                    'caste': lead.caste,
                    'father_name': lead.father_name,
                    'department': lead.department,
                    'application_id': lead.application_id,
                })
        return res

    @api.model
    def create(self, vals):
        if not vals.get('application_id'):
            vals['application_id'] = self.env['ir.sequence'].next_by_code('crm.lead.application')
        return super(CrmLead, self).create(vals)

    @api.depends('sales_manager_area_id')
    def _compute_allowed_managers(self):
        for lead in self:
            if lead.sales_manager_area_id:
                lead.allowed_manager_ids = lead.sales_manager_area_id.manager_ids
            else:
                lead.allowed_manager_ids = False

class SalesManager(models.Model):
    _name = "sales.manager"
    _description = "Sales Manager"

    name = fields.Char(string="Area", required=True)
    manager_ids = fields.Many2many(
        'res.partner',
        'sales_manager_partner_rel',
        'sales_manager_id',
        'partner_id',
        string="Sales Managers",
    )



