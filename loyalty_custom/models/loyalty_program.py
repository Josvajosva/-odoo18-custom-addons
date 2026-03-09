from odoo import api, fields, models


class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    use_floor_points = fields.Boolean(
        string='Floor-Based Points',
        default=False,
        help='When enabled, points are calculated based on complete multiples of the '
             'minimum purchase amount only. For example, if the rule is "5 points per 100 RS", '
             'then 165 RS = 5 points, 200 RS = 10 points, 350 RS = 15 points.',
    )
    double_points_days = fields.Integer(
        string='Double Points Within (Days)',
        default=0,
        help='If set to a value greater than 0, customers who make a repeat purchase '
             'within this many days will earn double points. Set to 0 to disable.',
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += ['use_floor_points', 'double_points_days']
        return fields