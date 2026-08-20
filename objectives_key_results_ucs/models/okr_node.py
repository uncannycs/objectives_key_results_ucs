from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class OkrNode(models.Model):
    _name = 'okr.node'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'OKR Node'
    _mail_post_access = 'read'

    _check_okr_success_points_threshold = models.Constraint(
        'CHECK(okr_success_points_threshold >= 0 AND okr_success_points_threshold <= 1)',
        'OKR success point threshold value must be in range from 0 to 1'
    )

    def _default_year(self):
        return str(fields.Date.today().year)

    def _default_quarter(self):
        return str((fields.Date.today().month - 1) // 3)

    def _default_mode(self):
        if self.env.user.has_group('objectives_key_results_ucs.group_okr_manager'):
            return 'company'
        elif self.env.user.has_group('objectives_key_results_ucs.group_okr_user'):
            return 'department'
        else:
            return 'employee'

    name = fields.Char(string="Title", tracking=True, required=True)
    year = fields.Char(default=_default_year, required=True,
                       compute='_compute_year', store=True, precompute=True,
                       recursive=True)
    quarter = fields.Selection([('0', 'Q1'), ('1', 'Q2'), ('2', 'Q3'), ('3', 'Q4')],
                               default=_default_quarter,
                               compute='_compute_quarter', store=True, precompute=True,
                               recursive=True)
    time_frame = fields.Char(string='Time Frame', compute='_compute_time_frame', search='_search_okr_time_frame')
    quarter_full_name = fields.Char(string='Quarter Full Name', compute='_compute_time_frame')
    description = fields.Text(string="Description")
    mode = fields.Selection([('company', 'Company'),
                             ('department', 'Department'),
                             ('employee', 'Employee')], string="Target", default=_default_mode, tracking=True)
    type = fields.Selection([('committed', 'Committed'),
                             ('aspirational', 'Aspirational')], string="Type", default='committed', tracking=True, required=True)
    state = fields.Selection([('draft', 'Draft'),
                             ('confirmed', 'Confirmed'),
                             ('cancelled', 'Cancelled')], default='draft', string="Status", tracking=True, readonly=True)
    result = fields.Selection([('new', 'New'),
                               ('inprogress', 'In Progress'),
                               ('successful', 'Successful'),
                               ('failed', 'Failed')], string="Result", tracking=True, compute='_compute_result', store=True,
                               help="Based on point, if point is greater than or equal to OKR success points threshold of top parent it will be Successful, and otherwise")
    company_id = fields.Many2one('res.company', string="Company",
                                 compute='_compute_company', store=True, precompute=True,
                                 tracking=True, recursive=True)
    department_id = fields.Many2one('hr.department', string="Department", compute='_compute_department', readonly=False, store=True, precompute=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", default=lambda self: self.env.user.employee_id)
    owner = fields.Char(string="Owner", readonly=True, tracking=True)
    user_id = fields.Many2one(
        'res.users',
        string="User",
        compute='_compute_owner_and_user_id',
        store=True,
        tracking=True,
        readonly=False,
        inverse='_inverse_user_id')
    parent_id = fields.Many2one('okr.node', string='Objective', tracking=True, ondelete='restrict',
                                domain="[('id','!=',id),'|','&',('mode','=','employee'),('department_id','=',department_id),'&',('mode','=','department'),('company_id','=',company_id)]",
                                help="Choose an Objective of which this is a key result.")
    child_ids = fields.One2many('okr.node', 'parent_id', string="Key Results")
    key_results_count = fields.Integer(string='Key Results Count', compute='_compute_key_results_count')
    recursive_child_ids = fields.Many2many('okr.node', 'recursive_objective', 'parent_id', 'child_id', string='Recursive Children', recursive=True,
                                           compute='_compute_recursive_child_ids', store=True)
    points = fields.Float(
        string="Points", tracking=True, aggregator='avg',
        compute='_compute_points', inverse='_inverse_points', readonly=False, store=True, recursive=True,
        help="The points indicates the level of completion of the objectives / results."
        " It must be evaluated on a scale of 0.0 - 1.0. If the current node has no result"
        " node (and is considered as a result of an objective), the point should be"
        " evaluated manually. If it has result nodes (and is considered as an objective"
        " of the results), the evaluation points are determined automatically by the weighted"
        " average points of the achieved successful results.\n"
        "Note: Results are considered successful when they reach the OKR Success Points"
        " Threshold which is 0.7 by default and can be configured in Settings."
        )
    progress = fields.Float(string='Progress', compute='_compute_progress', aggregator='avg')
    weight = fields.Float(string="Weight", tracking=True, aggregator='avg')
    okr_success_points_threshold = fields.Float(string="OKR success point threshold",
                                                compute='_compute_okr_success_points_threshold', store=True, precompute=True,
                                                readonly=False, recursive=True,
                                                help="Use this field to set value to compute whether the employee"
                                                " accomplish the OKR node successful or failed.")

    @api.constrains('mode')
    def _check_parent(self):
        for r in self:
            if r.mode in ('department', 'employee') and not r.parent_id:
                raise UserError(_("You must specify the Objective of this Key Result."))

    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def button_confirm(self):
        self.write({'state': 'confirmed'})

    def button_cancel(self):
        self.write({'state': 'cancelled'})

    @api.onchange('user_id')
    def _inverse_user_id(self):
        for r in self:
            r.owner = False
            if r.mode == 'department' and r.department_id:
                r.owner = r.department_id.manager_id.name
            elif r.mode == 'employee' and r.employee_id:
                r.owner = r.employee_id.name
            elif r.mode == 'company' and r.company_id:
                # find superior manager of this company
                superior_manager = r.env['hr.employee.public'].search([
                    ('company_id', '=', r.company_id.id),
                    ('user_id', '=', r.user_id.id)], limit=1)
                r.owner = superior_manager.name

    def _compute_key_results_count(self):
        total_key_result_data = self.env['okr.node']._read_group([('parent_id', 'in', self.ids)], ['parent_id'], ['__count'])
        mapped_data = {parent.id: count for parent, count in total_key_result_data}
        for r in self:
            r.key_results_count = mapped_data.get(r.id, 0)

    @api.depends('year', 'quarter')
    def _compute_time_frame(self):
        for r in self:
            if r.quarter:
                time_frame = "%s/%s" % (r.year, dict(r._fields['quarter']._description_selection(r.env)).get(r.quarter))
                r.quarter_full_name = time_frame
                r.time_frame = time_frame
            else:
                r.quarter_full_name = False
                r.time_frame = r.year

    @api.depends('points')
    def _compute_progress(self):
        for r in self:
            r.progress = r.points * 100

    @api.depends('mode', 'employee_id')
    def _compute_department(self):
        for r in self:
            if r.mode == 'company':
                r.department_id = False
            elif r.employee_id:
                r.department_id = r.employee_id.department_id
            else:
                r.department_id = self.env.user.employee_id.department_id

    @api.depends('mode', 'department_id')
    def _compute_company(self):
        for r in self:
            if r.mode in ('department', 'employee'):
                r.company_id = r.department_id.company_id or r.env.company
            else:
                r.company_id = r.env.company

    @api.depends('parent_id.year')
    def _compute_year(self):
        for r in self:
            if r.parent_id:
                r.year = r.parent_id.year
            else:
                r.year = r._default_year()

    @api.depends('parent_id.quarter')
    def _compute_quarter(self):
        for r in self:
            if r.parent_id:
                r.quarter = r.parent_id.quarter
            else:
                r.quarter = r._default_quarter()

    def _get_nested_children(self):
        child_ids = self.mapped('child_ids')
        for child_id in child_ids:
            child_ids += child_id._get_nested_children()
        return child_ids

    @api.depends('child_ids', 'child_ids.recursive_child_ids')
    def _compute_recursive_child_ids(self):
        for r in self:
            r.recursive_child_ids = [(6, 0, r._get_nested_children().ids)]

    @api.constrains('name')
    def _check_constrains_name(self):
        for r in self:
            if len(str(r.name)) > 100:
                raise ValidationError(_("The total number of characters for an objective cannot exceed 100 characters"))

    @api.depends('mode', 'company_id', 'department_id', 'employee_id')
    def _compute_owner_and_user_id(self):
        for r in self:
            r.user_id = False
            if r.mode == 'department' and r.department_id:
                r.user_id = r.department_id.manager_id.user_id
            elif r.mode == 'employee' and r.employee_id:
                r.user_id = r.employee_id.user_id
            elif r.mode == 'company' and r.company_id:
                superior_manager = r.env['hr.employee.public'].search([
                    ('company_id', '=', r.company_id.id),
                    ('parent_id', '=', False),
                    ('user_id', '!=', False)], limit=1)
                r.user_id = superior_manager.user_id

    @api.depends('parent_id.okr_success_points_threshold', 'company_id')
    def _compute_okr_success_points_threshold(self):
        for r in self:
            if not r.parent_id:
                r.okr_success_points_threshold = r.company_id.okr_success_points_threshold
            else:
                r.okr_success_points_threshold = r.parent_id.okr_success_points_threshold

    @api.depends('points', 'type', 'okr_success_points_threshold')
    def _compute_result(self):
        year_current = str(fields.Date.today().year)
        quarter_current = str((fields.Date.today().month - 1) // 3)
        for r in self:
            if (r.type == 'aspirational' and r.points >= r.okr_success_points_threshold) or r.points >= 1:
                r.result = 'successful'
            elif year_current > r.year or (year_current == r.year and r.quarter and quarter_current > r.quarter):
                r.result = 'failed'
            elif year_current == r.year and (not r.quarter or quarter_current == r.quarter):
                r.result = 'inprogress'
            else:
                r.result = 'new'

    def _inverse_points(self):
        pass

    @api.depends('child_ids', 'child_ids.points', 'child_ids.weight', 'child_ids.state')
    def _compute_points(self):
        for r in self:
            key_results = r.child_ids.filtered(lambda c: c.state == 'confirmed')
            if key_results:
                total_weight = sum(key_results.mapped('weight'))
                total_progress = 0
                if total_weight <= 0:
                    weight_rate = 100 / len(key_results)
                    for key_result in key_results:
                        total_progress += key_result.points * weight_rate
                else:
                    for key_result in key_results:
                        weight_rate = key_result.weight / total_weight * 100
                        total_progress += key_result.points * weight_rate
                r.points = min(1, max(0, total_progress / 100))

    @api.constrains('points')
    def _check_constrains_points(self):
        for r in self:
            if r.points < 0 or r.points > 1:
                raise ValidationError(_("Points need to be in range from 0 to 1"))

    @api.constrains('mode', 'department_id')
    def _check_department_owner(self):
        for r in self:
            r = r.sudo()
            if r.mode == 'department' and r.department_id:
                if not r.department_id.manager_id:
                    raise UserError(_("The department '%s' does not have a manager.") % r.department_id.display_name)
                if not r.department_id.manager_id.user_id:
                    raise UserError(_("The manager `%s` of the department `%s` has no user specified.")
                                    % (r.department_id.manager_id.display_name, r.department_id.display_name))

    @api.constrains('mode', 'employee_id')
    def _check_employee_owner(self):
        for r in self:
            r = r.sudo()
            if r.mode == 'employee' and r.employee_id and not r.employee_id.user_id:
                raise UserError(_("The employee `%s` has no user specified.") % r.employee_id.display_name)

    @api.constrains('mode', 'company_id')
    def _check_company_owner(self):
        for no_company_node in self.filtered(lambda r: r.mode == 'company' and not r.company_id):
            raise UserError(_("The objective or key result `%s` has no company specified") % no_company_node.display_name)
        for company in self.company_id:
            superior_manager = self.env['hr.employee.public'].search([
                ('company_id', '=', company.id),
                ('parent_id', '=', False),
                ('user_id', '!=', False)], limit=1)
            if not superior_manager:
                raise UserError(_("No highest-ranking manager for the company '%s' was found. \n\n"
                                  "On all the Objectives for the company, the owner must be assigned to one of the highest-ranking managers of the company.") % company.display_name)

    @api.constrains('year')
    def _check_constrains_year(self):
        for r in self:
            if not r.year.isnumeric():
                raise ValidationError(_("Year %s is invalid. It must be numerical.") % r.year)

    def _search_okr_time_frame(self, operator, value):
        if operator != 'ilike' and not isinstance(value, str):
            raise ValidationError(_("Not Implemented."))
        query = """
        SELECT id FROM okr_node where year||'/q'|| CASE
          WHEN quarter ='0' THEN 1
          WHEN quarter ='1' THEN 2
          WHEN quarter ='2' THEN 3
          WHEN quarter ='3' THEN 4
        END ILIKE %s"""
        return [('id', 'inselect', (query, [f'%{value}%']))]

    def _name_get(self):
        self.ensure_one()
        return '%s - %s' % (self.name, self.time_frame)

    @api.depends('name', 'time_frame')
    def _compute_display_name(self):
        for r in self:
            r.display_name = r._name_get()

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft(self):
        for r in self:
            if r.state != 'draft':
                raise UserError(_("You cannot delete an OKR record if its state is not Draft."))
