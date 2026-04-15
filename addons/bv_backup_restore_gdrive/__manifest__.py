{
    "name": "Database Backup Google Drive",
    "summary": "Google Drive storage backend for Database Backup & Restore",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "author": "Bakum Viacheslav",
    "license": "LGPL-3",
    "depends": ["bv_backup_restore"],
    "data": [
        "security/ir.model.access.csv",
        "views/backup_gdrive_config_views.xml",
        "views/backup_process_views.xml",
        "views/menuitems.xml",
    ],
    "installable": True,
    "application": False,
    "external_dependencies": {
        "python": [
            "google-api-python-client",
            "google-auth",
            "google-auth-oauthlib",
            "google-auth-httplib2",
        ]
    },
}
