# -*- coding: utf-8 -*-
{
    'name': "Pipes Project",
    'summary': "Comprehensive pipeline management for CRM, Sales, Projects and Invoicing",
    'description': """
Pipes Project Management System
===============================
This module provides end-to-end management of pipeline projects across multiple business functions.

Key Features:
- Complete workflow management from lead generation to project completion
- Track project milestones, approvals, and fund disbursements
- Integrated management of CRM, Sales, Projects and Invoicing
- Multi-level approval processes for work orders and fund releases
- Comprehensive tracking of project financials and documentation

The system supports various approval stages including work orders, completion certifications, and fund release processes across block, district, and state levels.
    """,
    'author': "Ciberon",
    'website': "https://www.yourcompany.com",
    'category': 'Project Management',
    'version': '1.0',
    'depends': ['base', 'project', 'sale_management', 'crm', 'stock', 'mrp', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/data.xml',
        'views/crm_form_view.xml',
        'views/sale_order_view.xml',
        'views/invoice_form.xml',
        'views/res_company.xml',
        # 'views/res_partner_view.xml',
        'views/inventory_adjustment_view.xml',
        'views/commission_view.xml',
        'views/payment_status_view.xml',
        'views/wizard_import_view.xml',
        'wizard/commission_wizard.xml',
        'wizard/dealer_wizard.xml',
        'wizard/dealerwise_wizard.xml',
        'report/commission_report.xml',
        'report/dealer_report.xml',
        'report/dealerwise_report.xml',
    ],
    'demo': [],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
