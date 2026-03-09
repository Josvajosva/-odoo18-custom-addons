from odoo import http, fields
from odoo.http import request
from odoo.fields import Domain

class InvoiceAPIController(http.Controller):

    @http.route('/api/v1/invoice/update', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def update_invoice(self, **post):
        """
        Update invoice lines via JSON-RPC call.
        Expected payload:
        {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "method": "write",
                "application_id": "A12345678",
                "tally_invoice_no": "Z1000",
                "invoice_line_ids": [[{
                    "product_id": "Inline emitting system",
                    "quantity": 1.0,
                    "price_unit": 125000.00,
                    "name": "Updated Product Description",
                    "tax": ["5%"]
                }]]
            }
        }
        """
        try:
            # Extract API token
            token = request.httprequest.headers.get('Authorization')
            if token and token.startswith('Bearer '):
                token = token[7:]
            elif not token:
                token = post.get('api_token')

            if not token:
                return {'success': False, 'error': 'Missing API token.'}

            # Validate API token
            user = request.env['res.users.apikeys']._check_credentials(scope='odoo.restapi', key=token)
            if not user:
                return {'success': False, 'error': 'Invalid or expired API token.'}
                
            # Extract JSON-RPC body
            #data = post#request.jsonrequest
            params = post
            application_id = params.get("application_id")
            line_groups = params.get("invoice_line_ids", [])
            
            if not application_id:
                return {"error": "Missing application_id arg"}

            # 🔹 Find invoice by custom application_id
            domain = Domain("application_id", "=", application_id)
            invoice = request.env["account.move"].sudo().search(domain, limit=1)
            
            if not invoice:
                return {"error": f"Invoice not found for application_id {application_id}"}

            new_lines = []
            for group in line_groups:
                for line in group:
                    # 🔸 Resolve product
                    product_name = line.get("product_id")
                    product = None
                    if product_name:
                        product_domain = Domain("name", "=", product_name)
                        product = request.env["product.product"].sudo().search(product_domain, limit=1)
                        if not product:
                            return {"error": f"Product '{product_name}' not found"}

                    # 🔸 Resolve taxes
                    tax_names = line.get("tax", [])
                    tax_domain = Domain("name", "=", product_name)
                    tax_ids = request.env["account.tax"].sudo().search(tax_domain)

                    # 🔸 Prepare invoice line
                    vals = {
                        "name": line.get("name") or (product.display_name if product else "No name"),
                        "quantity": line.get("quantity", 1.0),
                        "price_unit": line.get("price_unit", 0.0),
                        "tax_ids": [(6, 0, tax_ids.ids)],
                    }
                    if product:
                        vals["product_id"] = product.id

                    new_lines.append((0, 0, vals))

            # 🔹 Replace existing lines
            invoice.sudo().write({
                "zoho_invoice_no": params.get("tally_invoice_no"),
                "invoice_line_ids": [(5, 0, 0)] + new_lines #[(5, 0, 0)] + 
            })
            if invoice.state == 'draft':
                invoice.action_post()
            return {
                "jsonrpc": "2.0",
                "result": {
                    "status": "success",
                    "invoice_name": invoice.name,
                    "message": "Invoice lines updated successfully"
                }
            }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": str(e)
            }


class PaymentAPIController(http.Controller):

    @http.route('/api/v1/payment/create', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def create_payment(self, **post):
        """
        Create a payment linked to an invoice using JSON input.
        Example input:
        {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "method": "create",
                "amount": 125000.00,
                "ref": "Z1000",
                "date": "2025-10-08 12:05:05",
                "notes": "Payment for Invoice INV/2025/00456",
                "application_id": "A12345678"
            }
        }
        """
        try:
            # Extract API token
            token = request.httprequest.headers.get('Authorization')
            if token and token.startswith('Bearer '):
                token = token[7:]
            elif not token:
                token = post.get('api_token')

            if not token:
                return {'success': False, 'error': 'Missing API token.'}

            # Validate API token
            user = request.env['res.users.apikeys']._check_credentials(scope='odoo.restapi', key=token)
            if not user:
                return {'success': False, 'error': 'Invalid or expired API token.'}
                
            params = post#kwargs.get("params", {})
            application_id = params.get("application_id")
            amount = params.get("amount")
            ref = params.get("ref")
            date = params.get("date")
            #notes = params.get("notes")

            # Find related invoice by application_id
            invoice_domain = Domain("move_type", "=", "out_invoice")
            invoice_domain += [("application_id", "=", application_id)]
            invoice = request.env["account.move"].sudo().search(
                invoice_domain, limit=1
            )

            if not invoice:
                return {"error": f"No invoice found for application_id: {application_id}"}

            partner = invoice.partner_id
            journal_domain = Domain("type", "=", "bank")
            journal = request.env["account.journal"].sudo().search(
                journal_domain, limit=1
            )

            if not journal:
                return {"error": "No bank journal found to record the payment."}

            # Prepare payment values
            payment_vals = {
                "payment_type": "inbound",  # Customer payment
                "partner_type": "customer",
                "partner_id": partner.id,
                "amount": amount,
                "currency_id": invoice.currency_id.id,
                "date": fields.Datetime.from_string(date),
                "memo": ref,
                "journal_id": journal.id,
                "payment_method_id": request.env.ref("account.account_payment_method_manual_in").id,
                "invoice_ids": [(6, 0, invoice.ids)],
                #"communication": notes,
            }
            
            # Create payment
            payment = request.env["account.payment"].sudo().create(payment_vals)

            # (Optional) Post payment and reconcile
            payment.move_id.sudo().write({"application_id": application_id})
            payment_lines = payment.move_id.line_ids.filtered(lambda l: l.account_type == 'receivable')
            invoice_lines = invoice.mapped("line_ids").filtered(lambda l: l.account_type == 'receivable')
            (payment_lines + invoice_lines).reconcile()
            payment.action_post()
            # Return success response
            return {
                "success": True,
                "message": "Payment created successfully.",
                "payment_id": payment.id,
                "payment_name": payment.name,
                "amount": payment.amount,
                "invoice": invoice.zoho_invoice_no,
            }

        except Exception as e:
            return {"error": str(e)}

