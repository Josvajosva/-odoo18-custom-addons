# -*- coding: utf-8 -*-
{
    'name': "MRP manufacturing order subcontract operation bill creation",

    'summary': """
        Allow to subcontract the operation (work order) by setting the workcenter at vendor's site.
        Purchase order to the vendor will be created with the product (service) named as "operation_name@manufacturing_order".
        
        """,

    'description': """
        Allow to subcontract the operation (work order)
    """,

    'author': "",
    'website': "",

    "license": "LGPL-3",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Manufacturing',
    'version': '18.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mrp', 'purchase', 'stock', 'account', 'sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sale_email_template.xml',
        'data/sale_order_dashboard.xml',
        # 'views/views.xml',
        'views/mrp_workcenter_views.xml',
        # 'views/mrp_workorder_views.xml',
        'views/mrp_production_views.xml',
         'views/mrp_checklist.xml',
        'wizard/swapping_customer.xml',
        'views/sale_bom_view.xml',
        'views/sale_order_status.xml',
        'views/stock_scrap.xml',
        'views/templates.xml',
        'views/custom_view.xml',
        'views/similar_work_order_view.xml'

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    # "assets": {
    #         "web.assets_backend": [
    #             "mrp_operation_subcontracting/static/src/js/sale_order_dashboard.js",
    #         ],
    #     },
}
