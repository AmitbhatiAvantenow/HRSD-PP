{
    'name': 'HR Document Templates',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'HR document template engine: build, generate, share and approve HR documents.',
    'description': """
HR-focused document template engine.
Design once with a Canva-like drag-and-drop canvas, merge with per-template
dynamic variables, and generate PDF/DOCX output on demand for the HR document
lifecycle -- offer letters, employment contracts, confidentiality agreements,
policy acknowledgments, appraisal forms, relieving letters and more.
    """,
    'author': 'PS6',
    'depends': ['base', 'mail', 'web'],
    'external_dependencies': {
        'python': ['reportlab', 'PyPDF2', 'qrcode', 'PIL', 'jinja2', 'docx', 'barcode'],
    },
    'data': [
        'security/document_templates_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/document_templates_actions.xml',
        'views/document_templates_menus.xml',
        'data/document_templates_seed_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'document_templates/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
