"""Unit tests for LibraryInstaller batch installation operations."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from ams_compose.core.installer import LibraryInstaller, InstallationError
from ams_compose.core.config import AnalogHubConfig, ImportSpec, LockEntry


class TestBatchInstaller:
    """Test LibraryInstaller batch installation methods."""
    
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
    
    @patch('analog_hub.core.installer.LibraryInstaller.install_library')
    def test_install_all_success(self, mock_install_library, installer, sample_config):
        """Test successful installation of all libraries."""
        # Mock successful installations
        mock_install_library.side_effect = [
            LockEntry(
                repo="https://github.com/example/test-repo",
                ref="main",
                commit="abc123",
                source_path="lib/test",
                local_path="designs/libs/test_library",
                checksum="checksum1",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00"
            ),
            LockEntry(
                repo="https://github.com/example/another-repo",
                ref="v1.0.0",
                commit="def456",
                source_path="src",
                local_path="custom/path",
                checksum="checksum2",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00"
            )
        ]
        
        # Install all libraries
        result = installer.install_all()
        
        # Verify all libraries were installed
        assert len(result) == 2
        assert "test_library" in result
        assert "another_lib" in result
        
        # Verify install_library was called for each library
        assert mock_install_library.call_count == 2
        
        # Verify lock entries
        assert result["test_library"].repo == "https://github.com/example/test-repo"
        assert result["another_lib"].repo == "https://github.com/example/another-repo"
        assert result["another_lib"].local_path == "custom/path"
    
    @patch('analog_hub.core.installer.LibraryInstaller.install_library')
    def test_install_all_specific_libraries(self, mock_install_library, installer, sample_config):
        """Test installation of specific libraries only."""
        # Mock successful installation
        mock_install_library.return_value = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="abc123",
            source_path="lib/test",
            local_path="designs/libs/test_library",
            checksum="checksum1",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )
        
        # Install specific library
        result = installer.install_all(library_names=["test_library"])
        
        # Verify only specified library was installed
        assert len(result) == 1
        assert "test_library" in result
        assert "another_lib" not in result
        
        # Verify install_library was called once
        mock_install_library.assert_called_once()
    
    def test_install_all_missing_library(self, installer, sample_config):
        """Test installation when specified library doesn't exist in config."""
        with pytest.raises(InstallationError, match=r"Libraries not found in configuration: \{'nonexistent'\}"):
            installer.install_all(library_names=["nonexistent"])
    
    @patch('analog_hub.core.installer.LibraryInstaller.install_library')
    def test_install_all_partial_failure(self, mock_install_library, installer, sample_config):
        """Test installation when some libraries fail."""
        # Mock mixed success/failure
        mock_install_library.side_effect = [
            LockEntry(
                repo="https://github.com/example/test-repo",
                ref="main",
                commit="abc123",
                source_path="lib/test",
                local_path="designs/libs/test_library",
                checksum="checksum1",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00"
            ),
            Exception("Installation failed for another_lib")
        ]
        
        # Installation should raise error on first failure
        with pytest.raises(Exception, match="Installation failed for another_lib"):
            installer.install_all()