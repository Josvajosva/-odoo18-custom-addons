from odoo import http
from odoo.http import request
import datetime
import json
import secrets


class VendorPaymentController(http.Controller):
    @http.route(
        "/api/get_access_token/<int:vendor_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def get_access_token(self, vendor_id=None, **kwargs):
        data = {}
        vendor = request.env["res.partner"].sudo().browse(vendor_id)
        if not vendor.exists():
            data['success'] = False
            data['error'] = "Vendor not found"
            data['status'] = 400
        else:
            if not vendor.access_token:
                token = secrets.token_urlsafe(32)
                vendor.sudo().write({"access_token": token})
            else:
                token = vendor.access_token
            data['success'] = True
            data['vendor_id'] = vendor.id
            data['access_token'] = token
            data['status'] = 200
        return request.make_response(
            json.dumps(data),
            headers=[("Content-Type", "application/json")],
            status=data['status'],
        )


    @http.route(
        "/api/make_vendor_payment",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def make_vendor_payment(self, **kwargs):
        payload = request.get_json_data()
        auth_header = request.httprequest.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '').strip()
        if token:
            vendor = request.env["res.partner"].sudo().search([("access_token", "=", token)], limit=1)
            if vendor:
                if {"amount", "date", "type"}.issubset(set(payload.keys())):
                    try:
                        payment_date = datetime.datetime.strptime(payload['date'], "%Y-%m-%d").date()
                    except ValueError as e:
                        return {"success": False, "message": str(e), "status": 400}
                    amount = payload['amount']
                    if amount > 0:
                        payment_vals = {
                            'partner_id': vendor.id,
                            'amount': amount,
                            'date': payment_date,
                            'payment_type': "outbound",
                            'partner_type': 'supplier',
                            "memo": payload['type'],
                        }
                        payment = request.env['account.payment'].sudo().create(payment_vals)
                        payment.action_validate()
                        return {
                            "success": True,
                            "message": "Vendor payment created successfully",
                            "payment_id": payment.id,
                            "payment_name": payment.name,
                            "status": 200,
                        }
                    return {"success": False, "message": "Amount must be greater than 0", "status": 400}
                return {"success": False, "message": f"Required fields are missing", "status": 400}
            return {"success": False, "message": "Invalid token or vendor not found", "status": 401}
        return  {"success": False, "message": "Authorization token is required", "status": 401,}