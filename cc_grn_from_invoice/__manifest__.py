{
    'name': 'GRN Validation from Invoice',
    'version': '1.0',
    "author": "Priyadharshini A",
    'depends': ['base', 'purchase', 'sale', 'stock', 'account'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}