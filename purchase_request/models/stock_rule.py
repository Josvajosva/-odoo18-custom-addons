from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pr_ref = fields.Many2one(
        "purchase.request",
        string="Purchase Request",
        help="Reference to the Purchase Request created for this Sale Order",
    )

    def create_pr_for_selected_so(self):
        PurchaseRequest = self.env["purchase.request"]
        PurchaseRequestLine = self.env["purchase.request.line"]
        PurchaseRequestBom = self.env["purchase.request.bom"]

        if not self:
            raise UserError("No Sale Orders selected!")
        
        # Check if any of the selected Sale Orders already have a PR
        existing_pr_orders = self.filtered(lambda order: order.pr_ref)
        if existing_pr_orders:
            order_names = ", ".join(existing_pr_orders.mapped("name"))
            raise UserError(
                f"Purchase Request already exists for the following Sale Orders: {order_names}."
            )

        confirmed_orders = self.filtered(lambda order: order.state == "sale")
        if not confirmed_orders:
            raise UserError("No confirmed Sale Orders found!")
        
        for order in confirmed_orders:
            for line in order.order_line:
                product = line.product_id
                is_component = self.env["mrp.bom.line"].search_count([("product_id", "=", product.id)]) > 0
                has_bom = self.env["mrp.bom"].search_count([("product_tmpl_id", "=", product.product_tmpl_id.id)]) > 0
                if not has_bom and not is_component:
                    raise UserError(
                        f"The product '{product.name}' has no Bill of Materials. Please create a BoM before generating the Purchase Request."
                    )

        pr = PurchaseRequest.create(
            {
                "origin": ", ".join(confirmed_orders.mapped("name")),
                "company_id": confirmed_orders[0].company_id.id,
            }
        )

        confirmed_orders.write({"pr_ref": pr.id})

        product_lines = {}  # Dictionary to track summed component quantities across all BoMs
        bom_ids = set()  # Track linked BoMs

        def add_to_product_lines(product, uom, qty, request_id):
            """Accumulate quantities for the same product + UOM across all BoMs, using ordered qty directly."""
            key = (product.id, uom.id)  # Unique identifier for each product + UOM

            if key in product_lines:
                product_lines[key]["needed_qty"] += qty  # Sum all occurrences
            else:
                product_lines[key] = {
                    "product_id": product.id,
                    "product_uom_id": uom.id,
                    "needed_qty": qty,
                    "request_id": request_id,
                }

        for order in self:
            for line in order.order_line.filtered(lambda l: l.product_id.type == "product"):
                product = line.product_id
                uom = line.product_uom
                qty = line.product_uom_qty  # Directly use ordered quantity

                bom_records = self.env["mrp.bom"].search(
                    [
                        "|",
                        ("product_id", "=", product.id),
                        ("product_tmpl_id", "=", product.product_tmpl_id.id),
                    ]
                )

                if bom_records:
                    bom_ids.update(bom_records.ids)

                    for bom in bom_records:
                        for bom_line in bom.bom_line_ids:
                            component = bom_line.product_id
                            component_uom = bom_line.product_uom_id
                            component_qty = bom_line.product_qty * qty  # Multiply by ordered qty

                            # Accumulate total required component qty from all BoMs
                            add_to_product_lines(component, component_uom, component_qty, pr.id)

                else:
                    add_to_product_lines(product, uom, qty, pr.id)

        # Now check stock and add to PR only if needed
        final_product_lines = []
        for key, line in product_lines.items():
            product_id, uom_id = key
            product = self.env["product.product"].browse(product_id)

            # Get available stock
            stock_qty = product.qty_available

            if stock_qty < line["needed_qty"]:  # Only add to PR if stock is insufficient
                final_product_lines.append(line)

        if not final_product_lines:
            raise UserError("No valid products found for Purchase Request!")

        # Create Purchase Request Lines
        PurchaseRequestLine.create(final_product_lines)

        # Link the BoMs
        for bom_id in bom_ids:
            PurchaseRequestBom.create({"purchase_request_id": pr.id, "bom_id": bom_id})

        for order in self:
            order.message_post(
                body=f"Purchase Request {pr.name} created successfully, with linked BoMs!"
            )

        return True

    def action_create_pr(self):
        if self.env.context.get("from_confirm_wizard"):
            return self.create_pr_for_selected_so()

        return {
            "type": "ir.actions.act_window",
            "name": "Confirm Purchase Request",
            "res_model": "purchase.request.confirm.wizard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "purchase_request.view_purchase_request_confirm_wizard"
            ).id,
            "target": "new",
            "context": {"default_sale_order_ids": self.ids},
        }

