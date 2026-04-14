import logging
import os

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class BackupController(http.Controller):
    @http.route("/bv_backup_restore/download", type="http", auth="user")
    def file_download(self, **kwargs):
        if not request.env.user.has_group("base.group_system"):
            raise UserError("Only administrators can download backup files.")
        file_path = request.httprequest.args.get("path")
        backup_location = request.httprequest.args.get("backup_location") or "local"
        if not file_path:
            raise UserError("Missing file path.")
        try:
            with open(file_path, "rb") as backup_file:
                payload = backup_file.read()
            response = request.make_response(payload)
            response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(file_path)}"
            response.mimetype = "application/octet-stream"
            if backup_location == "remote" and os.path.exists(file_path):
                os.remove(file_path)
            return response
        except Exception as error:
            _logger.exception("Backup file download failed for %s", file_path)
            raise UserError(str(error))
