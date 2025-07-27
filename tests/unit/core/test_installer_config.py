"""Unit tests for LibraryInstaller configuration and lockfile operations."""

import pytest
import tempfile
import shutil
from pathlib import Path

from analog_hub.core.installer import LibraryInstaller, InstallationError
from analog_hub.core.config import AnalogHubConfig, ImportSpec, LockFile, LockEntry


class TestInstallerConfig:
    """Test LibraryInstaller configuration and lockfile methods."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def installer(self, temp_project):
        """Create LibraryInstaller instance."""
        return LibraryInstaller(
            project_root=temp_project,
            mirror_root=temp_project / ".mirror"
        )
    
    @pytest.fixture
    def sample_config(self, temp_project):
        """Create sample analog-hub.yaml configuration."""
        config = AnalogHubConfig()
        config.library_root = "designs/libs"
        config.imports = {
            "test_library": ImportSpec(
                repo="https://github.com/example/test-repo",
                ref="main",
                source_path="lib/test"
            ),
            "another_lib": ImportSpec(
                repo="https://github.com/example/another-repo", 
                ref="v1.0.0",
                source_path="src",
                local_path="custom/path"
            )
        }
        
        # Save config to file
        config_path = temp_project / "analog-hub.yaml"
        config.to_yaml(config_path)
        
        return config
    
    def test_load_config_success(self, installer, sample_config):
        """Test successful config loading."""
        config = installer.load_config()
        assert config.library_root == "designs/libs"
        assert "test_library" in config.imports
        assert "another_lib" in config.imports
        assert config.imports["test_library"].repo == "https://github.com/example/test-repo"
    
    def test_load_config_missing_file(self, installer):
        """Test loading config when file doesn't exist."""
        with pytest.raises(InstallationError, match="Configuration file not found"):
            installer.load_config()
    
    def test_load_config_invalid_yaml(self, installer, temp_project):
        """Test loading invalid YAML config."""
        config_path = temp_project / "analog-hub.yaml"
        config_path.write_text("invalid: yaml: content: [")
        
        with pytest.raises(InstallationError, match="Failed to load configuration"):
            installer.load_config()
    
    def test_load_lock_file_new(self, installer, sample_config):
        """Test loading lockfile when none exists."""
        config = installer.load_config()
        lock_file = installer.load_lock_file(config)
        
        assert lock_file.library_root == "designs/libs"
        assert lock_file.entries == {}
    
    def test_load_lock_file_existing(self, installer, temp_project):
        """Test loading existing lockfile."""
        # Create existing lockfile
        lock_data = LockFile(
            library_root="designs/libs",
            entries={
                "test_lib": LockEntry(
                    repo_url="https://github.com/example/test-repo",
                    ref="main",
                    resolved_commit="abc123",
                    source_path="lib/test",
                    local_path="designs/libs/test_lib",
                    checksum="checksum123",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".analog-hub.lock"
        lock_data.to_yaml(lock_path)
        
        # Create minimal config
        config = AnalogHubConfig()
        config.library_root = "designs/libs"
        
        # Load lockfile
        loaded_lock = installer.load_lock_file(config)
        
        assert loaded_lock.library_root == "designs/libs"
        assert "test_lib" in loaded_lock.entries
        assert loaded_lock.entries["test_lib"].repo_url == "https://github.com/example/test-repo"
        assert loaded_lock.entries["test_lib"].resolved_commit == "abc123"
    
    def test_save_lock_file(self, installer, temp_project):
        """Test saving lockfile."""
        lock_data = LockFile(
            library_root="designs/libs",
            entries={
                "test_lib": LockEntry(
                    repo_url="https://github.com/example/test-repo",
                    ref="main",
                    resolved_commit="abc123",
                    source_path="lib/test",
                    local_path="designs/libs/test_lib",
                    checksum="checksum123",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        installer.save_lock_file(lock_data)
        
        # Verify file was created
        lock_path = temp_project / ".analog-hub.lock"
        assert lock_path.exists()
        
        # Verify content can be loaded back
        loaded_lock = LockFile.from_yaml(lock_path)
        assert loaded_lock.library_root == "designs/libs"
        assert "test_lib" in loaded_lock.entries
        assert loaded_lock.entries["test_lib"].resolved_commit == "abc123"