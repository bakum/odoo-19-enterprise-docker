import datetime
import json
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile

import paramiko

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.service.db import exec_pg_environ, find_pg_tool
from odoo.tools import config

_logger = logging.getLogger(__name__)


class BackupProcess(models.Model):
    _name = "backup.process"
    _description = "Backup Process"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    def _default_db_name(self):
        return self.env.cr.dbname

    name = fields.Char(readonly=True, default="/")
    frequency_cycle = fields.Selection(
        [
            ("half_day", "Twice a day"),
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
        default="daily",
        required=True,
        tracking=True,
    )
    storage_path = fields.Char(required=True, tracking=True)
    backup_location = fields.Selection(
        [("local", "Local"), ("remote", "Remote Server")],
        default="local",
        required=True,
        tracking=True,
    )
    retention = fields.Integer(default=7)
    db_name = fields.Char(default=_default_db_name, required=True, tracking=True)
    backup_starting_time = fields.Datetime(required=True)
    next_execution = fields.Datetime(readonly=True, tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("running", "Running"), ("cancel", "Cancel")],
        default="draft",
        tracking=True,
    )
    backup_details_ids = fields.One2many("backup.process.detail", "backup_process_id")
    backup_format = fields.Selection(
        [("zip", "zip (includes filestore)"), ("dump", "pg_dump custom format")],
        default="zip",
        required=True,
        tracking=True,
    )
    enable_retention = fields.Boolean(default=False)
    remote_server_id = fields.Many2one(
        "backup.remote.server",
        domain=[("state", "=", "validated")],
    )

    @api.constrains("retention")
    def _check_retention_value(self):
        for rec in self:
            if rec.enable_retention and rec.retention < 1:
                raise UserError(_("Backup retention count must be at least 1."))

    @api.constrains("backup_location", "remote_server_id")
    def _check_remote_server(self):
        for rec in self:
            if rec.backup_location == "remote" and not rec.remote_server_id:
                raise UserError(_("Remote server is required for remote backup location."))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = sequence.next_by_code("backup.process") or "/"
        return super().create(vals_list)

    def confirm_process(self):
        for rec in self:
            if rec.state != "draft":
                continue
            if rec.backup_location == "remote":
                rec.remote_server_id.check_host_connected_call(raise_on_error=True)
            rec.state = "running"
            rec.next_execution = rec.backup_starting_time

    def cancel_process(self):
        self.write({"state": "cancel"})

    def reset_to_draft(self):
        self.write({"state": "draft", "next_execution": False})

    def action_run_now(self):
        for rec in self:
            if rec.state != "running":
                raise UserError(_("Manual run is available only for running processes."))
            rec._execute_backup_job()

    def test_host_connection(self):
        self.ensure_one()
        if not self.remote_server_id:
            raise UserError(_("Please select a remote server first."))
        self.remote_server_id.check_host_connected_call(raise_on_error=True)
        wizard = self.env["backup.custom.message.wizard"].create({"message": _("Connection successful!")})
        action = self.env.ref("bv_backup_restore.action_backup_custom_message_wizard").read()[0]
        action["res_id"] = wizard.id
        return action

    @api.model
    def cron_run_due_backups(self):
        now = fields.Datetime.now()
        due_records = self.search([("state", "=", "running"), ("next_execution", "<=", now)])
        for record in due_records:
            record._execute_backup_job()

    @api.model
    def cron_remove_old_backups(self):
        processes = self.search([("state", "=", "running"), ("enable_retention", "=", True)])
        for process in processes:
            success_logs = process.backup_details_ids.filtered(lambda d: d.status == "Success").sorted("backup_date_time")
            to_remove = success_logs[:-process.retention] if len(success_logs) > process.retention else self.env["backup.process.detail"]
            if to_remove:
                process._remove_backup_files(to_remove)

    def _execute_backup_job(self):
        self.ensure_one()
        now = fields.Datetime.now()
        backup_log_vals = {
            "name": self.db_name,
            "backup_process_id": self.id,
            "backup_date_time": now,
            "status": "Failure",
            "message": _("Backup failed before execution."),
        }
        try:
            backup_file = self._create_backup_file()
            destination_path = self._store_backup_file(backup_file["tmp_file"], backup_file["file_name"])
            backup_log_vals.update(
                {
                    "file_name": backup_file["file_name"],
                    "file_path": os.path.dirname(destination_path),
                    "url": destination_path,
                    "status": "Success",
                    "message": _("Backup successful at %s") % now,
                }
            )
        except Exception as error:
            _logger.exception("Backup execution failed for process %s", self.id)
            backup_log_vals["message"] = _("Backup failed: %s") % error
        finally:
            self.env["backup.process.detail"].create(backup_log_vals)
            self.next_execution = self._compute_next_execution(now)

    def _create_backup_file(self):
        self.ensure_one()
        timestamp = fields.Datetime.now().strftime("%Y-%m-%d-%H.%M.%S")
        extension = "zip" if self.backup_format == "zip" else "dump"
        filename = f"{self.db_name}_{timestamp}.{extension}"

        if self.backup_format == "dump":
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".dump")
            tmp_file.close()
            cmd = [find_pg_tool("pg_dump"), "--no-owner", "--format=c", f"--file={tmp_file.name}", self.db_name]
            subprocess.run(cmd, env=exec_pg_environ(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            return {"tmp_file": tmp_file.name, "file_name": filename}

        dump_dir = tempfile.mkdtemp(prefix="bv_backup_")
        dump_sql = os.path.join(dump_dir, "dump.sql")
        cmd = [find_pg_tool("pg_dump"), "--no-owner", f"--file={dump_sql}", self.db_name]
        subprocess.run(cmd, env=exec_pg_environ(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        filestore = config.filestore(self.db_name)
        if os.path.exists(filestore):
            shutil.copytree(filestore, os.path.join(dump_dir, "filestore"))
        with open(os.path.join(dump_dir, "manifest.json"), "w", encoding="utf-8") as manifest_file:
            manifest_file.write(json.dumps(self._build_manifest(), indent=4))

        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp_zip.close()
        with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zip_obj:
            for root, _, files in os.walk(dump_dir):
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                    arc_name = os.path.relpath(full_path, dump_dir)
                    zip_obj.write(full_path, arc_name)
        shutil.rmtree(dump_dir, ignore_errors=True)
        return {"tmp_file": tmp_zip.name, "file_name": filename}

    def _build_manifest(self):
        db = odoo.sql_db.db_connect(self.db_name)
        with db.cursor() as cr:
            cr.execute("SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
            modules = dict(cr.fetchall())
            pg_version = "%d.%d" % divmod(cr._obj.connection.server_version / 100, 100)
        return {
            "odoo_dump": "1",
            "db_name": self.db_name,
            "version": odoo.release.version,
            "version_info": odoo.release.version_info,
            "major_version": odoo.release.major_version,
            "pg_version": pg_version,
            "modules": modules,
        }

    def _store_backup_file(self, tmp_file, file_name):
        self.ensure_one()
        if self.backup_location == "local":
            backup_dir = os.path.join(self.storage_path, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            destination = os.path.join(backup_dir, file_name)
            shutil.move(tmp_file, destination)
            return destination

        ssh = self._login_remote()
        remote_file_path = os.path.join(self.storage_path, file_name).replace("\\", "/")
        with ssh.open_sftp() as sftp:
            sftp.put(tmp_file, remote_file_path)
        os.remove(tmp_file)
        ssh.close()
        return remote_file_path

    def _remove_backup_files(self, detail_records):
        self.ensure_one()
        if self.backup_location == "local":
            for detail in detail_records:
                if detail.url and os.path.exists(detail.url):
                    os.remove(detail.url)
                    detail.write({"status": "Dropped", "message": _("Dropped by retention policy.")})
                else:
                    detail.write({"status": "Failure", "message": _("File not found while applying retention.")})
            return

        ssh = self._login_remote()
        with ssh.open_sftp() as sftp:
            for detail in detail_records:
                try:
                    sftp.stat(detail.url)
                    sftp.remove(detail.url)
                    detail.write({"status": "Dropped", "message": _("Dropped by retention policy.")})
                except OSError:
                    detail.write({"status": "Failure", "message": _("Remote file not found while applying retention.")})
        ssh.close()

    def _login_remote(self):
        self.ensure_one()
        if not self.remote_server_id:
            raise UserError(_("Remote server is not configured."))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=self.remote_server_id.sftp_host,
            username=self.remote_server_id.sftp_user,
            password=self.remote_server_id.sftp_password,
            port=int(self.remote_server_id.sftp_port or 22),
        )
        return ssh

    def _compute_next_execution(self, from_dt):
        self.ensure_one()
        base_dt = fields.Datetime.to_datetime(from_dt)
        if self.frequency_cycle == "half_day":
            return base_dt + datetime.timedelta(hours=12)
        if self.frequency_cycle == "daily":
            return base_dt + datetime.timedelta(days=1)
        if self.frequency_cycle == "weekly":
            return base_dt + datetime.timedelta(weeks=1)
        if self.frequency_cycle == "monthly":
            return base_dt + datetime.timedelta(days=30)
        return base_dt + datetime.timedelta(days=365)
