from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    okr_success_points_threshold = fields.Float(
        string="OKR Success Points Threshold",
        help="Setting this field to set standard value for OKR node, \n"
             "help evaluate whether the employee accomplish successful or failed based on points value.",
        related='company_id.okr_success_points_threshold',
        readonly=False
    )
