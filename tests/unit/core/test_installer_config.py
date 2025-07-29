"""Unit tests for LibraryInstaller configuration and lockfile operations."""

import pytest
import tempfile
import shutil
from pathlib import Path

from ams_compose.core.installer import LibraryInstaller, InstallationError
from ams_compose.core.config import AnalogHubConfig, ImportSpec, LockFile, LockEntry


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
        """Create sample ams-compose.yaml configuration."""
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
        config_path = temp_project / "ams-compose.yaml"
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
        config_path = temp_project / "ams-compose.yaml"
        config_path.write_text("invalid: yaml: content: [")
        
        with pytest.raises(InstallationError, match="Failed to load configuration"):
            installer.load_config()
    
    def test_load_lock_file_new(self, installer, sample_config):
        """Test loading lockfile when none exists."""
        lock_file = installer.load_lock_file()
        
        assert lock_file.library_root == "designs/libs"
        assert lock_file.libraries == {}
    
    def test_load_lock_file_existing(self, installer, temp_project):
        """Test loading existing lockfile."""
        # Create existing lockfile
        lock_data = LockFile(
            library_root="designs/libs",
            libraries={
                "test_lib": LockEntry(
                    repo="https://github.com/example/test-repo",
                    ref="main",
                    commit="abc123",
                    source_path="lib/test",
                    local_path="designs/libs/test_lib",
                    checksum="checksum123",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".ams-compose.lock"
        lock_data.to_yaml(lock_path)
        
        # Create minimal config
        config = AnalogHubConfig()
        config.library_root = "designs/libs"
        
        # Load lockfile
        loaded_lock = installer.load_lock_file()
        
        assert loaded_lock.library_root == "designs/libs"
        assert "test_lib" in loaded_lock.libraries
        assert loaded_lock.libraries["test_lib"].repo == "https://github.com/example/test-repo"
        assert loaded_lock.libraries["test_lib"].commit == "abc123"
    
    def test_save_lock_file(self, installer, temp_project):
        """Test saving lockfile."""
        lock_data = LockFile(
            library_root="designs/libs",
            libraries={
                "test_lib": LockEntry(
                    repo="https://github.com/example/test-repo",
                    ref="main",
                    commit="abc123",
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
        lock_path = temp_project / ".ams-compose.lock"
        assert lock_path.exists()
        
        # Verify content can be loaded back
        loaded_lock = LockFile.from_yaml(lock_path)
        assert loaded_lock.library_root == "designs/libs"
        assert "test_lib" in loaded_lock.libraries
        assert loaded_lock.libraries["test_lib"].commit == "abc123"
    
    def test_import_spec_checkin_field_default(self):
        """Test ImportSpec checkin field defaults to True."""
        import_spec = ImportSpec(
            repo="https://github.com/example/test-repo",
            ref="main",
            source_path="lib/test"
        )
        assert import_spec.checkin is True
    
    def test_import_spec_checkin_field_explicit_false(self):
        """Test ImportSpec checkin field can be set to False."""
        import_spec = ImportSpec(
            repo="https://github.com/example/test-repo",
            ref="main",
            source_path="lib/test",
            checkin=False
        )
        assert import_spec.checkin is False
    
    def test_lock_entry_with_checkin_field(self):
        """Test LockEntry includes checkin field."""
        lock_entry = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="abc123",
            source_path="lib/test",
            local_path="designs/libs/test_lib",
            checksum="checksum123",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            checkin=False
        )
        assert lock_entry.checkin is False
    
    def test_config_yaml_serialization_with_checkin(self, temp_project):
        """Test config serialization preserves checkin field."""
        config = AnalogHubConfig()
        config.library_root = "designs/libs"
        config.imports = {
            "stable_lib": ImportSpec(
                repo="https://github.com/example/stable-repo",
                ref="v1.0.0",
                source_path="lib",
                checkin=False
            ),
            "critical_lib": ImportSpec(
                repo="https://github.com/example/critical-repo",
                ref="main",
                source_path="src"
                # checkin defaults to True
            )
        }
        
        # Save and reload config
        config_path = temp_project / "ams-compose.yaml"
        config.to_yaml(config_path)
        
        loaded_config = AnalogHubConfig.from_yaml(config_path)
        
        assert loaded_config.imports["stable_lib"].checkin is False
        assert loaded_config.imports["critical_lib"].checkin is True
    
    def test_installer_propagates_checkin_field_from_import_spec_to_lock_entry(self, installer, temp_project):
        """Test that installer propagates checkin field from ImportSpec to LockEntry."""
        # This test will fail until we implement the functionality
        # Create a minimal config with checkin=False
        config = AnalogHubConfig()
        config.library_root = "designs/libs"
        config.imports = {
            "test_lib": ImportSpec(
                repo="https://github.com/example/test-repo",
                ref="main",
                source_path="lib/test",
                checkin=False
            )
        }
        
        config_path = temp_project / "ams-compose.yaml"
        config.to_yaml(config_path)
        
        # Mock the mirror manager and path extractor to avoid actual git operations
        from unittest.mock import Mock, patch
        with patch.object(installer.mirror_manager, 'update_mirror') as mock_mirror, \
             patch.object(installer.path_extractor, 'extract_library') as mock_extract:
            
            # Set up mock returns
            mock_mirror.return_value = Mock(resolved_commit="abc123")
            mock_extract.return_value = Mock(
                local_path="designs/libs/test_lib",
                checksum="checksum123"
            )
            
            # Call install_library
            lock_entry = installer.install_library(
                library_name="test_lib",
                import_spec=config.imports["test_lib"],
                library_root=config.library_root
            )
            
            # Assert checkin field is propagated
            assert lock_entry.checkin is False