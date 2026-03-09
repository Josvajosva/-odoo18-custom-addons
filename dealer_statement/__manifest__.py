{
    "name": "Dealer Statement",
    "summary": "Dealer statement report with XLSX export",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "author": "Your Name",
    "license": "LGPL-3",
    "depends": ["base", "account"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/dealer_statement_report_wizard_views.xml",
        "views/dealer_statement_report_menu.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
