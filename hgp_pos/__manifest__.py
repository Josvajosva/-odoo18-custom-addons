{
    'name': 'HGP POS',
    'version': '18.0.0.0',
    'category': 'Hidden',
    'sequence': 1,
    'author': 'Boscosoft Technologies Pvt Ltd',
    'website': 'http://www.boscosofttech.com',
    'summary': 'HGP Core',
    'depends': [
        'product',
        'point_of_sale',
    ],
    'data': [
        'views/pos_title.xml',
        'wizard/product_lable.xml',
        'report/product_label.xml',
    ],

    'assets': {
        'point_of_sale._assets_pos': [
            'hgp_pos/static/src/xml/**/*',
            'hgp_pos/static/src/js/**/*'
        ]
    },
    'qweb': [

    ],
    'bootstrap': True, 
    'installable': True,
    'application': True,
    'auto_install': True,
}
