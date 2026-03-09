# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Product Xlsx report',
    'category': 'Customization',
    'description': """ """,
    'summary': 'Stock/Sales',
    'version': '18.0',
    'author': "OODU IMPLEMENTERS PRIVATE LIMITED",
    'website': "https://www.odooimplementers.com/",
    'depends': ['sale_management','stock','contacts','mrp'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard.xml',
        'wizard/sales_wizard.xml',
        'wizard/manufacture_wizard.xml',
        'wizard/product_variance.xml',
        'wizard/inventory_valuation.xml',
        'views/scrap.xml'
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
