{
    'name': 'Mrp Subcontracting',
    'version': '1.0',
    'summary': 'Create bill for mrp work orders',
    'description': 'Bill generate',
    'author': 'Rajeeth T {+91 97878 83489}',
    'depends': ['base', 'product','mrp','stock'],
    'data': [
        'views/mrp_bill_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}