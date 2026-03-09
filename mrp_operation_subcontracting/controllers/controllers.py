# -*- coding: utf-8 -*-
# from odoo import http


# class MrpOperationSubcontracting(http.Controller):
#     @http.route('/mrp_operation_subcontracting/mrp_operation_subcontracting', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mrp_operation_subcontracting/mrp_operation_subcontracting/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mrp_operation_subcontracting.listing', {
#             'root': '/mrp_operation_subcontracting/mrp_operation_subcontracting',
#             'objects': http.request.env['mrp_operation_subcontracting.mrp_operation_subcontracting'].search([]),
#         })

#     @http.route('/mrp_operation_subcontracting/mrp_operation_subcontracting/objects/<model("mrp_operation_subcontracting.mrp_operation_subcontracting"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mrp_operation_subcontracting.object', {
#             'object': obj
#         })
