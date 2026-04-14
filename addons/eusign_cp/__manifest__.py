{
    'name': 'EUSignCP Connector',
    'author' : 'Bakum Viacheslav',
    'website' : 'https://optimus.com.ua',
    'summary' : 'EUSignCP Connector',
    'category': 'SCADA/NWServer',
    'version': '19.0.1.0.0',
    'license' : 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
    "data": [
        'views/signer_template.xml',
        'data/data.xml',
    ],
    'assets': {
        'eusign_cp.assets_signer': [
            'eusign_cp/static/src/**/*',
        ],
        'eusign_cp.assets_library': [
            'eusign_cp/static/lib/euutils.js',
            'eusign_cp/static/lib/euscpt.js',
            'eusign_cp/static/lib/euscpm.js',
            'eusign_cp/static/lib/euscp.ex.js',
            'eusign_cp/static/lib/qr/qrcodedecode.js',
            'eusign_cp/static/lib/qr/reedsolomon.js',
            'eusign_cp/static/lib/fs/Blob.min.js',
            'eusign_cp/static/lib/fs/FileSaver.js',
            'eusign_cp/static/lib/fs/jszip.min.js',
            'eusign_cp/static/lib/toastify-js.js',
            'eusign_cp/static/lib/toastify.min.css',
        ]
    },
    'depends': ['base', 'web', "website"],
}