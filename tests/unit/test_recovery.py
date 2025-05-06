# test_recovery.py

import datetime
import json
import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from evodev.recovery import RecoverySystem


class TestRecoverySystem(unittest.TestCase):
    """Unit tests for the RecoverySystem class"""

    @patch("evodev.recovery.os.makedirs")
    @patch("evodev.recovery.threading.Thread")
    @patch("evodev.recovery.docker.from_env")
    def setUp(self, mock_docker, mock_thread, mock_makedirs):
        """Set up test fixtures"""
        self.recovery_system = RecoverySystem()
        # Make sure the monitoring thread doesn't actually start
        mock_thread.return_value.start.assert_called_once()
        # Configure the mock docker client
        self.mock_docker_client = mock_docker.return_value
        self.recovery_system.docker_client = self.mock_docker_client

    @patch("evodev.recovery.os.environ.get")
    def test_init_with_custom_env_variables(self, mock_env_get):
        """Test initialization with custom environment variables"""
        # Configure mock environment variables
        mock_env_get.side_effect = lambda key, default: {
            "GITLAB_URL": "http://custom-gitlab:8080",
            "GITLAB_API_TOKEN": "custom-token",
            "BACKUP_DIR": "/custom/backups",
            "BACKUP_INTERVAL": "7200",
        }.get(key, default)

        # Create a new instance with custom environment variables
        with patch("evodev.recovery.threading.Thread"), patch(
            "evodev.recovery.docker.from_env"
        ), patch("evodev.recovery.os.makedirs"):
            recovery = RecoverySystem()

            # Verify that environment variables were read correctly
            self.assertEqual(recovery.gitlab_url, "http://custom-gitlab:8080")
            self.assertEqual(recovery.gitlab_token, "custom-token")
            self.assertEqual(recovery.backup_dir, "/custom/backups")
            self.assertEqual(recovery.backup_interval, 7200)

    def test_check_services_status(self):
        """Test the service status checking functionality"""
        # Mock container objects
        container1 = MagicMock()
        container1.name = "gitlab"
        container1.status = "running"
        container1.image.tags = ["gitlab/gitlab-ce:latest"]
        container1.attrs = {
            "Created": "2023-01-01T00:00:00Z",
            "State": {"Health": {"Status": "healthy"}},
        }

        container2 = MagicMock()
        container2.name = "ollama"
        container2.status = "exited"
        container2.image.tags = ["ollama/ollama:latest"]
        container2.attrs = {"Created": "2023-01-01T00:00:00Z", "State": {}}

        # Configure mock Docker client to return our mock containers
        self.mock_docker_client.containers.list.return_value = [container1, container2]

        # Call the method being tested
        result = self.recovery_system._check_services_status()

        # Verify the result
        expected_result = {
            "gitlab": {
                "status": "running",
                "image": "gitlab/gitlab-ce:latest",
                "created": "2023-01-01T00:00:00Z",
                "health": "healthy",
            },
            "ollama": {
                "status": "exited",
                "image": "ollama/ollama:latest",
                "created": "2023-01-01T00:00:00Z",
                "health": "unknown",
            },
        }
        self.assertEqual(result, expected_result)

    @patch("evodev.recovery.datetime.datetime")
    def test_archive_system_state(self, mock_datetime):
        """Test the archiving of system state"""
        # Configure mock datetime
        mock_datetime.now.return_value = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.strftime = datetime.datetime.strftime

        # Sample services status
        services_status = {
            "gitlab": {"status": "running", "image": "gitlab/gitlab-ce:latest"}
        }

        # Configure mock open
        mock_file = mock_open()
        with patch("evodev.recovery.open", mock_file):
            # Call the method being tested
            self.recovery_system._archive_system_state(services_status)

            # Verify that the file was opened with the correct path
            expected_path = os.path.join(
                self.recovery_system.backup_dir, "system_state_20230101_120000.json"
            )
            mock_file.assert_called_once_with(expected_path, "w")

            # Verify that the correct data was written to the file
            expected_data = {
                "timestamp": "20230101_120000",
                "services": services_status,
            }
            mock_file().write.assert_called_once_with(
                json.dumps(expected_data, indent=2)
            )

    @patch("evodev.recovery.requests.get")
    def test_verify_system_integrity_success(self, mock_get):
        """Test system integrity verification when all services are running"""
        # Configure mock services status
        services_status = {
            "gitlab": {"status": "running"},
            "ollama": {"status": "running"},
            "autonomous-system": {"status": "running"},
            "recovery-system": {"status": "running"},
        }

        # Configure mock response from GitLab API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the method being tested
        result = self.recovery_system._verify_system_integrity(services_status)

        # Verify the result
        self.assertTrue(result)

        # Verify that GitLab API was called with the correct parameters
        mock_get.assert_called_once_with(
            f"{self.recovery_system.gitlab_url}/api/v4/projects",
            headers={"Private-Token": self.recovery_system.gitlab_token},
            timeout=5,
        )

    @patch("evodev.recovery.requests.get")
    def test_verify_system_integrity_missing_service(self, mock_get):
        """Test system integrity verification when a critical service is missing"""
        # Configure mock services status with a missing critical service
        services_status = {
            "gitlab": {"status": "running"},
            # ollama is missing
            "autonomous-system": {"status": "running"},
            "recovery-system": {"status": "running"},
        }

        # Call the method being tested
        result = self.recovery_system._verify_system_integrity(services_status)

        # Verify the result
        self.assertFalse(result)

        # GitLab API should not be called if a critical service is missing
        mock_get.assert_not_called()

    @patch("evodev.recovery.requests.get")
    def test_verify_system_integrity_service_not_running(self, mock_get):
        """Test system integrity verification when a critical service is not running"""
        # Configure mock services status with a critical service not running
        services_status = {
            "gitlab": {"status": "running"},
            "ollama": {"status": "exited"},  # Not running
            "autonomous-system": {"status": "running"},
            "recovery-system": {"status": "running"},
        }

        # Call the method being tested
        result = self.recovery_system._verify_system_integrity(services_status)

        # Verify the result
        self.assertFalse(result)

        # GitLab API should not be called if a critical service is not running
        mock_get.assert_not_called()

    @patch("evodev.recovery.requests.get")
    def test_verify_system_integrity_gitlab_api_error(self, mock_get):
        """Test system integrity verification when GitLab API returns an error"""
        # Configure mock services status with all critical services running
        services_status = {
            "gitlab": {"status": "running"},
            "ollama": {"status": "running"},
            "autonomous-system": {"status": "running"},
            "recovery-system": {"status": "running"},
        }

        # Configure mock response from GitLab API with error code
        mock_response = MagicMock()
        mock_response.status_code = 500  # Error
        mock_get.return_value = mock_response

        # Call the method being tested
        result = self.recovery_system._verify_system_integrity(services_status)

        # Verify the result
        self.assertFalse(result)

    @patch("evodev.recovery.subprocess.run")
    def test_create_backup_success(self, mock_run):
        """Test successful backup creation"""
        # Configure mock subprocess.run to return success
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Backup created successfully"
        mock_run.return_value = mock_process

        # Call the method being tested
        with patch("evodev.recovery.datetime.datetime") as mock_datetime:
            # Configure mock datetime
            mock_datetime.now.return_value = datetime.datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.strftime = datetime.datetime.strftime

            result = self.recovery_system.create_backup()

            # Verify that subprocess.run was called with the correct command
            expected_backup_file = os.path.join(
                self.recovery_system.backup_dir, "system_backup_20230101_120000.tar.gz"
            )
            mock_run.assert_called_once_with(
                f"/app/scripts/create_backup.sh {expected_backup_file}",
                shell=True,
                capture_output=True,
                text=True,
            )

            # Verify the result
            self.assertTrue(result)

    @patch("evodev.recovery.subprocess.run")
    def test_create_backup_failure(self, mock_run):
        """Test backup creation failure"""
        # Configure mock subprocess.run to return failure
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Error creating backup"
        mock_run.return_value = mock_process

        # Call the method being tested
        with patch("evodev.recovery.datetime.datetime") as mock_datetime:
            # Configure mock datetime
            mock_datetime.now.return_value = datetime.datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.strftime = datetime.datetime.strftime

            result = self.recovery_system.create_backup()

            # Verify the result
            self.assertFalse(result)

    @patch("evodev.recovery.subprocess.run")
    @patch("evodev.recovery.os.listdir")
    def test_restore_system_with_specific_file(self, mock_listdir, mock_run):
        """Test system restoration with a specific backup file"""
        # Configure mock subprocess.run to return success
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "System restored successfully"
        mock_run.return_value = mock_process

        # Specify a backup file
        backup_file = "/backups/specific_backup.tar.gz"

        # Call the method being tested
        result = self.recovery_system.restore_system(backup_file)

        # Verify that subprocess.run was called with the correct command
        mock_run.assert_called_once_with(
            f"/app/scripts/restore_system.sh {backup_file}",
            shell=True,
            capture_output=True,
            text=True,
        )

        # Verify the result
        self.assertTrue(result)

        # listdir should not be called if a specific file is provided
        mock_listdir.assert_not_called()

    @patch("evodev.recovery.subprocess.run")
    @patch("evodev.recovery.os.listdir")
    def test_restore_system_with_latest_backup(self, mock_listdir, mock_run):
        """Test system restoration with the latest backup file"""
        # Configure mock subprocess.run to return success
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "System restored successfully"
        mock_run.return_value = mock_process

        # Configure mock os.listdir to return backup files
        mock_listdir.return_value = [
            "system_backup_20230101_120000.tar.gz",
            "system_backup_20230102_120000.tar.gz",  # This is the latest
            "system_state_20230101_120000.json",  # This should be ignored
        ]

        # Call the method being tested without specifying a backup file
        result = self.recovery_system.restore_system()

        # Verify that subprocess.run was called with the correct command (latest backup)
        expected_backup_file = os.path.join(
            self.recovery_system.backup_dir, "system_backup_20230102_120000.tar.gz"
        )
        mock_run.assert_called_once_with(
            f"/app/scripts/restore_system.sh {expected_backup_file}",
            shell=True,
            capture_output=True,
            text=True,
        )

        # Verify the result
        self.assertTrue(result)

    @patch("evodev.recovery.os.listdir")
    def test_restore_system_no_backups_available(self, mock_listdir):
        """Test system restoration when no backup files are available"""
        # Configure mock os.listdir to return no backup files
        mock_listdir.return_value = []

        # Call the method being tested without specifying a backup file
        result = self.recovery_system.restore_system()

        # Verify the result
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
