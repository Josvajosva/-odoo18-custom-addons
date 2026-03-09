# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _description = "Purchase Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    @api.model
    def _company_get(self):
        return self.env["res.company"].browse(self.env.company.id)

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    @api.model
    def _get_default_name(self):
        return self.env["ir.sequence"].next_by_code("purchase.request")

    @api.model
    def _default_picking_type(self):
        type_obj = self.env["stock.picking.type"]
        company_id = self.env.context.get("company_id") or self.env.company.id
        types = type_obj.search(
            [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company_id)]
        )
        if not types:
            types = type_obj.search(
                [("code", "=", "incoming"), ("warehouse_id", "=", False)]
            )
        return types[:1]

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ("to_approve", "approved", "rejected", "done"):
                rec.is_editable = False
            else:
                rec.is_editable = True

    name = fields.Char(
        string="Request Reference",
        required=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    is_name_editable = fields.Boolean(
        default=lambda self: self.env.user.has_group("base.group_no_one"),
    )
    origin = fields.Char(string="Source Document")
    date_start = fields.Date(
        string="Creation date",
        help="Date when the user initiated the request.",
        default=fields.Date.context_today,
        tracking=True,
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        required=True,
        copy=False,
        tracking=True,
        default=_get_default_requested_by,
        index=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        tracking=True,
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref("purchase_request.group_bom_engineer").id,
            )
        ],
        index=True,
    )
    description = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=False,
        default=_company_get,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="purchase.request.line",
        inverse_name="request_id",
        string="Products to Purchase",
        readonly=False,
        copy=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="line_ids.product_id",
        string="Product",
        readonly=True,
    )
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)
    to_approve_allowed = fields.Boolean(compute="_compute_to_approve_allowed")
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Type",
        required=True,
        default=_default_picking_type,
    )
    group_id = fields.Many2one(
        comodel_name="procurement.group",
        string="Procurement Group",
        copy=False,
        index=True,
    )
    line_count = fields.Integer(
        string="Purchase Request Line count",
        compute="_compute_line_count",
        readonly=True,
    )
    move_count = fields.Integer(
        string="Stock Move count", compute="_compute_move_count", readonly=True
    )
    purchase_count = fields.Integer(
        string="Purchases count", compute="_compute_purchase_count", readonly=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    estimated_cost = fields.Monetary(
        compute="_compute_estimated_cost",
        string="Total Estimated Cost",
        store=True,
    )
    # ref_bom_id = fields.One2many(
    #     comodel_name="purchase.request.bom",
    #     inverse_name="purchase_request_id",
    #     string="Reference BOMs",
    #     copy=False,
    # )
    ref_bom_ids = fields.One2many(
        comodel_name="purchase.request.bom",
        inverse_name="purchase_request_id",
        string="BoM References",
        copy=False,
    )
    po_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Generated Purchase Order",
        readonly=True,
    )
    po_supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Preferred supplier",
        store=True,
    )
    po_created = fields.Boolean(string='PO Created', default=False)


    @api.depends("line_ids", "line_ids.estimated_cost")
    def _compute_estimated_cost(self):
        for rec in self:
            rec.estimated_cost = sum(rec.line_ids.mapped("estimated_cost"))

    @api.depends("line_ids")
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.mapped("line_ids.purchase_lines.order_id"))

    def action_view_purchase_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        lines = self.mapped("line_ids.purchase_lines.order_id")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("purchase.purchase_order_form").id, "form")
            ]
            action["res_id"] = lines.id
        return action

    @api.depends("line_ids")
    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(
                rec.mapped("line_ids.purchase_request_allocation_ids.stock_move_id")
            )

    def action_view_stock_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_all"
        )
        # remove default filters
        action["context"] = {}
        lines = self.mapped(
            "line_ids.purchase_request_allocation_ids.stock_move_id.picking_id"
        )
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = lines.id
        return action

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.mapped("line_ids"))

    def action_view_purchase_request_line(self):
        action = (
            self.env.ref("purchase_request.purchase_request_line_form_action")
            .sudo()
            .read()[0]
        )
        lines = self.mapped("line_ids")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("purchase_request.purchase_request_line_form").id, "form")
            ]
            action["res_id"] = lines.ids[0]
        return action

    # @api.depends("state", "line_ids.product_qty", "line_ids.cancelled")
    # def _compute_to_approve_allowed(self):
    #     for rec in self:
    #         rec.to_approve_allowed = rec.state == "draft" and any(
    #             not line.cancelled and line.product_qty for line in rec.line_ids
    #         )

    @api.depends("state", "line_ids.needed_qty", "line_ids.cancelled")
    def _compute_to_approve_allowed(self):
        for rec in self:
            rec.to_approve_allowed = rec.state == "draft" and any(
                not line.cancelled and line.needed_qty for line in rec.line_ids
            )

    def copy(self, default=None):
        default = dict(default or {})
        self.ensure_one()
        default.update({"state": "draft", "name": self._get_default_name()})
        return super().copy(default)

    @api.model
    def _get_partner_id(self, request):
        user_id = request.assigned_to or self.env.user
        return user_id.partner_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self._get_default_name()
        requests = super().create(vals_list)
        for vals, request in zip(vals_list, requests, strict=True):
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return requests

    def write(self, vals):
        res = super().write(vals)
        for request in self:
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return res

    def _can_be_deleted(self):
        self.ensure_one()
        return self.state == "draft"

    def unlink(self):
        for request in self:
            if not request._can_be_deleted():
                raise UserError(
                    _("You cannot delete a purchase request which is not draft.")
                )
        return super().unlink()

    def button_draft(self):
        self.mapped("line_ids").do_uncancel()
        return self.write({"state": "draft"})

    def button_to_approve(self):
        self.to_approve_allowed_check()
        return self.write({"state": "to_approve"})

    def button_approved(self):
        return self.write({"state": "approved"})

    def button_rejected(self):
        self.mapped("line_ids").do_cancel()
        return self.write({"state": "rejected"})

    def button_done(self):
        return self.write({"state": "done"})

    def check_auto_reject(self):
        """When all lines are cancelled the purchase request should be
        auto-rejected."""
        for pr in self:
            if not pr.line_ids.filtered(lambda line: line.cancelled is False):
                pr.write({"state": "rejected"})

    def to_approve_allowed_check(self):
        for rec in self:
            if not rec.to_approve_allowed:
                raise UserError(
                    _(
                        "You can't request an approval for a purchase request "
                        "which is empty. (%s)"
                    )
                    % rec.name
                )

    def action_generate_vendor(self):
        """Assign vendors to PR lines based on product and restrict vendor selection."""
        for request in self:
            for line in request.line_ids:
                product = line.product_id

                if product and product.seller_ids:
                    vendor_ids = product.seller_ids.mapped("partner_id.id")

                    if vendor_ids:
                        # Assign first vendor
                        line.ven_id = vendor_ids[0]

                        # Store vendor_ids on a computed field for use in domain
                        line.ven_domain_ids = [(6, 0, vendor_ids)]

                    else:
                        line.ven_id = False
                else:
                    line.ven_id = False

        return {'type': 'ir.actions.act_window_close'}

    # def action_create_po(self):
    #     """Creates and confirms a Purchase Order from the Purchase Request."""
    #     purchase_order_model = self.env["purchase.order"]
    #     purchase_order_line_model = self.env["purchase.order.line"]
    #
    #     for request in self:
    #         if not request.line_ids:
    #             raise UserError(_("There are no products in this purchase request."))
    #
    #         if request.po_id:
    #             raise UserError(_("A Purchase Order has already been created for this request."))
    #
    #         # Determine Supplier
    #         po_supplier_id = request.po_supplier_id
    #         if not po_supplier_id:
    #             raise UserError(_("No supplier is set for this purchase request."))
    #
    #         # Create the Purchase Order
    #         po_values = {
    #             "partner_id": po_supplier_id.id,
    #             "origin": request.name,
    #             "company_id": request.company_id.id,
    #             "currency_id": request.currency_id.id,
    #         }
    #         po = purchase_order_model.create(po_values)
    #
    #         # Create Purchase Order Lines
    #         for line in request.line_ids:
    #             if not line.product_id:
    #                 continue
    #
    #             po_line_values = {
    #                 "order_id": po.id,
    #                 "product_id": line.product_id.id,
    #                 "name": line.name or line.product_id.name,
    #                 # "product_qty": line.product_qty,
    #                 "product_qty": line.needed_qty,
    #                 "product_uom": line.product_uom_id.id,
    #                 "price_unit": line.estimated_cost,
    #                 "date_planned": line.date_required,
    #             }
    #             purchase_order_line_model.create(po_line_values)
    #
    #         # Link PO to Purchase Request
    #         request.po_id = po.id
    #
    #         #Confirm the Purchase Order immediately after creation
    #         po.button_confirm()
    #
    #     return {
    #         "name": _("Purchase Order"),
    #         "type": "ir.actions.act_window",
    #         "res_model": "purchase.order",
    #         "view_mode": "form",
    #         "res_id": po.id,
    #         "target": "current",
    #     }

    # def action_create_po(self):
    #     """Creates and confirms a Purchase Order from the Purchase Request."""
    #     purchase_order_model = self.env["purchase.order"]
    #     purchase_order_line_model = self.env["purchase.order.line"]
    #
    #     for request in self:
    #         if not request.line_ids:
    #             raise UserError(_("There are no products in this purchase request."))
    #
    #         if request.po_id:
    #             raise UserError(_("A Purchase Order has already been created for this request."))
    #
    #         # Determine Supplier
    #         po_supplier_id = request.po_supplier_id
    #         if not po_supplier_id:
    #             raise UserError(_("No supplier is set for this purchase request."))
    #
    #         # Create the Purchase Order
    #         po_values = {
    #             "partner_id": po_supplier_id.id,
    #             "origin": request.name,
    #             "company_id": request.company_id.id,
    #             "currency_id": request.currency_id.id,
    #         }
    #         po = purchase_order_model.create(po_values)
    #
    #         # Create Purchase Order Lines and Link to PR Lines
    #         for line in request.line_ids:
    #             if not line.product_id:
    #                 continue
    #
    #             po_line_values = {
    #                 "order_id": po.id,
    #                 "product_id": line.product_id.id,
    #                 "name": line.name or line.product_id.name,
    #                 "product_qty": line.needed_qty,
    #                 "price_unit": line.product_id.standard_price or 0.0,
    #                 "product_uom": line.product_uom_id.id,
    #                 "date_planned": line.date_required,
    #                 "purchase_request_lines": [(4, line.id)],  # Link PR Line to PO Line
    #             }
    #             po_line = purchase_order_line_model.create(po_line_values)
    #
    #             # Link PR Line to Purchase Order Line
    #             line.write({"purchase_lines": [(4, po_line.id)]})
    #
    #         # Link PO to Purchase Request
    #         request.po_id = po.id
    #
    #         # Confirm the Purchase Order immediately after creation
    #         po.button_confirm()
    #
    #     return {
    #         "name": _("Purchase Order"),
    #         "type": "ir.actions.act_window",
    #         "res_model": "purchase.order",
    #         "view_mode": "form",
    #         "res_id": po.id,
    #         "target": "current",
    #     }

    # def action_create_po(self):
    #     print("43333333333333333335")
    #     purchase_order_obj = self.env['purchase.order']
    #     purchase_order_line_obj = self.env['purchase.order.line']
    #
    #     # Group PR lines by preferred vendor
    #     pr_lines = self.env['purchase.request.line'].browse(self.env.context.get('active_ids', []))
    #     vendor_groups = {}
    #
    #     # Debug: Check if there are any lines and if ven_id is set
    #     for line in pr_lines:
    #         if not line.ven_id:
    #             raise UserError(_('Please set a Preferred Vendor on all lines before proceeding.'))
    #         vendor_groups.setdefault(line.ven_id, []).append(line)
    #
    #     created_pos = []
    #     for vendor, lines in vendor_groups.items():
    #         # Prepare values for the purchase order creation
    #         po_vals = {
    #             'partner_id': vendor.id,
    #             'order_line': [],
    #             'origin': ', '.join(set(line.origin for line in lines if line.origin)),
    #             'company_id': lines[0].company_id.id,  # Ensure company is correctly set
    #             'currency_id': lines[0].company_id.currency_id.id,  # Ensure currency is correctly set
    #         }
    #
    #         # Debug: Check the PO values before creation
    #         print(f"Creating Purchase Order with values: {po_vals}")
    #
    #         # Create Purchase Order
    #         po = purchase_order_obj.create(po_vals)
    #
    #         if po:
    #             created_pos.append(po.id)
    #             print(f"Purchase Order Created: {po.id}")
    #         else:
    #             raise UserError(_('Purchase Order creation failed.'))
    #
    #         for line in lines:
    #             # Prepare values for the purchase order line creation
    #             po_line_vals = {
    #                 'order_id': po.id,
    #                 'product_id': line.product_id.id,
    #                 'name': line.name or line.product_id.name,
    #                 'product_qty': line.purchased_qty,
    #                 'product_uom': line.product_uom_id.id,
    #                 'price_unit': line.product_id.standard_price,
    #                 'date_planned': line.date_required,
    #             }
    #
    #             # Debug: Check PO Line values before creation
    #             print(f"Creating Purchase Order Line with values: {po_line_vals}")
    #
    #             # Create Purchase Order Line
    #             po_line = purchase_order_line_obj.create(po_line_vals)
    #             line.purchase_lines = [(4, po_line.id)]  # Link PR Line to PO Line
    #
    #     # Check if POs were created and return appropriate action
    #     if len(created_pos) == 1:
    #         action = {
    #             'type': 'ir.actions.act_window',
    #             'name': _('Purchase Order'),
    #             'res_model': 'purchase.order',
    #             'view_mode': 'form',
    #             'res_id': created_pos[0],
    #             'target': 'current',
    #         }
    #     else:
    #         action = {
    #             'type': 'ir.actions.act_window',
    #             'name': _('Purchase Orders'),
    #             'res_model': 'purchase.order',
    #             'view_mode': 'tree,form',
    #             'domain': [('id', 'in', created_pos)],
    #             'target': 'current',
    #         }
    #
    #     return action

    # def create_purchase_orders(self):
    #     """ Create Purchase Orders (RFQ) based on the preferred vendor of each line, creating only one PO per vendor. """
    #     for request in self:
    #         vendor_groups = {}
    #         for line in request.line_ids:
    #             if not line.ven_id:
    #                 raise UserError(_("No preferred supplier found for product: %s") % line.product_id.name)
    #
    #             if line.ven_id not in vendor_groups:
    #                 vendor_groups[line.ven_id] = []
    #
    #             vendor_groups[line.ven_id].append(line)
    #
    #         for vendor, lines in vendor_groups.items():
    #             purchase_order = self.env['purchase.order'].create({
    #                 'partner_id': vendor.id,
    #                 'company_id': request.company_id.id,
    #                 'date_order': fields.Date.today(),
    #                 'state': 'draft',
    #             })
    #
    #             for line in lines:
    #                 # Use estimated cost as price
    #                 price_unit = line.estimated_cost
    #
    #                 # Create PO line
    #                 po_line = self.env['purchase.order.line'].create({
    #                     'order_id': purchase_order.id,
    #                     'product_id': line.product_id.id,
    #                     'product_uom': line.product_uom_id.id,
    #                     'product_qty': line.needed_qty,
    #                     'price_unit': price_unit,
    #                     'name': line.name,
    #                 })
    #
    #                 # Update PR Line purchase state
    #                 line.purchase_state = 'rfq_created'  # Update to your field value
    #
    #         request.write({'state': 'to_approve'})
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'reload',
    #     }

    def action_create_po(self):
        """Creates and confirms multiple Purchase Orders grouped by vendor from the Purchase Request."""
        purchase_order_model = self.env["purchase.order"]
        purchase_order_line_model = self.env["purchase.order.line"]

        for request in self:
            if not request.line_ids:
                raise UserError(_("There are no products in this purchase request."))

            # Group lines by vendor
            vendor_line_map = {}
            for line in request.line_ids:
                if not line.ven_id:
                    raise UserError(_("No supplier is set for line %s.") % line.product_id.display_name)

                vendor = line.ven_id
                vendor_line_map.setdefault(vendor, []).append(line)

            po_map = {}  # Track created POs

            for vendor, lines in vendor_line_map.items():
                po_values = {
                    "partner_id": vendor.id,
                    "origin": request.name,
                    "company_id": request.company_id.id,
                    "currency_id": request.currency_id.id,
                    "pur_request_id": request.id,
                    "so_reference":request.origin,
                }
                po = purchase_order_model.create(po_values)

                for line in lines:
                    if not line.product_id:
                        continue

                    po_line_values = {
                        "order_id": po.id,
                        "product_id": line.product_id.id,
                        "name": line.name or '',
                        "product_qty": line.purchased_qty,
                        "price_unit": line.product_id.standard_price or 0.0,
                        "product_uom": line.product_uom_id.id,
                        "date_planned": line.date_required,
                        "purchase_request_lines": [(4, line.id)],
                    }
                    po_line = purchase_order_line_model.create(po_line_values)

                    # Link PR Line to PO Line
                    line.write({"purchase_lines": [(4, po_line.id)]})

                # Optional: store one of the created POs on the request
                if not request.po_id:
                    request.po_id = po.id
                po_map[po.id] = po
                request.po_created = True
                # # Confirm PO
                # po.button_confirm()

        if len(po_map) == 1:
            return {
                "name": _("Purchase Order"),
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "view_mode": "form",
                "res_id": list(po_map.keys())[0],
                "target": "current",
            }
        else:
            return {
                "name": _("Purchase Orders"),
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "view_mode": "tree,form",
                "domain": [("id", "in", list(po_map.keys()))],
                "context": dict(self.env.context),
            }


# class PurchaseRequestBom(models.Model):
#     _name = "purchase.request.bom"
#     _description = "Link between Purchase Request and BOM"

#     purchase_request_id = fields.Many2one(
#         comodel_name="purchase.request", 
#         string="Purchase Request", 
#         required=True
#     )
#     bom_id = fields.Many2one(
#         comodel_name="mrp.bom", 
#         string="BoM", 
#         required=True
#     )

class PurchaseRequestBom(models.Model):
    _name = "purchase.request.bom"
    _description = "BoM References for Purchase Request"

    purchase_request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        required=True,
        ondelete="cascade"
    )
    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Bill of Materials",
        required=True,
        ondelete="cascade"
    )
