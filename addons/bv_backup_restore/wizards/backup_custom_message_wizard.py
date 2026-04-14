from odoo import fields, models


class BackupCustomMessageWizard(models.TransientModel):
    _name = "backup.custom.message.wizard"
    _description = "Backup Custom Message Wizard"

    message = fields.Html(readonly=True)
