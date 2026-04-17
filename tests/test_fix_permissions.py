"""
Unit tests for fix_permissions function in psws_watch9.py
"""

import pytest
import subprocess
import os
import stat
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the function to test
from scripts.watchers.psws_watch9 import fix_permissions


class TestFixPermissionsUnit:
    """Unit tests for the fix_permissions function"""

    @patch("scripts.watchers.psws_watch9.subprocess.run")
    @patch("scripts.watchers.psws_watch9.writeLog")
    def test_fix_permissions_success(self, mock_log, mock_run):
        """Test successful permission change"""
        path = "/test/path/data"

        fix_permissions(path)

        # Verify chmod was called with correct arguments
        mock_run.assert_called_once_with(["chmod", "-R", "755", path], check=True)

        # Verify success was logged
        mock_log.assert_called_once()
        assert "Successfully applied 755 permissions" in str(mock_log.call_args)

    @patch("scripts.watchers.psws_watch9.subprocess.run")
    @patch("scripts.watchers.psws_watch9.writeLog")
    def test_fix_permissions_subprocess_error(self, mock_log, mock_run):
        """Test handling when chmod command fails"""
        path = "/restricted/path"
        error = subprocess.CalledProcessError(1, "chmod")
        mock_run.side_effect = error

        # Should not raise an exception
        fix_permissions(path)

        # Verify error was logged
        mock_log.assert_called_once()
        assert "ERROR" in str(mock_log.call_args)
        assert "failed to set permissions" in str(mock_log.call_args)

    @patch("scripts.watchers.psws_watch9.subprocess.run")
    @patch("scripts.watchers.psws_watch9.writeLog")
    def test_fix_permissions_permission_denied(self, mock_log, mock_run):
        """Test handling when permission is denied"""
        path = "/denied/path"
        error = subprocess.CalledProcessError(1, "chmod", stderr="Permission denied")
        mock_run.side_effect = error

        fix_permissions(path)

        # Verify error was logged
        mock_log.assert_called_once()
        assert "ERROR" in str(mock_log.call_args)

    @patch("scripts.watchers.psws_watch9.subprocess.run")
    @patch("scripts.watchers.psws_watch9.writeLog")
    def test_fix_permissions_nonexistent_path(self, mock_log, mock_run):
        """Test handling when path does not exist"""
        path = "/nonexistent/path/that/does/not/exist"
        error = subprocess.CalledProcessError(
            1, "chmod", stderr="No such file or directory"
        )
        mock_run.side_effect = error

        fix_permissions(path)

        # Verify error was logged
        mock_log.assert_called_once()
        assert "ERROR" in str(mock_log.call_args)
        assert path in str(mock_log.call_args)


class TestFixPermissionsIntegration:
    """Integration tests with real filesystem"""

    def test_fix_permissions_recursive_real_filesystem(
        self, grape_legacy_upload_dir, mock_watchlog
    ):
        """Test that permissions are actually applied recursively on real files"""
        # Apply permissions
        fix_permissions(str(grape_legacy_upload_dir))

        # Verify all files and directories have 755 permissions
        for dirpath, dirnames, filenames in os.walk(str(grape_legacy_upload_dir)):
            # Check directory permissions
            dir_perms = oct(os.stat(dirpath).st_mode)[-3:]
            assert dir_perms == "755", (
                f"Directory {dirpath} has perms {dir_perms}, expected 755"
            )

            # Check file permissions
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                file_perms = oct(os.stat(filepath).st_mode)[-3:]
                assert file_perms == "755", (
                    f"File {filepath} has perms {file_perms}, expected 755"
                )

        # Verify success was logged
        assert any(
            "Successfully applied 755 permissions" in msg for msg in mock_watchlog
        )

    def test_fix_permissions_on_nonexistent_path(self, mock_watchlog):
        """Test error handling when path doesn't exist"""
        nonexistent = "/tmp/path_that_definitely_does_not_exist_12345678"

        fix_permissions(nonexistent)

        # Verify error was logged
        assert any("ERROR" in msg for msg in mock_watchlog)

    def test_fix_permissions_continuous_drf_structure(
        self, continuous_drf_upload_dir, mock_watchlog
    ):
        """Test permissions on DRF directory structure with h5 files"""
        fix_permissions(str(continuous_drf_upload_dir))

        # Verify all files have correct permissions
        for dirpath, dirnames, filenames in os.walk(str(continuous_drf_upload_dir)):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                file_perms = oct(os.stat(filepath).st_mode)[-3:]
                assert file_perms == "755", f"File {filepath} has incorrect permissions"

        # Verify metadata files are accessible
        metadata_file = (
            continuous_drf_upload_dir / "ch0" / "metadata" / "dmd_properties.h5"
        )
        assert metadata_file.exists()
        assert stat.S_IMODE(os.stat(metadata_file).st_mode) == 0o755

    def test_fix_permissions_magnetometer_nested_structure(
        self, magnetometer_upload_dir, mock_watchlog
    ):
        """Test permissions on deeply nested magnetometer directory structure"""
        fix_permissions(str(magnetometer_upload_dir))

        # Verify all nested directories and files have correct permissions
        for dirpath, dirnames, filenames in os.walk(str(magnetometer_upload_dir)):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                file_perms = oct(os.stat(filepath).st_mode)[-3:]
                assert file_perms == "755"

        # Specifically check the deeply nested file
        deeply_nested = magnetometer_upload_dir / "archives" / "2024" / "january.zip"
        assert deeply_nested.exists()
        assert stat.S_IMODE(os.stat(deeply_nested).st_mode) == 0o755

    def test_fix_permissions_with_existing_files(
        self, temp_watch_directory, mock_watchlog
    ):
        """Test permissions are updated on existing files with different permissions"""
        test_dir = temp_watch_directory / "test_perms"
        test_dir.mkdir()

        # Create files with different permissions
        file1 = test_dir / "file1.txt"
        file1.write_text("test")
        os.chmod(file1, 0o644)  # rw-r--r--

        file2 = test_dir / "file2.txt"
        file2.write_text("test")
        os.chmod(file2, 0o600)  # rw-------

        subdir = test_dir / "subdir"
        subdir.mkdir()
        os.chmod(subdir, 0o700)  # rwx------

        # Apply permissions
        fix_permissions(str(test_dir))

        # Verify all now have 755
        assert stat.S_IMODE(os.stat(file1).st_mode) == 0o755
        assert stat.S_IMODE(os.stat(file2).st_mode) == 0o755
        assert stat.S_IMODE(os.stat(subdir).st_mode) == 0o755
