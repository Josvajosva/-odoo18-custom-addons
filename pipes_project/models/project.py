from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = "project.task"

    # allocation_days = fields.Char(string="Allocation Days")