{
    'name': 'Loyalty Custom - Floor Points & Double Points',
    'version': '18.0.1.0.0',
    'category': 'Sales/Loyalty',
    'summary': 'Floor-based loyalty points calculation with repeat purchase doubling',
    'description': """
        - Floor-based point calculation: Only complete multiples of the threshold earn points.
          e.g. Every 100 RS = 5 points, so 165 RS = 5 points, 200 RS = 10 points.
        - Repeat purchase doubling: If a customer purchases again within N days,
          their points are doubled for that purchase.
        - Works for both POS and Sale Orders.
    """,
    'depends': ['loyalty', 'sale_loyalty', 'pos_loyalty'],
    'data': [
        'views/loyalty_program_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'loyalty_custom/static/src/overrides/models/**/*.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}