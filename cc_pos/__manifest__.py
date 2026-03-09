{
    "name": "Loyalty Customization",
    'version': '1.0',
    "author": "Priyadharshini A",
    'depends': ['base', 'point_of_sale', 'pos_loyalty', 'contacts'],
    "data": [
        "security/ir.model.access.csv",
        'views/res_partner.xml',
        'views/pos_config_view.xml',
        'views/loyalty_program_views.xml',
        'views/loyalty_rule_views.xml',
        # 'views/activities_menu.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'cc_pos/static/src/js/floor_calculation.js',
            'cc_pos/static/src/js/exclusive_rule.js',
            'cc_pos/static/src/js/payment_screen_patch.js',
        ],
        'point_of_sale.assets': [
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css',
            'loyalty_pos/static/src/js/pos_redeem.js',
            'loyalty_pos/static/src/xml/pos_redeem.xml',
        ],
    },
    'qweb': [
        'static/src/xml/pos_redeem.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False
}