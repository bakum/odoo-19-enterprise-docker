import logging

import paramiko

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BackupRemoteServer(models.Model):
    _name = "backup.remote.server"
    _description = "Backup Remote Server"

    name = fields.Char(required=True)
    sftp_host = fields.Char(required=True)
    sftp_port = fields.Integer(default=22, required=True)
    sftp_user = fields.Char(required=True)
    sftp_password = fields.Char(required=True)
    state = fields.Selection([("draft", "Draft"), ("validated", "Validated")], default="draft")
    active = fields.Boolean(default=True)
    temp_backup_dir = fields.Char(required=True)
    def_backup_dir = fields.Char(required=True)

    def test_host_connection(self):
        self.ensure_one()
        self.check_host_connected_call(raise_on_error=True)
        wizard = self.env["backup.custom.message.wizard"].create({"message": _("Connection successful!")})
        action = self.env.ref("bv_backup_restore.action_backup_custom_message_wizard").read()[0]
        action["res_id"] = wizard.id
        return action

    def check_host_connected_call(self, raise_on_error=False):
        self.ensure_one()
        response = {"status": True, "message": _("Success")}
        try:
            ssh = self._get_ssh_client()
            self._validate_remote_dir(ssh, self.def_backup_dir)
            ssh.close()
        except Exception as error:
            _logger.exception("Remote server validation failed for server %s", self.id)
            response.update({"status": False, "message": str(error)})
            if raise_on_error:
                raise UserError(str(error))
        return response

    def _get_ssh_client(self):
        self.ensure_one()
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=self.sftp_host,
            username=self.sftp_user,
            password=self.sftp_password,
            port=int(self.sftp_port or 22),
        )
        return ssh

    def _validate_remote_dir(self, ssh, backup_dir):
        cmd_check = f"ls {backup_dir}"
        cmd_touch = f"touch {backup_dir}/.bv_backup_restore_test"
        cmd_rm = f"rm {backup_dir}/.bv_backup_restore_test"
        for command in (cmd_check, cmd_touch, cmd_rm):
            _, stdout, stderr = ssh.exec_command(command)
            errors = stderr.readlines()
            if errors:
                raise UserError(_("Remote command failed: %s") % "".join(errors))
            stdout.readlines()

    def set_validated(self):
        for record in self:
            record.check_host_connected_call(raise_on_error=True)
            record.state = "validated"

    def reset_to_draft(self):
        for record in self:
            active_processes = self.env["backup.process"].search_count(
                [
                    ("remote_server_id", "=", record.id),
                    ("backup_location", "=", "remote"),
                    ("state", "=", "running"),
                ]
            )
            if active_processes:
                raise UserError(_("This remote server is used by active backup processes."))
            record.state = "draft"
