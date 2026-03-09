# -*- coding: utf-8 -*-
# Part of Hyperland. See LICENSE file for full copyright and licensing details.

{
    'name': 'Loyalty Rule Exclusive',
    'version': '18.0.1.0.0',
    'category': 'Sales/Loyalty',
    'summary': 'Ensure mutually exclusive loyalty rule evaluation based on amount thresholds',
    'description': """
Loyalty Rule Exclusive
======================

This module customizes Odoo's Loyalty Program behavior to ensure:

1. **Mutually Exclusive Rules**: Only ONE rule is applied per order based on amount thresholds.
2. **Automatic Priority**: Rules with higher minimum_amount are evaluated first.
3. **Clear Threshold Logic**:
   - If amount >= 50 → Higher threshold rule applies
   - If amount < 50 → Lower threshold rule applies
4. **No Double Rewards**: Prevents stacking or combining of multiple rules.
5. **Detailed Logging**: Logs which rule was applied for debugging and auditing.

How It Works
------------
When "Exclusive Rule Evaluation" is enabled on a Loyalty Program:

1. Rules are automatically sorted by minimum_amount (descending - highest first)
2. The system checks each rule starting from the highest threshold
3. The FIRST matching rule is applied
4. All other rules are skipped (even if they would match)

Example:
- Rule A: minimum_amount = 50
- Rule B: minimum_amount = 10

With this setup:
- Order of 30 → Only Rule B applies (30 < 50, but 30 >= 10)
- Order of 60 → Only Rule A applies (60 >= 50, Rule B never checked)
- Order of 5 → No rule applies (5 < 10)

No additional configuration needed - just enable the checkbox!
    """,
    'author': 'Hyperland',
    'website': 'https://www.hyperland.com',
    'depends': ['sale_loyalty', 'loyalty', 'pos_loyalty'],
    'data': [
        'views/loyalty_program_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'loyalty_rule_exclusive/static/src/overrides/**/*.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
