from unittest.mock import MagicMock, patch

from odoo.tests import common


class TestBackupGDrive(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.gdrive_config = self.env["backup.gdrive.config"].create(
            {
                "name": "GDrive Main",
                "client_id": "client-id",
                "client_secret": "client-secret",
                "redirect_uri": "http://localhost",
                "refresh_token": "refresh-token",
                "folder_id": "folder-id",
                "state": "validated",
            }
        )
        self.process = self.env["backup.process"].create(
            {
                "storage_path": "/tmp",
                "backup_location": "google_drive",
                "gdrive_config_id": self.gdrive_config.id,
                "backup_starting_time": "2026-01-01 00:00:00",
                "db_name": self.env.cr.dbname,
            }
        )
        self.detail = self.env["backup.process.detail"].create(
            {
                "name": self.env.cr.dbname,
                "file_name": "db_2026.zip",
                "backup_process_id": self.process.id,
                "url": "file-id",
                "status": "Success",
            }
        )

    def _mock_drive_service(self):
        delete_obj = MagicMock()
        delete_obj.execute.return_value = {}
        create_obj = MagicMock()
        create_obj.execute.return_value = {"id": "created-file-id"}
        files_obj = MagicMock()
        files_obj.delete.return_value = delete_obj
        files_obj.create.return_value = create_obj
        service = MagicMock()
        service.files.return_value = files_obj
        return service

    def test_download_action_uses_gdrive_route(self):
        action = self.detail.download_db_file()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn(f"/bv_backup_restore_gdrive/download/{self.detail.id}", action["url"])

    def test_remove_backup_files_marks_dropped(self):
        with patch.object(type(self.gdrive_config), "get_drive_service", return_value=self._mock_drive_service()):
            self.process._remove_backup_files(self.detail)
        self.assertEqual(self.detail.status, "Dropped")

    def test_store_backup_file_returns_file_id(self):
        with patch("os.remove"), patch.object(
            type(self.gdrive_config), "get_drive_service", return_value=self._mock_drive_service()
        ):
            value = self.process._store_backup_file("/tmp/test.zip", "test.zip")
        self.assertEqual(value, "created-file-id")
