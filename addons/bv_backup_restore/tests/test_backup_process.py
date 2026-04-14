import tempfile
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestBackupProcess(TransactionCase):
    def setUp(self):
        super().setUp()
        self.process_model = self.env["backup.process"]
        self.storage_path = tempfile.gettempdir()

    def _create_running_process(self):
        process = self.process_model.create(
            {
                "storage_path": self.storage_path,
                "db_name": self.env.cr.dbname,
                "backup_starting_time": "2026-01-01 00:00:00",
                "frequency_cycle": "daily",
                "backup_location": "local",
                "backup_format": "dump",
            }
        )
        process.confirm_process()
        return process

    def test_manual_run_creates_backup_detail(self):
        process = self._create_running_process()
        with (
            patch.object(type(process), "_create_backup_file", return_value={"tmp_file": __file__, "file_name": "fake.dump"}),
            patch.object(type(process), "_store_backup_file", return_value=__file__),
        ):
            process.action_run_now()
        self.assertEqual(len(process.backup_details_ids), 1)
        self.assertEqual(process.backup_details_ids[0].status, "Success")

    def test_cron_runs_due_processes(self):
        process = self._create_running_process()
        process.next_execution = "2000-01-01 00:00:00"
        with (
            patch.object(type(process), "_create_backup_file", return_value={"tmp_file": __file__, "file_name": "fake.dump"}),
            patch.object(type(process), "_store_backup_file", return_value=__file__),
        ):
            self.process_model.cron_run_due_backups()
        process.flush_recordset(["backup_details_ids"])
        self.assertTrue(process.backup_details_ids)

    def test_retention_cleanup_marks_old_entries_as_dropped(self):
        process = self._create_running_process()
        process.enable_retention = True
        process.retention = 2
        details = self.env["backup.process.detail"]

        for idx in range(3):
            details |= self.env["backup.process.detail"].create(
                {
                    "name": process.db_name,
                    "file_name": f"backup_{idx}.dump",
                    "backup_process_id": process.id,
                    "file_path": self.storage_path,
                    "url": __file__,
                    "backup_date_time": f"2026-01-0{idx + 1} 00:00:00",
                    "status": "Success",
                    "message": "ok",
                }
            )

        dropped_ids = []

        def fake_remove(_self, detail_records):
            for detail in detail_records:
                dropped_ids.append(detail.id)
                detail.write({"status": "Dropped"})

        with patch.object(type(process), "_remove_backup_files", fake_remove):
            self.process_model.cron_remove_old_backups()

        self.assertEqual(len(dropped_ids), 1)
        dropped = self.env["backup.process.detail"].browse(dropped_ids[0])
        self.assertEqual(dropped.status, "Dropped")
