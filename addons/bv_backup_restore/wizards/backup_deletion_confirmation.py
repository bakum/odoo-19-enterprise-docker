from odoo import fields, models


class BackupDeletionConfirmation(models.TransientModel):
    _name = "backup.deletion.confirmation"
    _description = "Backup Deletion Confirmation Wizard"

    backup_id = fields.Many2one("backup.process.detail")
    message = fields.Html()

    def action_delete_backup_detail(self):
        for wizard in self:
            wizard.backup_id.unlink()
