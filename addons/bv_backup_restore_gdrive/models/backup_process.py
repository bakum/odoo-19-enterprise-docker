import os

from googleapiclient.http import MediaFileUpload

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BackupProcess(models.Model):
    _inherit = "backup.process"

    backup_location = fields.Selection(
        selection_add=[("google_drive", "Google Drive")],
        ondelete={"google_drive": "set default"},
    )
    gdrive_config_id = fields.Many2one(
        "backup.gdrive.config",
        domain=[("state", "=", "validated")],
        tracking=True,
    )

    @api.constrains("backup_location", "gdrive_config_id")
    def _check_gdrive_config(self):
        for rec in self:
            if rec.backup_location == "google_drive" and not rec.gdrive_config_id:
                raise UserError(_("Google Drive configuration is required for Google Drive backups."))

    def confirm_process(self):
        for rec in self:
            if rec.state != "draft":
                continue
            if rec.backup_location == "google_drive":
                if not rec.gdrive_config_id:
                    raise UserError(_("Please select a Google Drive configuration first."))
                rec.gdrive_config_id.test_connection()
        return super().confirm_process()

    def test_gdrive_connection(self):
        self.ensure_one()
        if not self.gdrive_config_id:
            raise UserError(_("Please select a Google Drive configuration first."))
        return self.gdrive_config_id.test_connection()

    def _store_backup_file(self, tmp_file, file_name):
        self.ensure_one()
        if self.backup_location != "google_drive":
            return super()._store_backup_file(tmp_file, file_name)

        service = self.gdrive_config_id.get_drive_service()
        metadata = {"name": file_name, "parents": [self.gdrive_config_id.folder_id]}
        media = MediaFileUpload(tmp_file, resumable=True)
        created = service.files().create(body=metadata, media_body=media, fields="id").execute()
        os.remove(tmp_file)
        # Store file id in detail.url for retention/download operations.
        return created["id"]

    def _remove_backup_files(self, detail_records):
        self.ensure_one()
        if self.backup_location != "google_drive":
            return super()._remove_backup_files(detail_records)

        service = self.gdrive_config_id.get_drive_service()
        for detail in detail_records:
            try:
                service.files().delete(fileId=detail.url).execute()
                detail.write({"status": "Dropped", "message": _("Dropped by retention policy.")})
            except Exception:
                detail.write({"status": "Failure", "message": _("Google Drive file not found while applying retention.")})
