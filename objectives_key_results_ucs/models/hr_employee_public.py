from odoo import fields, models

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    okr_node_ids = fields.One2many('okr.node', 'employee_id', string='OKR', readonly=True)
    okr_nodes_count = fields.Integer(string='OKR Count', compute='_compute_okr_nodes_count', compute_sudo=True)

    def _compute_okr_nodes_count(self):
        okr_data = self.env['okr.node']._read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        mapped_data = {employee.id: count for employee, count in okr_data}
        for r in self:
            r.okr_nodes_count = mapped_data.get(r.id, 0)

    def action_view_okr(self):
        action = self.env['ir.actions.act_window']._for_xml_id('objectives_key_results_ucs.okr_node_action')
        action['context'] = {}
        action['domain'] = "[('employee_id','in',%s)]" % self.ids
        return action
