from odoo import models, fields

class Company(models.Model):
    _inherit = 'res.company'

    _sql_constraints = [
        (
            'okr_success_points_threshold',
            'CHECK(okr_success_points_threshold >= 0 AND okr_success_points_threshold <= 1)',
            'OKR success point threshold value must be in range from 0 to 1'
        )
    ]

    okr_success_points_threshold = fields.Float(string="OKR Success Points Threshold", default=0.7)
