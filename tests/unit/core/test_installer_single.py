"""Unit tests for LibraryInstaller single library operations."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from ams_compose.core.installer import LibraryInstaller, InstallationError
from ams_compose.core.config import AnalogHubConfig, ImportSpec, LockEntry
from ams_compose.core.extractor import ExtractionState
from ams_compose.core.mirror import MirrorState


class TestSingleLibraryInstaller:
    """Test LibraryInstaller single library installation methods."""
    
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
            )
        }
        
        # Save config to file
        config_path = temp_project / "analog-hub.yaml"
        config.to_yaml(config_path)
        
        return config
    
    @patch('analog_hub.core.installer.ChecksumCalculator')
    @patch('analog_hub.core.installer.RepositoryMirror')
    @patch('analog_hub.core.installer.PathExtractor')
    def test_install_library_success(self, mock_extractor_class, mock_mirror_class, mock_checksum_class, installer, sample_config):
        """Test successful single library installation."""
        # Mock ChecksumCalculator
        mock_checksum_class.generate_repo_hash.return_value = "hash123"
        
        # Mock mirror manager
        mock_mirror = Mock()
        mock_mirror_class.return_value = mock_mirror
        mock_mirror_path = Path("/test/mirror/path")
        
        # Mock mirror state with resolved commit
        mock_mirror_state = MirrorState(resolved_commit="abc123def456")
        mock_mirror.update_mirror.return_value = mock_mirror_state
        mock_mirror.get_mirror_path.return_value = mock_mirror_path
        
        # Mock path extractor
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extraction_state = ExtractionState(
            local_path="designs/libs/test_library",
            checksum="checksum123"
        )
        mock_extractor.extract_library.return_value = mock_extraction_state
        
        # Re-initialize installer to use mocks
        installer.mirror_manager = mock_mirror
        installer.path_extractor = mock_extractor
        
        # Test installation
        import_spec = sample_config.imports["test_library"]
        lock_entry = installer.install_library("test_library", import_spec, "designs/libs")
        
        # Verify mock calls
        mock_mirror.update_mirror.assert_called_once_with(
            "https://github.com/example/test-repo", 
            "main"
        )
        mock_extractor.extract_library.assert_called_once_with(
            library_name="test_library",
            import_spec=import_spec,
            mirror_path=mock_mirror_path,
            library_root="designs/libs",
            repo_hash="hash123",
            resolved_commit="abc123def456"
        )
        
        # Verify returned LockEntry
        assert isinstance(lock_entry, LockEntry)
        assert lock_entry.repo == "https://github.com/example/test-repo"
        assert lock_entry.ref == "main"
        assert lock_entry.commit == "abc123def456"
        assert lock_entry.source_path == "lib/test"
        assert lock_entry.local_path == "designs/libs/test_library"
        assert lock_entry.checksum == "checksum123"
        assert lock_entry.installed_at is not None
        assert lock_entry.updated_at is not None
    
    @patch('analog_hub.core.installer.RepositoryMirror')
    def test_install_library_mirror_failure(self, mock_mirror_class, installer, sample_config):
        """Test library installation when mirror operation fails."""
        # Mock mirror manager to raise exception
        mock_mirror = Mock()
        mock_mirror_class.return_value = mock_mirror
        mock_mirror.update_mirror.side_effect = Exception("Git operation failed")
        
        # Re-initialize installer to use mock
        installer.mirror_manager = mock_mirror
        
        # Test installation failure
        import_spec = sample_config.imports["test_library"]
        with pytest.raises(InstallationError, match="Failed to install library 'test_library'"):
            installer.install_library("test_library", import_spec, "designs/libs")