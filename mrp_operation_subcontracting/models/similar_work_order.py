from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import timedelta


_logger = logging.getLogger(__name__)


class MRPRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    employee_ratio = fields.Float(
        string="Employee Capacity",
        help="Number of employees needed to complete the operation."
    )


class WorkCenter(models.Model):
    _inherit = "mrp.workcenter"

    employee_ids = fields.Many2many(
        'hr.employee',
        string="Allowed Employees",
        domain="[('company_id', '=', company_id)]",
        help="If left empty, all employees can log in to the workcenter."
    )
    similar_work_center = fields.Many2many(
        'mrp.workcenter',
        'workcenter_similar_rel',
        'workcenter_src_id',
        string='Similar Work Centers'
    )


class WorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    employee_ids = fields.Many2many(
        'hr.employee',
        string="Employees",
        compute="_compute_employees",
        store=True,
        readonly=False
    )
    mo_id = fields.Many2one(
        'mrp.production',
        string="Manufacturing Order",
        compute="_compute_mo_id",
        store=True
    )

    @api.depends('workorder_id.production_id')
    def _compute_mo_id(self):
        for record in self:
            record.mo_id = record.workorder_id.production_id if record.workorder_id else False

    @api.depends('workcenter_id')
    def _compute_employees(self):
        for workorder in self:
            workorder.employee_ids = workorder.workcenter_id.employee_ids


class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    def _get_similar_workorders(self):
        self.ensure_one()

        reverse_similar = self.env['mrp.workcenter'].search([
            ('similar_work_center', 'in', self.workcenter_id.id)
        ])

        all_similar_wcs = self.workcenter_id.similar_work_center | reverse_similar

        return self.production_id.workorder_ids.filtered(
            lambda w: w.workcenter_id in all_similar_wcs and w.state not in ['done', 'cancel']
        )

    def _apply_action_with_guard(self, action_name, visited=None):
        if visited is None:
            visited = set()

        for wo in self:
            if wo.id in visited:
                continue

            visited.add(wo.id)

            getattr(super(MrpWorkOrder, wo), action_name)()

            # if action_name == 'button_start':
            #     super(MrpWorkOrder, wo).button_start()
            # elif action_name == 'button_pending':
            #     super(MrpWorkOrder, wo).button_pending()
            # elif action_name == 'button_finish':
            #     super(MrpWorkOrder, wo).button_finish()

            similar_wos = wo._get_similar_workorders()
            similar_wos._apply_action_with_guard(action_name, visited)


    def button_start(self):
        """Start the main and similar work orders, and properly track productivity."""
        date_start = fields.Datetime.now()
        date_end = date_start + timedelta(hours=1)  # Adjust expected duration as needed

        for wo in self:
            print(f"\n=== Starting Main Work Order: {wo.id} - {wo.workcenter_id.name} ===")

            # Start main work order
            if wo.state != 'progress':
                wo.write({
                    'state': 'progress',
                    'date_start': date_start,
                    'date_finished': date_end,
                })
                print(f"Set main Work Order {wo.id} to 'progress'.")

                # Create calendar leave if not already present
                if not wo.leave_id:
                    leave = self.env['resource.calendar.leaves'].create({
                        'name': wo.display_name,
                        'calendar_id': wo.workcenter_id.resource_calendar_id.id,
                        'date_from': date_start,
                        'date_to': date_end,
                        'resource_id': wo.workcenter_id.resource_id.id,
                        'time_type': 'other'
                    })
                    wo.leave_id = leave.id

            # Start timer for main WO if not already running
            if not wo.time_ids.filtered(lambda t: not t.date_end):
                self.env['mrp.workcenter.productivity'].create(
                    wo._prepare_timeline_vals(wo.duration_expected or 0.0, date_start)
                )
                print(f"Started timer for main Work Order {wo.id}")

            # Get similar work centers (forward + reverse)
            reverse_similar = self.env['mrp.workcenter'].search([
                ('similar_work_center', 'in', wo.workcenter_id.id)
            ])
            all_similar_wcs = wo.workcenter_id.similar_work_center | reverse_similar
            print(f"Similar Work Centers found: {[wc.name for wc in all_similar_wcs]}")

            # Process similar work orders in the same MO
            for swc in all_similar_wcs:
                similar_wos = self.env['mrp.workorder'].search([
                    ('production_id', '=', wo.production_id.id),
                    ('workcenter_id', '=', swc.id),
                    ('state', 'not in', ['done', 'cancel'])
                ])
                for swo in similar_wos:
                    if swo.id == wo.id:
                        continue

                    if swo.state != 'progress':
                        swo.write({
                            'state': 'progress',
                            'date_start': date_start,
                            'date_finished': date_end,
                        })
                        print(f"Set Similar Work Order {swo.id} ({swo.workcenter_id.name}) to 'progress'.")

                        if not swo.leave_id:
                            leave = self.env['resource.calendar.leaves'].create({
                                'name': swo.display_name,
                                'calendar_id': swo.workcenter_id.resource_calendar_id.id,
                                'date_from': date_start,
                                'date_to': date_end,
                                'resource_id': swo.workcenter_id.resource_id.id,
                                'time_type': 'other'
                            })
                            swo.leave_id = leave.id

                    if not swo.time_ids.filtered(lambda t: not t.date_end):
                        self.env['mrp.workcenter.productivity'].create(
                            swo._prepare_timeline_vals(swo.duration_expected or 0.0, date_start)
                        )
                        print(f"Started timer for Similar Work Order {swo.id}")

        return True


    def button_pending(self):
        """Pause the main and similar work orders and stop timers."""
        date_now = fields.Datetime.now()

        for wo in self:
            print(f"\n=== Pausing Main Work Order: {wo.id} - {wo.workcenter_id.name} ===")
            if wo.state == 'progress':
                wo.write({'state': 'pending'})
                print(f"Set main Work Order {wo.id} to 'pending'.")

                last_timer = wo.time_ids.filtered(lambda t: not t.date_end)
                if last_timer:
                    last_timer.date_end = date_now
                    print(f"Stopped timer for Work Order {wo.id}")

            # Find all similar work centers (direct + reverse)
            reverse_similar = self.env['mrp.workcenter'].search([
                ('similar_work_center', 'in', wo.workcenter_id.id)
            ])
            all_similar_wcs = wo.workcenter_id.similar_work_center | reverse_similar

            for swc in all_similar_wcs:
                similar_wos = self.env['mrp.workorder'].search([
                    ('production_id', '=', wo.production_id.id),
                    ('workcenter_id', '=', swc.id),
                    ('state', '=', 'progress')
                ])
                for swo in similar_wos:
                    swo.write({'state': 'pending'})
                    print(f"Set Similar Work Order {swo.id} ({swo.workcenter_id.name}) to 'pending'.")

                    last_timer = swo.time_ids.filtered(lambda t: not t.date_end)
                    if last_timer:
                        last_timer.date_end = date_now
                        print(f"Stopped timer for Similar Work Order {swo.id}")

        return True


    def button_finish(self):
        """Finish the main and similar work orders and stop any running timers."""
        date_now = fields.Datetime.now()

        for wo in self:
            print(f"\n=== Finishing Main Work Order: {wo.id} - {wo.workcenter_id.name} ===")
            if wo.state in ['progress', 'pending']:
                wo.write({'state': 'done', 'date_finished': date_now})
                print(f"Set main Work Order {wo.id} to 'done'.")

                last_timer = wo.time_ids.filtered(lambda t: not t.date_end)
                if last_timer:
                    last_timer.date_end = date_now
                    print(f"Stopped timer for Work Order {wo.id}")

            # Find all similar work centers (direct + reverse)
            reverse_similar = self.env['mrp.workcenter'].search([
                ('similar_work_center', 'in', wo.workcenter_id.id)
            ])
            all_similar_wcs = wo.workcenter_id.similar_work_center | reverse_similar

            for swc in all_similar_wcs:
                similar_wos = self.env['mrp.workorder'].search([
                    ('production_id', '=', wo.production_id.id),
                    ('workcenter_id', '=', swc.id),
                    ('state', 'in', ['progress', 'pending'])
                ])
                for swo in similar_wos:
                    swo.write({'state': 'done', 'date_finished': date_now})
                    print(f"Set Similar Work Order {swo.id} ({swo.workcenter_id.name}) to 'done'.")

                    last_timer = swo.time_ids.filtered(lambda t: not t.date_end)
                    if last_timer:
                        last_timer.date_end = date_now
                        print(f"Stopped timer for Similar Work Order {swo.id}")

        return True

