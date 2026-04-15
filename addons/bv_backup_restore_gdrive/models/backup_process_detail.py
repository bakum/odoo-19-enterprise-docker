from odoo import models


class BackupProcessDetail(models.Model):
    _inherit = "backup.process.detail"

    def download_db_file(self):
        self.ensure_one()
        if self.backup_location != "google_drive":
            return super().download_db_file()

        return {
            "type": "ir.actions.act_url",
            "url": f"/bv_backup_restore_gdrive/download/{self.id}",
            "target": "new",
        }
