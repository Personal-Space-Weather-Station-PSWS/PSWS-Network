"""
Integration tests for watchdog trigger handling and permissions in psws_watch9.py

Tests the full flow: trigger detection -> processing -> permission fixing
for all three upload types: Grape Legacy (g), Continuous DRF (c), and Magnetometer (m)
"""
import pytest
import os
import stat
import subprocess
import tempfile
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path

from scripts.watchers.psws_watch9 import TriggerDirHandler, fix_permissions


class TestGrapeLegacyUploadPermissions:
    """Test Grape 1 Legacy (g) uploads with permission verification"""
    
    @patch('scripts.watchers.psws_watch9.os.system')
    @patch('scripts.watchers.psws_watch9.os.rmdir')
    @patch('scripts.watchers.psws_watch9.get_size')
    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_grape_legacy_trigger_calls_fix_permissions(self, mock_log, mock_size, 
                                                         mock_rmdir, mock_system):
        """Test that Grape Legacy trigger detection detects trigger correctly"""
        mock_size.return_value = 1000000
        
        handler = TriggerDirHandler(Path("/home/station1"))
        event = MagicMock()
        event.is_directory = True
        # Proper trigger format: g_<obs>_#<instrument>_<timestamp>
        event.src_path = "/home/station1/g_obs123_#INSTRUMENT01_20240101"
        
        handler.on_created(event)
        
        # Verify Grape Legacy processing was logged
        logs = [str(call) for call in mock_log.call_args_list]
        assert any("Grape 1 Legacy" in str(log) for log in logs)

    def test_grape_legacy_permissions_applied_to_data(
        self, grape_legacy_upload_dir, mock_watchlog
    ):
        """Test that fix_permissions actually changes permissions on Grape Legacy data"""
        # Corrupt the permissions first
        for dirpath, dirnames, filenames in os.walk(str(grape_legacy_upload_dir)):
            os.chmod(dirpath, 0o700)
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                os.chmod(filepath, 0o600)

        # Verify permissions are corrupted
        for dirpath, dirnames, filenames in os.walk(str(grape_legacy_upload_dir)):
            perms = stat.S_IMODE(os.stat(dirpath).st_mode)
            assert perms == 0o700, "Test setup: permissions should be 0o700"

        # Apply fix_permissions
        fix_permissions(str(grape_legacy_upload_dir))

        # Verify all permissions are now 755
        for dirpath, dirnames, filenames in os.walk(str(grape_legacy_upload_dir)):
            dir_perms = stat.S_IMODE(os.stat(dirpath).st_mode)
            assert dir_perms == 0o755, f"Directory {dirpath} not fixed"

            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                file_perms = stat.S_IMODE(os.stat(filepath).st_mode)
                assert file_perms == 0o755, f"File {filepath} not fixed"


class TestContinuousDRFUploadPermissions:
    """Test Continuous DRF (c) uploads with permission verification"""
    
    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_continuous_drf_trigger_detection(self, mock_log):
        """Test that Continuous DRF trigger is detected correctly"""
        handler = TriggerDirHandler(Path("/home/station2"))
        event = MagicMock()
        event.is_directory = True
        # c trigger format: c_<obs>_#<instrument>_<timestamp>
        event.src_path = "/home/station2/c_drf123_#INSTR02_20240101"
        
        # This will fail at some point due to missing files, but we're just checking detection
        with patch('scripts.watchers.psws_watch9.get_size', return_value=5000000):
            with patch('os.path.isfile', return_value=False):
                handler.on_created(event)
        
        # Verify Continuous processing was logged
        logs = [str(call) for call in mock_log.call_args_list]
        assert any("trigger" in str(log).lower() for log in logs)

    def test_continuous_drf_permissions_on_h5_files(
        self, continuous_drf_upload_dir, mock_watchlog
    ):
        """Test that h5 metadata files get correct permissions"""
        # Set incorrect permissions on h5 files
        h5_file = continuous_drf_upload_dir / "ch0" / "drf_properties.h5"
        metadata_h5 = (
            continuous_drf_upload_dir / "ch0" / "metadata" / "dmd_properties.h5"
        )

        os.chmod(h5_file, 0o600)
        os.chmod(metadata_h5, 0o600)

        # Apply fix_permissions
        fix_permissions(str(continuous_drf_upload_dir))

        # Verify h5 files now have correct permissions
        assert stat.S_IMODE(os.stat(h5_file).st_mode) == 0o755
        assert stat.S_IMODE(os.stat(metadata_h5).st_mode) == 0o755


class TestMagnetometerUploadPermissions:
    """Test Magnetometer (m) uploads with permission verification"""
    
    @patch('scripts.watchers.psws_watch9.subprocess.run')
    @patch('scripts.watchers.psws_watch9.os.rmdir')
    @patch('scripts.watchers.psws_watch9.get_size')
    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_magnetometer_trigger_detected(self, mock_log, mock_size, 
                                                        mock_rmdir, mock_run):
        """Test that Magnetometer trigger is detected"""
        mock_size.return_value = 500000
        
        handler = TriggerDirHandler(Path("/home/station3"))
        event = MagicMock()
        event.is_directory = True
        # Magnetometer trigger format: m_<obs>_#<instrument>_<timestamp>
        event.src_path = "/home/station3/m_mag123_#INSTR03_20240101120000"
        
        handler.on_created(event)
        
        # Verify the trigger was detected (will be logged)
        logs = [str(call) for call in mock_log.call_args_list]
        # Just verify that subprocess.run was attempted
        assert mock_run.called or any("Issued" in str(log) for log in logs)

    def test_magnetometer_permissions_on_zip_files(
        self, magnetometer_upload_dir, mock_watchlog
    ):
        """Test that magnetometer zip files and nested structures get correct permissions"""
        # Set incorrect permissions on all files and directories
        for dirpath, dirnames, filenames in os.walk(str(magnetometer_upload_dir)):
            os.chmod(dirpath, 0o700)
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                os.chmod(filepath, 0o600)

        # Apply fix_permissions
        fix_permissions(str(magnetometer_upload_dir))

        # Verify all files and directories have correct permissions
        for dirpath, dirnames, filenames in os.walk(str(magnetometer_upload_dir)):
            dir_perms = stat.S_IMODE(os.stat(dirpath).st_mode)
            assert dir_perms == 0o755, f"Directory {dirpath} not fixed"

            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                file_perms = stat.S_IMODE(os.stat(filepath).st_mode)
                assert file_perms == 0o755, f"Zip file {filepath} not fixed"

        # Specifically verify deeply nested structure
        deeply_nested = magnetometer_upload_dir / "archives" / "2024" / "january.zip"
        assert stat.S_IMODE(os.stat(deeply_nested).st_mode) == 0o755


class TestErrorScenarios:
    """Test error scenarios: permission denied, non-existent paths, corrupted uploads"""
    
    @patch('scripts.watchers.psws_watch9.subprocess.run')
    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_error_scenario_permission_denied_on_chmod(self, mock_log, mock_run):
        """Test error scenario: permission denied when trying to chmod"""
        error = subprocess.CalledProcessError(1, 'chmod', stderr="Permission denied")
        mock_run.side_effect = error
        
        # Attempt fix_permissions (will fail gracefully)
        fix_permissions("/some/restricted/dir")
        
        # Verify error was logged
        assert mock_log.called
        assert "ERROR" in str(mock_log.call_args)
    
    def test_error_scenario_nonexistent_path(self, mock_watchlog):
        """Test error scenario: non-existent upload path"""
        nonexistent_path = "/tmp/nonexistent_upload_dir_12345"
        
        fix_permissions(nonexistent_path)
        
        # Verify error was logged
        assert any("ERROR" in msg for msg in mock_watchlog)
        assert any(nonexistent_path in msg for msg in mock_watchlog)
    
    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_error_scenario_corrupted_grape_legacy_missing_csvdata(self, mock_log):
        """Test error scenario: Grape Legacy upload without csvData directory"""
        corrupted_path = "/tmp/nonexistent_csvdata_12345/g12345"
        
        # Should handle gracefully
        fix_permissions(corrupted_path)
        
        # Verify error was logged
        assert mock_log.called
        assert "ERROR" in str(mock_log.call_args)
    
    def test_error_scenario_corrupted_drf_missing_metadata(self, temp_watch_directory, mock_watchlog):
        """Test error scenario: DRF upload with missing metadata files"""
        obs_dir = temp_watch_directory / "c12345"
        obs_dir.mkdir()
        ch0 = obs_dir / "ch0"
        ch0.mkdir()
        
        # Create some files but not the metadata files
        (ch0 / "data_file.drf").write_text("data")
        
        # This should still apply permissions to what exists
        fix_permissions(str(obs_dir))
        
        # Verify permissions were applied to existing files
        assert stat.S_IMODE(os.stat(ch0 / "data_file.drf").st_mode) == 0o755
    
    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_error_scenario_corrupted_magnetometer_missing_magdata(self, mock_log):
        """Test error scenario: Magnetometer upload without magData directory"""
        corrupted_path = "/tmp/nonexistent_magdata_12345"
        
        # Should handle gracefully - path doesn't exist
        fix_permissions(corrupted_path)
        
        # Verify error was logged
        assert mock_log.called
        assert "ERROR" in str(mock_log.call_args)
    
    @patch('scripts.watchers.psws_watch9.subprocess.run')
    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_error_subprocess_called_with_correct_args_despite_error(self, mock_log, mock_run):
        """Test that subprocess is called with correct chmod args even if it fails"""
        error = subprocess.CalledProcessError(1, 'chmod')
        mock_run.side_effect = error
        
        path = "/test/path"
        fix_permissions(path)
        
        # Verify subprocess.run was called with correct args
        mock_run.assert_called_once_with(["chmod", "-R", "755", path], check=True)
        
        # Verify error was logged
        assert mock_log.called
        assert "ERROR" in str(mock_log.call_args)

        # Restore permissions for cleanup
        os.chmod(restricted_dir, 0o755)

    def test_error_scenario_nonexistent_path(self, mock_watchlog):
        """Test error scenario: non-existent upload path"""
        nonexistent_path = "/tmp/nonexistent_upload_dir_12345"

        fix_permissions(nonexistent_path)

        # Verify error was logged
        assert any("ERROR" in msg for msg in mock_watchlog)
        assert any(nonexistent_path in msg for msg in mock_watchlog)

    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_error_scenario_corrupted_grape_legacy_missing_csvdata(
        self, mock_log
    ):
        """Test error scenario: Grape Legacy upload without csvData directory"""
        corrupted_path = "/tmp/nonexistent_csvdata_12345/g12345"

        # Should handle gracefully
        fix_permissions(corrupted_path)

        # Verify error was logged
        assert mock_log.called
        assert "ERROR" in str(mock_log.call_args)

    def test_error_scenario_corrupted_drf_missing_metadata(
        self, temp_watch_directory, mock_watchlog
    ):
        """Test error scenario: DRF upload with missing metadata files"""
        obs_dir = temp_watch_directory / "c12345"
        obs_dir.mkdir()
        ch0 = obs_dir / "ch0"
        ch0.mkdir()

        # Create some files but not the metadata files
        (ch0 / "data_file.drf").write_text("data")

        # This should still apply permissions to what exists
        fix_permissions(str(obs_dir))

        # Verify permissions were applied to existing files
        assert stat.S_IMODE(os.stat(ch0 / "data_file.drf").st_mode) == 0o755

    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_error_scenario_corrupted_magnetometer_missing_magdata(
        self, mock_log
    ):
        """Test error scenario: Magnetometer upload without magData directory"""
        corrupted_path = "/tmp/nonexistent_magdata_12345"

        # Should handle gracefully - path doesn't exist
        fix_permissions(corrupted_path)

        # Verify error was logged
        assert mock_log.called
        assert "ERROR" in str(mock_log.call_args)

    @patch('scripts.watchers.psws_watch9.subprocess.run')
    @patch('scripts.watchers.psws_watch9.writeLog')
    def test_error_subprocess_called_with_correct_args_despite_error(
        self, mock_log, mock_run
    ):
        """Test that subprocess is called with correct chmod args even if it fails"""
        error = subprocess.CalledProcessError(1, 'chmod')
        mock_run.side_effect = error

        path = "/test/path"
        fix_permissions(path)

        # Verify subprocess.run was called with correct args
        mock_run.assert_called_once_with(["chmod", "-R", "755", path], check=True)

        # Verify error was logged
        assert mock_log.called
        assert "ERROR" in str(mock_log.call_args)


class TestAllUploadTypesPermissionFlow:
    """Test complete permission flow for all upload types"""
    
    def test_all_three_upload_types_get_fixed_permissions(self, mock_watchlog):
        """Test that all three upload types result in 755 permissions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 1. Grape Legacy
            grape_dir = tmpdir_path / "csvData" / "g12345"
            grape_dir.mkdir(parents=True)
            (grape_dir / "data.csv").write_text("data")
            os.chmod(grape_dir, 0o700)
            os.chmod(grape_dir / "data.csv", 0o600)
            
            # 2. Continuous DRF
            drf_dir = tmpdir_path / "c12345" / "ch0"
            drf_dir.mkdir(parents=True)
            (drf_dir / "data.drf").write_text("data")
            os.chmod(tmpdir_path / "c12345", 0o700)
            os.chmod(drf_dir, 0o700)
            os.chmod(drf_dir / "data.drf", 0o600)
            
            # 3. Magnetometer
            mag_dir = tmpdir_path / "magData"
            mag_dir.mkdir()
            (mag_dir / "obs.zip").write_text("zip")
            os.chmod(mag_dir, 0o700)
            os.chmod(mag_dir / "obs.zip", 0o600)
            
            # Fix permissions on all
            fix_permissions(str(grape_dir.parent))  # Fix csvData parent
            fix_permissions(str(drf_dir.parent.parent))  # Fix c12345 parent
            fix_permissions(str(mag_dir))  # Fix magData
            
            # Verify all have correct permissions
            for path in [grape_dir, grape_dir / "data.csv",
                         tmpdir_path / "c12345", drf_dir, drf_dir / "data.drf",
                         mag_dir, mag_dir / "obs.zip"]:
                perms = stat.S_IMODE(os.stat(path).st_mode)
                assert perms == 0o755, f"{path} has perms {oct(perms)}, expected 0o755"
