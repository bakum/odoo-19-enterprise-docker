import io
import logging

from googleapiclient.http import MediaIoBaseDownload

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class BackupGDriveController(http.Controller):
    @http.route("/bv_backup_restore_gdrive/download/<int:detail_id>", type="http", auth="user")
    def gdrive_file_download(self, detail_id):
        if not request.env.user.has_group("base.group_system"):
            raise UserError("Only administrators can download backup files.")

        detail = request.env["backup.process.detail"].browse(detail_id)
        if not detail.exists() or detail.backup_location != "google_drive":
            raise UserError("Google Drive backup log was not found.")

        try:
            service = detail.backup_process_id.gdrive_config_id.get_drive_service()
            media_request = service.files().get_media(fileId=detail.url)
            stream = io.BytesIO()
            downloader = MediaIoBaseDownload(stream, media_request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            response = request.make_response(stream.getvalue())
            response.headers["Content-Disposition"] = f"attachment; filename={detail.file_name}"
            response.mimetype = "application/octet-stream"
            return response
        except Exception as error:
            _logger.exception("Google Drive download failed for detail %s", detail_id)
            raise UserError(str(error))
