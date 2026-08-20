{
    'name': 'Objectives & Key Results | OKR Management | Employee Goal Tracking | KPI & Targets | Performance Management',
    'summary': 'Help you implement and execute OKR (Objectives & Key Results) in your organizations',
    'description': """
Objectives & Key Results (OKR)
==============================
OKR is a goal-setting framework designed to define and link the objectives of enterprises, departments, and employees to specific, measurable outcomes.

Key Features:
-------------
* OKR Definitions: Create, edit, and track OKRs at individual, department, and organizational levels.
* Automated Progress Measurement: Track objective achievements automatically through key result metrics.
* Visualization: View objectives & key result hierarchies.
    """,
    'author': 'Uncanny Consulting Services LLP',
    'website': 'https://uncannycs.com',
    'category': 'Human Resources/OKR',
    'version': '19.0.1.0.0',
    'depends': ['hr', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/okr_node_views.xml',
        'views/root_menu.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_public_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': [
        'static/description/banner.gif'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': '0',
    'currency': 'USD',
    'license': 'Other proprietary',
}
