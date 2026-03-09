from odoo import http
from odoo.http import request, Response
from datetime import datetime, timedelta
import requests
import requests
import json
from odoo import models




class PurchaseOrderZohoAPIController(http.Controller):


    @http.route('/purchase/zoho/api', auth="public", type='http', methods=['GET'], csrf=False)

    def api_purchase_rec(self, **kw):

        try:
            # Extract auth_key and encapiKey from the request parameters
            auth_type = kw.get('auth_type')
            encapiKey = kw.get('encapiKey')

            # Check if auth_type and encapiKey are provided
            if not auth_type or not encapiKey:
                return Response(json.dumps({'success': False, 'error': 'Missing auth_type or encapiKey.'}),
                                content_type='application/json;charset=utf-8',
                                status=400)

            # Validate the API key
            api_user_id = request.env['res.users.apikeys']._check_credentials(scope='db', key=encapiKey)
            if not api_user_id:
                return Response(json.dumps({'success': False, 'error': 'Invalid or expired API key.'}),
                                content_type='application/json;charset=utf-8',
                                status=401)

            # Fetch the user associated with the API key
            res_user = request.env['res.users'].sudo().search([('id', '=', api_user_id)], limit=1)
            if not res_user:
                return Response(json.dumps({'success': False, 'error': 'User not found.'}),
                                content_type='application/json;charset=utf-8',
                                status=404)

            # Fetch incoming stock pickings
            purchase_orders = request.env['purchase.order'].sudo().search([])

            if not purchase_orders:
                return Response(json.dumps({'success': False, 'error': 'No incoming receipts found.'}),
                                content_type='application/json;charset=utf-8',
                                status=404)

            res = {
                'Zoho_api': []
            }


            for po in purchase_orders:
                po_entry = {
                    "vendor_id": po.partner_id.ref or "",  # Assuming vendor ID is stored in partner ref
                    "reference_number": po.name,
                    "gst_treatment": "business_gst",  # Modify as needed
                    "gst_no": po.partner_id.vat or "",  # Assuming GST number is stored in VAT field
                    "source_of_supply": "AP",  # Modify as per business logic
                    "destination_of_supply": "TN",  # Modify as per business logic
                    "date": po.date_order.strftime('%Y-%m-%d'),
                    "delivery_date": po.date_planned.strftime('%Y-%m-%d') if po.date_planned else "",
                    "due_date": "",  # Modify as needed
                    "discount": "",  # Modify if discount is applicable
                    "notes": "Please deliver as soon as possible.",
                    "terms": "Thanks for your business.",
                    "custom_fields": [
                        {
                            "customfield_id": "1611956000001825822",
                            "api_name": "cf_project",
                            "value": "BERACHAH ENTERPRISE"
                        }
                    ],
                    "line_items": [
                        {
                            "item_id": line.product_id.zoho_id or "",  # Assuming product internal reference
                            "name": line.product_id.name,
                            "unit": line.product_uom.name,
                            "rate": line.price_unit,
                            "quantity": line.product_qty
                        } for line in po.order_line
                    ]
                }

                res['Zoho_api'].append(po_entry)

            # Return the response
            return Response(
                json.dumps(res, sort_keys=False, indent=4),
                content_type='application/json;charset=utf-8',
                status=200
            )

        except Exception as e:

            return Response(json.dumps({'success': False, 'error': f'Internal Server Error: {str(e)}'}),
                            content_type='application/json;charset=utf-8',
                            status=500)



class PurchaseZoho(models.Model):
    _name = "purchase.zoho"
    _description = "Sync Purchase Orders to Zoho"

    def api_created_purchase_zoho(self, **kw):
        try:
            url = "https://www.zohoapis.in/books/v3/settings/incomingwebhooks/iw_create_purchase_order/execute?auth_type=apikey&encapiKey=PHtE6r1YQb3u3m568RhT5qTtRZakN9gor%2BhhKwEU445EWfEAH00Doogqmme2qU0vB6IWHaGSy4o64rOYtr6CIDzsZ20fVWqyqK3sx%2FVYSPOZhM3mjRZy6Bp1JAaJBcK6HJculneO65yPFvnvEDkS"

            headers = {'Content-Type': 'application/json'}

            # Fetch latest completed purchase order
            po = request.env['purchase.order'].sudo().search([('state', '=', 'draft')], order='date_order desc', limit=1)

            if not po:
                return Response(json.dumps({'success': False, 'error': 'No completed purchase orders found.'}),
                                content_type='application/json;charset=utf-8',
                                status=404)

            # Check if vendor_id exists
            vendor_id = po.partner_id.ref if po.partner_id.ref else ""
            if not vendor_id:
                return Response(json.dumps({'success': False, 'error': 'Vendor ID (ref) missing for supplier.'}),
                                content_type='application/json;charset=utf-8',
                                status=400)

            # Build line items
            line_items = []
            for line in po.order_line:
                item_id = line.product_id.zoho_id if line.product_id.zoho_id else ""
                if not item_id:
                    return Response(json.dumps({'success': False, 'error': f'Item ID missing for product {line.product_id.name}'}),
                                    content_type='application/json;charset=utf-8',
                                    status=400)

            # Fetch Zoho Tax Code only from taxes present in po.order_line
            zoho_tax_code = ""
            if line.taxes_id:
                tax_codes = [tax.zoho_tax_code for tax in line.taxes_id if tax.zoho_tax_code]
                zoho_tax_code = tax_codes[0] if tax_codes else ""  # Take only the first valid tax code


            line_items.append({
                    "item_id": item_id,
                    "unit": line.product_uom.name,
                    "rate": line.price_unit,
                    "quantity": line.product_qty,
                    "tax_id": zoho_tax_code
                })



            # Construct payload
            grn_data = {
                "vendor_id": vendor_id,
                "gst_treatment": "business_gst",
                "gst_no": po.partner_id.vat if po.partner_id.vat else "",
                "source_of_supply": "",
                "destination_of_supply": "",
                "date": po.date_order.strftime('%Y-%m-%d'),
                "notes": po.notes,
                "custom_fields": [
                    {
                        "customfield_id": "1611956000001825822",
                        "api_name": "cf_project",
                        "value": po.partner_id.name if po.partner_id.name else ""
                    },
                    {
                        "customfield_id": "1611956000009888094",
                        "api_name": "cf_odoo_id",
                        "value": po.name
                    }

                ],
                "line_items": line_items
            }

            payload = {"JSONString": json.dumps(grn_data)}

            # Print payload for debugging
            print("Payload Sent to Zoho:", json.dumps(grn_data, indent=4))

            # Send request
            response = requests.post(url, json=payload, headers=headers)

            # Log response
            print("Zoho API Response:", response.status_code, response.text)

            if response.status_code == 200:
                return Response("Created successfully", status=200)
            else:
                return Response(f"Creation failed: {response.text}", status=response.status_code)

        except json.JSONDecodeError:
            return Response("Invalid JSON format", status=400)
        except Exception as e:
            return Response(f"Internal Server Error: {str(e)}", status=500)


