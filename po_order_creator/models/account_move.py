from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_intercompany_so_invoice = fields.Boolean(
        compute='_compute_intercompany_so_invoice',
        store=True,
    )
    intercompany_so_name = fields.Char(
        compute='_compute_intercompany_so_invoice',
        store=True,
    )
    intercompany_so_qr_image = fields.Boolean()

    @api.depends('move_type', 'line_ids.sale_line_ids.order_id')
    def _compute_intercompany_so_invoice(self):
        for move in self:
            so_names = ''
            is_intercompany = False
            if move.move_type == 'out_invoice':
                sale_orders = move.line_ids.sale_line_ids.order_id
                intercompany_sos = sale_orders.filtered(
                    lambda so: so.auto_purchase_order_id
                )
                if intercompany_sos:
                    is_intercompany = True
                    so_names = ', '.join(intercompany_sos.mapped('name'))
            move.is_intercompany_so_invoice = is_intercompany
            move.intercompany_so_name = so_names

    def _get_intercompany_so_ids(self):
        """Return comma-separated SO IDs. Kept for compatibility."""
        self.ensure_one()
        sale_orders = self.line_ids.sale_line_ids.order_id
        intercompany_sos = sale_orders.filtered(lambda so: so.auto_purchase_order_id)
        return ','.join(str(so.id) for so in intercompany_sos)

    def _get_intercompany_po_ids(self):
        """Return comma-separated PO IDs for QR code. Called from report template."""
        self.ensure_one()
        sale_orders = self.line_ids.sale_line_ids.order_id
        intercompany_sos = sale_orders.filtered(lambda so: so.auto_purchase_order_id)
        po_ids = intercompany_sos.mapped('auto_purchase_order_id')
        return ','.join(str(po.id) for po in po_ids)

    def action_post(self):
        """Override to update product vendor prices when vendor bill is confirmed"""
        res = super().action_post()
        for move in self:
            if move.move_type == 'in_invoice' and move.state == 'posted':
                self._update_product_vendor_prices(move)
        return res

    def _update_product_vendor_prices(self, move):
        """Update product vendor prices based on confirmed purchase order amounts"""
        for line in move.invoice_line_ids:
            if not line.purchase_line_id or not line.product_id:
                continue

            purchase_line = line.purchase_line_id
            product = line.product_id
            partner_id = purchase_line.order_id.partner_id
            vendor = partner_id if not partner_id.parent_id else partner_id.parent_id

            if not vendor or not product:
                continue

            po_price = purchase_line.price_unit

            supplier_info = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('partner_id', '=', vendor.id),
                # ('company_id', '=', move.company_id.id),
            ], limit=1)

            if supplier_info:
                supplier_info.write({
                    'price': po_price,
                    'currency_id': purchase_line.currency_id.id,
                })

            company_partner = (move.company_id.parent_id or move.company_id).partner_id

            is_inter_company = company_partner in (
                    vendor | vendor.parent_id
            )

            if is_inter_company:
                product.sudo().with_context(disable_auto_svl=True).write({
                    'standard_price': po_price
                })


    def _get_invoice_quantities_by_product(self, invoice):
        """Return dict product_id (id) -> quantity in product UoM (from invoice lines)."""
        product_lines = invoice.invoice_line_ids.filtered(
            lambda l: l.display_type == "product" and l.product_id
        )
        product_lines.mapped('product_id.uom_id')
        product_lines.mapped('product_uom_id')
        qtys = {}
        for line in product_lines:
            pid = line.product_id.id
            if line.product_uom_id == line.product_id.uom_id:
                qty = line.quantity
            else:
                qty = line.product_uom_id._compute_quantity(
                    line.quantity, line.product_id.uom_id, round=False
                )
            qtys[pid] = qtys.get(pid, 0) + qty
        return qtys

    @api.model
    def action_confirm(self, scan_input):
        def _response(level, message, action=None):
            res = {"ok": True, "level": level, "message": message}
            if isinstance(action, dict) and action.get("type"):
                res["action"] = action
            return res

        try:
            po_id_str, invoice_id_str = (p.strip() for p in str(scan_input or "").strip().split("|", 1))
            po_id = int(po_id_str)
            invoice_id = int(invoice_id_str)
        except Exception as e:
            raise ValidationError(_("Please scan a valid QR code (format: PO_id|Invoice_id).")) from e

        purchase_order = self.env["purchase.order"].sudo().browse(po_id)
        if not purchase_order.exists():
            raise UserError(_("Purchase Order %s not found.") % po_id_str)

        invoice = self.env["account.move"].sudo().browse(invoice_id)
        if not invoice.exists():
            raise UserError(_("Invoice %s not found.") % invoice_id_str)
        if invoice.move_type not in ("out_invoice", "in_invoice"):
            raise UserError(_("Document is not an invoice."))
        if invoice.state != "posted":
            raise UserError(_("Only posted (confirmed) invoices can be used. Please confirm the invoice first."))

        invoice_qtys = self._get_invoice_quantities_by_product(invoice)

        # DB search instead of Python filter (faster on large POs)
        picking = self.env["stock.picking"].sudo().search([
            ("id", "in", purchase_order.picking_ids.ids),
            ("state", "not in", ("done", "cancel")),
        ], order="id", limit=1)

        if not picking:
            raise UserError(
                _("No open receipt found for Purchase Order %s. Create or confirm the receipt first.")
                % purchase_order.name
            )

        # Disable mail tracking, recomputes & unnecessary side-effects
        perf_ctx = {
            "mail_notrack": True,
            "tracking_disable": True,
            "mail_create_nolog": True,
            "mail_activity_automation_skip": True,
        }
        picking = picking.with_context(**perf_ctx)
        if picking.state in ("draft", "waiting"):
            picking.action_confirm()

        # DB search instead of Python filter for active moves
        active_moves = self.env["stock.move"].sudo().search([
            ("picking_id", "=", picking.id),
            ("state", "not in", ("done", "cancel")),
            ("product_id", "!=", False),
        ])

        # Prefetch product data in batch
        active_moves.mapped('product_id.uom_id')
        active_moves.mapped('product_uom')

        moves_to_update = self.env["stock.move"]
        for move in active_moves:
            pid = move.product_id.id
            inv_qty = invoice_qtys.get(pid, 0)
            rounding = move.product_uom.rounding
            if float_is_zero(inv_qty, precision_rounding=rounding):
                continue
            # Skip UoM conversion if same UoM
            if move.product_id.uom_id == move.product_uom:
                move.quantity = inv_qty
            else:
                move.quantity = move.product_id.uom_id._compute_quantity(
                    inv_qty, move.product_uom, round=False
                )
            moves_to_update |= move

        if not moves_to_update:
            raise UserError(
                _("Invoice has no product quantities matching the receipt. Check the invoice and receipt lines.")
            )

        # Batch write picked flag in one query
        moves_to_update.write({"picked": True})

        res = picking.with_context(
            skip_backorder=True,
            skip_sanity_check=True,
            **perf_ctx,
        )._pre_action_done_hook()
        if res is not True:
            return _response("warning", _("Receipt needs additional steps."), action=res)
        picking.with_context(cancel_backorder=False, **perf_ctx)._action_done()

        return _response("success", _("Purchase order receipt validated successfully."))