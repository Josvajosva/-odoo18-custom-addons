# from odoo import models, fields, api
# import requests
# from odoo.exceptions import UserError
# import json
# import re
# from odoo.exceptions import UserError, ValidationError
# from datetime import date



# class CrmLead(models.Model):
#     _inherit = 'crm.lead'

#     farmer_type = fields.Selection([
#         ('70_percent', 'Micro Farmer (75% )'),
#         ('100_percent', 'Small Scale Farmer (100%)'),
#         ('other', 'Other')
#     ], string='Farmer Type', default='70_percent')
#     layout_image = fields.Binary(string="Layout Image")
#     layout_image_filename = fields.Char(string="Layout File Name")
#     gps_image = fields.Binary(string="Gps Image")
#     gps_image_filename = fields.Char(string="Gps File Name")
#     stage_name = fields.Char(related='stage_id.name', store=True)
#     latitude = fields.Float(string='Latitude', digits=(16, 6))
#     longitude = fields.Float(string='Longitude', digits=(16, 6))
#     mi_type = fields.Selection([
#         ('drip_irrigation', 'Drip Irrigation'),
#         ('sprinkler_irrigation', 'Sprinkler Irrigation'),
#         ('rain_gun', 'Rain Gun'),
#         ('micro_sprinkler', 'Micro Sprinkler'),
#         ('bubbler_irrigation', 'Bubbler Irrigation'),
#         ('drip_to_sprinkler', 'Drip to Sprinkler System'),
#     ], string='MI Type')

#     mi_area = fields.Float(string='MI Area ', digits=(16, 3))
#     total_area = fields.Float(string='Total Area ', digits=(16, 3))
#     survey_number = fields.Char(string='Survey Number')
#     sub_division_no = fields.Char(string='Sub-Division No')
#     crop_name = fields.Char(string='Crop Name')
#     spacing = fields.Float(string='Spacing', digits=(16, 2))
#     pro_rata_spacing = fields.Float(string='Pro Rata Spacing', digits=(16, 2))
#     sales_manager_area_id = fields.Many2one(
#         'sales.manager',
#         string="Area"
#     )
#     sales_manager_id = fields.Many2one(
#         'res.partner',
#         string="Sales Manager",
#         domain="[('id', 'in', allowed_manager_ids)]"
#     )

#     allowed_manager_ids = fields.Many2many(
#         'res.partner',
#         compute="_compute_allowed_managers",
#         string="Allowed Managers",
#         store=False
#     )

#     application_id = fields.Char(
#         string="Application Id",
#         readonly=True,
#         copy=False,
#         default=lambda self: self.env['ir.sequence'].next_by_code('crm.lead.application')
#     )

#     father_name = fields.Char(string="Father Name")
#     caste = fields.Selection([
#         ('bc', 'BC'),
#         ('mbc', 'MBC'),
#         ('sc', 'SC'),
#         ('st', 'ST'),
#         ('oc', 'OC'),
#         ('other', 'Other'),
#     ], string="Caste")
#     gender = fields.Selection([
#         ('male', 'Male'),
#         ('female', 'Female'),
#         ('other', 'Other'),
#     ], string="Gender")

#     district = fields.Char(string="District")
#     block = fields.Char(string="Block")
#     village = fields.Char(string="Village")
#     department = fields.Char(string="Department")
#     scheme = fields.Char(string="Scheme")
#     applied_area = fields.Float(string="Applied Area ", digits=(16, 3))
#     dealer_id = fields.Many2one(
#         'res.partner',
#         string="Dealer",
#         # domain="[('is_dealer', '=', True)]"
#     )

#     area_manager_id = fields.Many2one(
#         'area.manager',
#         string="Area Manager"
#     )

#     # @api.onchange('partner_id', 'dealer_id')
#     # def _onchange_partner_id_assign_dealer(self):
#     #     """ Auto-assign dealer when customer is selected """
#     #     if self.partner_id:
#     #         self.dealer_id = self.partner_id.city
#     #     else:
#     #         self.dealer_id = False

#     # @api.onchange('partner_id')
#     # def _onchange_partner_id_filter_dealer(self):
#     #     """ Filter dealer dropdown based on customer's city """
#     #     if self.partner_id and self.partner_id.city:
#     #         raise ValidationError(
#     #             "Customer does not have a city. Please set the city before selecting a dealer."
#     #         )
#     #         return {
#     #             'domain': {
#     #                 'dealer_id': [
#     #                     ('is_dealer', '=', True),
#     #                     ('city', '=', self.partner_id.city)
#     #                 ]
#     #             }
#     #         }
#     #     else:
#     #         raise ValidationError(
#     #             "Customer does not have a city. Please set the city before selecting a dealer."
#     #         )
#     #         return {
#     #             'domain': {
#     #                 'dealer_id': [('is_dealer', '=', True)]
#     #             }
#     #         }

#     # @api.onchange('partner_id')
#     # def _onchange_partner_id_filter_dealer(self):
#     #     domain = [('is_dealer', '=', True)]
#     #     if self.partner_id and self.partner_id.city:
#     #         domain.append(('city', '=', self.partner_id.city))
#     #     return {'domain': {'dealer_id': domain}}


#     @api.model
#     def create(self, vals):
#         lead = super(CrmLead, self).create(vals)
#         if not lead.partner_id:
#             partner = self.env['res.partner'].create({
#                 'name': lead.partner_name or lead.contact_name or "Unknown Farmer",
#                 'village': lead.village,
#                 'district': lead.district,
#                 'gender': lead.gender,
#                 'caste': lead.caste,
#                 'father_name': lead.father_name,
#                 'department': lead.department,
#                 'application_id': lead.application_id,
#             })
#             lead.partner_id = partner.id

#         return lead

#     def write(self, vals):
#         res = super(CrmLead, self).write(vals)
#         for lead in self:
#             if lead.partner_id:
#                 lead.partner_id.write({
#                     'village': lead.village,
#                     'district': lead.district,
#                     'gender': lead.gender,
#                     'caste': lead.caste,
#                     'father_name': lead.father_name,
#                     'department': lead.department,
#                     'application_id': lead.application_id,
#                 })
#         return res

#     @api.model
#     def create(self, vals):
#         if not vals.get('application_id'):
#             vals['application_id'] = self.env['ir.sequence'].next_by_code('crm.lead.application')
#         return super(CrmLead, self).create(vals)

#     @api.depends('sales_manager_area_id')
#     def _compute_allowed_managers(self):
#         for lead in self:
#             if lead.sales_manager_area_id:
#                 lead.allowed_manager_ids = lead.sales_manager_area_id.manager_ids
#             else:
#                 lead.allowed_manager_ids = False

# class SalesManager(models.Model):
#     _name = "sales.manager"
#     _description = "Sales Manager"

#     name = fields.Char(string="Area", required=True)
#     manager_ids = fields.Many2many(
#         'res.partner',
#         'sales_manager_partner_rel',
#         'sales_manager_id',
#         'partner_id',
#         string="Sales Managers",
#     )

# class AreaManager(models.Model):
#     _name = "area.manager"
#     _description = "Area Manager"

#     name = fields.Char(string="Name", required=True)
#     phone = fields.Char(string="Phone")
#     email = fields.Char(string="Email")

from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
import json
import re
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

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
    stage_name = fields.Char(related='stage_id.name', export_string_translation=False)
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
        required=True,
        copy=False,
    )
    work_order_no = fields.Char(
        string="Work Order No",
        copy=False,
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
    dealer_id = fields.Many2one(
        'res.partner',
        string="Dealer",
    )

    area_manager_id = fields.Many2one(
        'area.manager',
        string="Area Manager"
    )

    def action_new_quotation(self):
        action = super(CrmLead, self).action_new_quotation()
        if action and action.get('context'):
            action['context'].update({
                'default_dealer_id': self.dealer_id.id if self.dealer_id else False
            })
        return action

    @api.model
    def create(self, vals):
        for vl in vals:
            if not vl.get('application_id'):
                raise UserError(_("Application ID is required. Please provide an Application ID."))
        _logger.error("lead create: %s", vals)
        lead = super(CrmLead, self).create(vals)
        _logger.error("lead created: %s", lead)
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
            _logger.error("partner created: %s", lead.partner_id)
        return lead

    def write(self, vals):
        if 'application_id' in vals and not vals['application_id']:
            raise UserError(_("Application ID is required. Please provide an Application ID."))
            
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

    @api.constrains('application_id')
    def _check_application_id(self):
        """Ensure application_id is unique"""
        for lead in self:
            if lead.application_id:
                existing_lead = self.search([
                    ('application_id', '=', lead.application_id),
                    ('id', '!=', lead.id)
                ])
                if existing_lead:
                    raise ValidationError(_("Application ID must be unique. This Application ID already exists."))

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

class AreaManager(models.Model):
    _name = "area.manager"
    _description = "Area Manager"

    name = fields.Char(string="Name", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
