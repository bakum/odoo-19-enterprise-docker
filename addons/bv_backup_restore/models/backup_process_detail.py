import os
import tempfile

from odoo import _, fields, models
from odoo.exceptions import UserError


class BackupProcessDetail(models.Model):
    _name = "backup.process.detail"
    _description = "Backup Process Detail"
    _order = "id desc"

    name = fields.Char()
    file_name = fields.Char()
    backup_process_id = fields.Many2one("backup.process", required=True, ondelete="cascade")
    file_path = fields.Char()
    url = fields.Char()
    backup_date_time = fields.Datetime()
    status = fields.Char()
    message = fields.Char()
    backup_location = fields.Selection(related="backup_process_id.backup_location")

    def download_db_file(self):
        self.ensure_one()
        if self.status != "Success":
            raise UserError(_("Only successful backups can be downloaded."))

        path_to_download = self.url
        if self.backup_location == "remote":
            path_to_download = self._fetch_remote_file_locally()
        if not path_to_download or not os.path.exists(path_to_download):
            raise UserError(_("Backup file is not available."))
        return {
            "type": "ir.actions.act_url",
            "url": f"/bv_backup_restore/download?path={path_to_download}&backup_location={self.backup_location}",
            "target": "new",
        }

    def _fetch_remote_file_locally(self):
        self.ensure_one()
        process = self.backup_process_id
        ssh = process._login_remote()
        local_file = os.path.join(tempfile.gettempdir(), self.file_name)
        with ssh.open_sftp() as sftp:
            sftp.get(self.url, local_file)
        ssh.close()
        return local_file

    def unlink_confirmation(self):
        self.ensure_one()
        if self.status != "Success":
            return self.unlink()
        message = _(
            "<p><strong>Warning:</strong> Deleting this log removes only the record, not the file on storage.</p>"
            "<p>Do you want to continue?</p>"
        )
        wizard = self.env["backup.deletion.confirmation"].create({"backup_id": self.id, "message": message})
        return {
            "type": "ir.actions.act_window",
            "name": _("Deletion Confirmation"),
            "view_mode": "form",
            "res_model": "backup.deletion.confirmation",
            "res_id": wizard.id,
            "target": "new",
        }
