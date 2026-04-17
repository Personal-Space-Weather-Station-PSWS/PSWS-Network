"""
Pytest configuration and shared fixtures for watch9 tests
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path so we can import scripts
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_watch_directory():
    """Create a temporary directory structure for watchdog testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a station directory
        station = tmpdir_path / "S123"
        station.mkdir()

        # Create subdirectories for different upload types
        (station / "csvData").mkdir()
        (station / "magData").mkdir()

        yield station


@pytest.fixture
def mock_watchlog(monkeypatch):
    """Mock the writeLog function to capture log messages"""
    messages = []

    def capture_log(msg):
        messages.append(msg)
        print(f"LOG: {msg}")

    monkeypatch.setattr("scripts.watchers.psws_watch9.writeLog", capture_log)
    return messages


@pytest.fixture
def grape_legacy_upload_dir(temp_watch_directory):
    """Create a Grape 1 Legacy upload directory structure"""
    obs_dir = temp_watch_directory / "csvData" / "g12345"
    obs_dir.mkdir(parents=True, exist_ok=True)

    # Create some test data files
    (obs_dir / "data1.csv").write_text("test,data,1")
    (obs_dir / "data2.csv").write_text("test,data,2")

    # Create nested subdirectory with file
    nested = obs_dir / "nested" / "subdir"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "nested_data.csv").write_text("nested,data")

    return obs_dir


@pytest.fixture
def continuous_drf_upload_dir(temp_watch_directory):
    """Create a Continuous DRF upload directory structure"""
    obs_dir = temp_watch_directory / "c12345"
    obs_dir.mkdir(parents=True, exist_ok=True)

    # Create channel structure
    ch0 = obs_dir / "ch0"
    ch0.mkdir()

    # Create metadata directory and h5 files
    metadata_dir = ch0 / "metadata"
    metadata_dir.mkdir()
    (metadata_dir / "dmd_properties.h5").write_text("mock h5 file")
    (ch0 / "drf_properties.h5").write_text("mock h5 file")

    # Create some data files
    (ch0 / "data_file.drf").write_text("drf data")

    return obs_dir


@pytest.fixture
def magnetometer_upload_dir(temp_watch_directory):
    """Create a Magnetometer upload directory structure"""
    mag_dir = temp_watch_directory / "magData"
    mag_dir.mkdir(parents=True, exist_ok=True)

    # Create some magnetometer data files (zip files)
    (mag_dir / "OBS2024-01-01T00:00.zip").write_text("mock zip data")
    (mag_dir / "OBS2024-01-02T00:00.zip").write_text("mock zip data")

    # Create nested directory structure
    nested = mag_dir / "archives" / "2024"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "january.zip").write_text("mock zip data")

    return mag_dir
