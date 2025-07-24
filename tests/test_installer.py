"""Tests for installation orchestration."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from analog_hub.core.installer import LibraryInstaller, InstallationError
from analog_hub.core.config import AnalogHubConfig, ImportSpec, LockFile, LockEntry
from analog_hub.core.extractor import LibraryMetadata


class TestLibraryInstaller:
    """Test LibraryInstaller class."""
    
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
        
        config_path = temp_project / "analog-hub.yaml"
        config.to_yaml(config_path)
        return config
    
    def test_load_config_success(self, installer, sample_config):
        """Test successful configuration loading."""
        config = installer.load_config()
        
        assert config.library_root == "designs/libs"
        assert len(config.imports) == 2
        assert "test_library" in config.imports
        assert config.imports["test_library"].repo == "https://github.com/example/test-repo"
    
    def test_load_config_missing_file(self, installer):
        """Test configuration loading with missing file."""
        with pytest.raises(InstallationError, match="Configuration file not found"):
            installer.load_config()
    
    def test_load_config_invalid_yaml(self, installer, temp_project):
        """Test configuration loading with invalid YAML."""
        config_path = temp_project / "analog-hub.yaml"
        config_path.write_text("invalid: yaml: content: [")
        
        with pytest.raises(InstallationError, match="Failed to load configuration"):
            installer.load_config()
    
    def test_load_lock_file_new(self, installer, sample_config):
        """Test loading lock file when it doesn't exist."""
        lock_file = installer.load_lock_file()
        
        assert lock_file.version == "1"
        assert lock_file.library_root == "designs/libs"
        assert len(lock_file.libraries) == 0
    
    def test_load_lock_file_existing(self, installer, temp_project):
        """Test loading existing lock file."""
        # Create existing lock file
        lock_file = LockFile(
            library_root="test/libs",
            libraries={
                "test_lib": LockEntry(
                    repo="https://github.com/example/repo",
                    ref="main",
                    commit="abc123",
                    source_path="src",
                    local_path="test/libs/test_lib",
                    checksum="def456",
                    installed_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".analog-hub.lock"
        lock_file.to_yaml(lock_path)
        
        loaded_lock = installer.load_lock_file()
        assert loaded_lock.library_root == "test/libs"
        assert len(loaded_lock.libraries) == 1
        assert "test_lib" in loaded_lock.libraries
    
    def test_save_lock_file(self, installer, temp_project):
        """Test saving lock file."""
        lock_file = LockFile(
            library_root="designs/libs",
            libraries={
                "test_lib": LockEntry(
                    repo="https://github.com/example/repo",
                    ref="main", 
                    commit="abc123",
                    source_path="src",
                    local_path="designs/libs/test_lib",
                    checksum="def456",
                    installed_at="2025-01-01T00:00:00"
                )
            }
        )
        
        installer.save_lock_file(lock_file)
        
        lock_path = temp_project / ".analog-hub.lock"
        assert lock_path.exists()
        
        # Verify content
        loaded_lock = LockFile.from_yaml(lock_path)
        assert loaded_lock.library_root == "designs/libs"
        assert len(loaded_lock.libraries) == 1
    
    @patch('analog_hub.core.mirror.MirrorMetadata')
    @patch('analog_hub.core.installer.RepositoryMirror')
    @patch('analog_hub.core.installer.PathExtractor')
    def test_install_library_success(self, mock_extractor_class, mock_mirror_class, mock_metadata_class, installer, sample_config):
        """Test successful single library installation."""
        # Mock mirror manager
        mock_mirror = Mock()
        mock_mirror_class.return_value = mock_mirror
        mock_mirror_path = Path("/test/mirror/path")
        mock_mirror.mirror_repository.return_value = mock_mirror_path
        
        # Mock mirror metadata
        mock_metadata = Mock()
        mock_metadata_class.from_yaml.return_value = mock_metadata
        mock_metadata.resolved_commit = "abc123def456"
        
        # Mock path extractor
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_library_metadata = LibraryMetadata(
            library_name="test_library",
            repo_url="https://github.com/example/test-repo",
            repo_hash="hash123",
            ref="main",
            resolved_commit="abc123def456",
            source_path="lib/test",
            local_path="designs/libs/test_library",
            checksum="checksum123",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )
        mock_extractor.extract_library.return_value = mock_library_metadata
        
        # Re-initialize installer to use mocks
        installer.mirror_manager = mock_mirror
        installer.path_extractor = mock_extractor
        
        # Test installation
        import_spec = sample_config.imports["test_library"]
        lock_entry = installer.install_library("test_library", import_spec, "designs/libs")
        
        # Verify mock calls
        mock_mirror.mirror_repository.assert_called_once_with(
            "https://github.com/example/test-repo", "main"
        )
        mock_extractor.extract_library.assert_called_once()
        
        # Verify lock entry
        assert lock_entry.repo == "https://github.com/example/test-repo"
        assert lock_entry.ref == "main"
        assert lock_entry.commit == "abc123def456"
        assert lock_entry.source_path == "lib/test"
        assert lock_entry.checksum == "checksum123"
    
    @patch('analog_hub.core.installer.RepositoryMirror')
    def test_install_library_mirror_failure(self, mock_mirror_class, installer, sample_config):
        """Test library installation with mirror failure."""
        # Mock mirror failure
        mock_mirror = Mock()
        mock_mirror_class.return_value = mock_mirror
        mock_mirror.mirror_repository.side_effect = Exception("Mirror failed")
        
        installer.mirror_manager = mock_mirror
        
        import_spec = sample_config.imports["test_library"]
        
        with pytest.raises(InstallationError, match="Failed to install library 'test_library'"):
            installer.install_library("test_library", import_spec, "designs/libs")
    
    @patch('analog_hub.core.installer.LibraryInstaller.install_library')
    def test_install_all_success(self, mock_install_library, installer, sample_config):
        """Test successful installation of all libraries."""
        # Mock individual installations
        mock_lock_entry1 = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="abc123",
            source_path="lib/test",
            local_path="designs/libs/test_library",
            checksum="checksum1",
            installed_at="2025-01-01T00:00:00"
        )
        mock_lock_entry2 = LockEntry(
            repo="https://github.com/example/another-repo",
            ref="v1.0.0", 
            commit="def456",
            source_path="src",
            local_path="custom/path",
            checksum="checksum2",
            installed_at="2025-01-01T00:00:00"
        )
        
        mock_install_library.side_effect = [mock_lock_entry1, mock_lock_entry2]
        
        # Test installation
        installed = installer.install_all()
        
        assert len(installed) == 2
        assert "test_library" in installed
        assert "another_lib" in installed
        assert mock_install_library.call_count == 2
        
        # Verify lock file was saved
        lock_file = installer.load_lock_file()
        assert len(lock_file.libraries) == 2
    
    @patch('analog_hub.core.installer.LibraryInstaller.install_library')
    def test_install_all_specific_libraries(self, mock_install_library, installer, sample_config):
        """Test installation of specific libraries."""
        mock_lock_entry = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="abc123",
            source_path="lib/test", 
            local_path="designs/libs/test_library",
            checksum="checksum1",
            installed_at="2025-01-01T00:00:00"
        )
        
        mock_install_library.return_value = mock_lock_entry
        
        # Test installation of specific library
        installed = installer.install_all(["test_library"])
        
        assert len(installed) == 1
        assert "test_library" in installed
        mock_install_library.assert_called_once()
    
    def test_install_all_missing_library(self, installer, sample_config):
        """Test installation with missing library in configuration."""
        with pytest.raises(InstallationError, match="Libraries not found in configuration"):
            installer.install_all(["nonexistent_library"])
    
    @patch('analog_hub.core.installer.LibraryInstaller.install_library')
    def test_install_all_partial_failure(self, mock_install_library, installer, sample_config):
        """Test installation with some libraries failing."""
        # First library succeeds, second fails
        mock_lock_entry = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="abc123",
            source_path="lib/test",
            local_path="designs/libs/test_library", 
            checksum="checksum1",
            installed_at="2025-01-01T00:00:00"
        )
        
        mock_install_library.side_effect = [
            mock_lock_entry,
            Exception("Installation failed")
        ]
        
        with pytest.raises(InstallationError, match="Failed to install 1 libraries"):
            installer.install_all()
    
    @patch('analog_hub.core.installer.LibraryInstaller.install_library')
    @patch('analog_hub.core.installer.PathExtractor')
    def test_update_library_success(self, mock_extractor_class, mock_install_library, installer, sample_config, temp_project):
        """Test successful library update."""
        # Setup existing lock file
        existing_lock = LockFile(
            library_root="designs/libs",
            libraries={
                "test_library": LockEntry(
                    repo="https://github.com/example/test-repo",
                    ref="main",
                    commit="old123",
                    source_path="lib/test",
                    local_path="designs/libs/test_library",
                    checksum="oldchecksum",
                    installed_at="2025-01-01T00:00:00"
                )
            }
        )
        installer.save_lock_file(existing_lock)
        
        # Mock path extractor for removal
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        installer.path_extractor = mock_extractor
        
        # Mock new installation
        updated_lock_entry = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main", 
            commit="new456",
            source_path="lib/test",
            local_path="designs/libs/test_library",
            checksum="newchecksum",
            installed_at="2025-01-01T01:00:00"
        )
        mock_install_library.return_value = updated_lock_entry
        
        # Test update
        result = installer.update_library("test_library")
        
        # Verify removal and installation
        mock_extractor.remove_library.assert_called_once_with("test_library")
        mock_install_library.assert_called_once()
        
        # Verify result
        assert result.commit == "new456"
        assert result.checksum == "newchecksum"
        
        # Verify lock file updated
        lock_file = installer.load_lock_file()
        assert lock_file.libraries["test_library"].commit == "new456"
    
    def test_update_library_not_in_config(self, installer, sample_config):
        """Test update of library not in configuration."""
        with pytest.raises(InstallationError, match="Library 'nonexistent' not found in configuration"):
            installer.update_library("nonexistent")
    
    def test_update_library_not_installed(self, installer, sample_config):
        """Test update of library not currently installed."""
        with pytest.raises(InstallationError, match="Library 'test_library' is not currently installed"):
            installer.update_library("test_library")
    
    def test_list_installed_libraries(self, installer, temp_project):
        """Test listing installed libraries."""
        # Setup lock file with libraries
        lock_file = LockFile(
            library_root="designs/libs",
            libraries={
                "lib1": LockEntry(
                    repo="https://github.com/example/repo1",
                    ref="main",
                    commit="abc123",
                    source_path="src",
                    local_path="designs/libs/lib1",
                    checksum="checksum1",
                    installed_at="2025-01-01T00:00:00"
                ),
                "lib2": LockEntry(
                    repo="https://github.com/example/repo2", 
                    ref="v1.0.0",
                    commit="def456",
                    source_path="lib",
                    local_path="custom/lib2",
                    checksum="checksum2",
                    installed_at="2025-01-01T01:00:00"
                )
            }
        )
        installer.save_lock_file(lock_file)
        
        # Test listing
        installed = installer.list_installed_libraries()
        
        assert len(installed) == 2
        assert "lib1" in installed
        assert "lib2" in installed
        assert installed["lib1"].commit == "abc123"
        assert installed["lib2"].commit == "def456"
    
    @patch('analog_hub.core.extractor.LibraryMetadata')
    @patch('analog_hub.core.installer.PathExtractor')
    def test_validate_installation_success(self, mock_extractor_class, mock_metadata_class, installer, temp_project):
        """Test successful installation validation."""
        # Setup lock file
        lock_file = LockFile(
            library_root="designs/libs",
            libraries={
                "test_lib": LockEntry(
                    repo="https://github.com/example/repo",
                    ref="main",
                    commit="abc123",
                    source_path="src",
                    local_path="designs/libs/test_lib",
                    checksum="checksum123",
                    installed_at="2025-01-01T00:00:00"
                )
            }
        )
        installer.save_lock_file(lock_file)
        
        # Mock library directory exists
        library_path = temp_project / "designs/libs/test_lib"
        library_path.mkdir(parents=True)
        metadata_path = library_path / ".analog-hub-meta.yaml"
        metadata_path.touch()
        
        # Mock path extractor checksum calculation
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        installer.path_extractor = mock_extractor
        mock_extractor._calculate_directory_checksum.return_value = "checksum123"
        
        # Mock metadata loading
        mock_metadata_class.from_yaml.return_value = Mock()
        
        # Test validation
        valid, invalid = installer.validate_installation()
        
        assert len(valid) == 1
        assert "test_lib" in valid
        assert len(invalid) == 0
    
    def test_validate_installation_missing_directory(self, installer, temp_project):
        """Test validation with missing library directory."""
        # Setup lock file
        lock_file = LockFile(
            library_root="designs/libs", 
            libraries={
                "missing_lib": LockEntry(
                    repo="https://github.com/example/repo",
                    ref="main",
                    commit="abc123",
                    source_path="src",
                    local_path="designs/libs/missing_lib",
                    checksum="checksum123",
                    installed_at="2025-01-01T00:00:00"
                )
            }
        )
        installer.save_lock_file(lock_file)
        
        # Test validation
        valid, invalid = installer.validate_installation()
        
        assert len(valid) == 0
        assert len(invalid) == 1
        assert "missing_lib: library directory not found" in invalid
    
    @patch('analog_hub.core.installer.RepositoryMirror')
    def test_clean_unused_mirrors(self, mock_mirror_class, installer, temp_project):
        """Test cleaning unused mirrors."""
        # Setup lock file with one library
        lock_file = LockFile(
            library_root="designs/libs",
            libraries={
                "active_lib": LockEntry(
                    repo="https://github.com/example/active-repo",
                    ref="main",
                    commit="abc123", 
                    source_path="src",
                    local_path="designs/libs/active_lib",
                    checksum="checksum123",
                    installed_at="2025-01-01T00:00:00"
                )
            }
        )
        installer.save_lock_file(lock_file)
        
        # Mock mirror manager
        mock_mirror = Mock()
        mock_mirror_class.return_value = mock_mirror
        installer.mirror_manager = mock_mirror
        
        # Mock list_mirrors to return active and unused mirrors
        mock_mirror.list_mirrors.return_value = [
            {
                'repo_url': 'https://github.com/example/active-repo',
                'mirror_path': '/mirrors/active'
            },
            {
                'repo_url': 'https://github.com/example/unused-repo',
                'mirror_path': '/mirrors/unused'
            }
        ]
        
        # Test cleanup
        removed = installer.clean_unused_mirrors()
        
        # Verify only unused mirror was removed
        mock_mirror.remove_mirror.assert_called_once_with('https://github.com/example/unused-repo')
        assert len(removed) == 1
        assert '/mirrors/unused' in removed