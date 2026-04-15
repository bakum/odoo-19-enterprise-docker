import logging
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class BackupGDriveConfig(models.Model):
    _name = "backup.gdrive.config"
    _description = "Backup Google Drive Configuration"

    name = fields.Char(required=True)
    client_id = fields.Char(required=True)
    client_secret = fields.Char(required=True)
    redirect_uri = fields.Char(required=True, default="http://localhost")
    auth_code = fields.Char(help="Temporary OAuth code from Google consent screen.")
    refresh_token = fields.Char(copy=False)
    folder_id = fields.Char(required=True, help="Google Drive folder ID where backups are stored.")
    state = fields.Selection([("draft", "Draft"), ("validated", "Validated")], default="draft")
    active = fields.Boolean(default=True)

    def _build_client_config(self):
        self.ensure_one()
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }

    def action_get_auth_url(self):
        self.ensure_one()
        flow = Flow.from_client_config(self._build_client_config(), scopes=GDRIVE_SCOPES)
        flow.redirect_uri = self.redirect_uri
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
        wizard = self.env["backup.custom.message.wizard"].create(
            {
                "message": _(
                    "Open this URL, approve access, then paste returned code in Authorization Code field:\n%s"
                )
                % auth_url
            }
        )
        action = self.env.ref("bv_backup_restore.action_backup_custom_message_wizard").read()[0]
        action["res_id"] = wizard.id
        return action

    def action_fetch_refresh_token(self):
        self.ensure_one()
        if not self.auth_code:
            raise UserError(_("Authorization code is required."))
        flow = Flow.from_client_config(self._build_client_config(), scopes=GDRIVE_SCOPES)
        flow.redirect_uri = self.redirect_uri
        code = self.auth_code.strip()
        if "code=" in code:
            parsed = parse_qs(urlparse(code).query)
            code = parsed.get("code", [code])[0]
        flow.fetch_token(code=code)
        refresh_token = flow.credentials.refresh_token
        if not refresh_token:
            raise UserError(_("Google did not return a refresh token. Use prompt=consent and retry."))
        self.refresh_token = refresh_token
        self.state = "validated"
        self.auth_code = False
        return self.test_connection()

    def _build_credentials(self):
        self.ensure_one()
        if not self.refresh_token:
            raise UserError(_("Refresh token is missing. Generate it first."))
        credentials = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=GDRIVE_SCOPES,
        )
        credentials.refresh(Request())
        return credentials

    def get_drive_service(self):
        self.ensure_one()
        credentials = self._build_credentials()
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    def test_connection(self):
        self.ensure_one()
        try:
            service = self.get_drive_service()
            file_info = service.files().get(fileId=self.folder_id, fields="id,name,mimeType").execute()
            if file_info.get("mimeType") != "application/vnd.google-apps.folder":
                raise UserError(_("Folder ID must reference a Google Drive folder."))
        except Exception as error:
            _logger.exception("Google Drive validation failed for config %s", self.id)
            self.state = "draft"
            raise UserError(_("Google Drive validation failed: %s") % error) from error
        self.state = "validated"
        wizard = self.env["backup.custom.message.wizard"].create({"message": _("Google Drive connection successful!")})
        action = self.env.ref("bv_backup_restore.action_backup_custom_message_wizard").read()[0]
        action["res_id"] = wizard.id
        return action

    def reset_to_draft(self):
        self.write({"state": "draft"})

    def action_open_folder(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"https://drive.google.com/drive/folders/{self.folder_id}",
            "target": "new",
        }
