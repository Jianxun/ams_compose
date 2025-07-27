"""Unit tests for LibraryInstaller management operations."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from analog_hub.core.installer import LibraryInstaller
from analog_hub.core.config import AnalogHubConfig, LockFile, LockEntry


class TestInstallerManagement:
    """Test LibraryInstaller management methods."""
    
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
    
    def test_list_installed_libraries(self, installer, temp_project):
        """Test listing installed libraries."""
        # Create sample library directories
        lib_root = temp_project / "designs" / "libs"
        lib_root.mkdir(parents=True)
        
        lib1_path = lib_root / "library1"
        lib1_path.mkdir()
        (lib1_path / "test.sch").write_text("content1")
        
        lib2_path = lib_root / "library2"
        lib2_path.mkdir()
        (lib2_path / "test.v").write_text("content2")
        
        # Create lockfile with entries
        lock_data = LockFile(
            library_root="designs/libs",
            entries={
                "library1": LockEntry(
                    repo_url="https://github.com/example/repo1",
                    ref="main",
                    resolved_commit="abc123",
                    source_path="lib",
                    local_path="designs/libs/library1",
                    checksum="checksum1",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                ),
                "library2": LockEntry(
                    repo_url="https://github.com/example/repo2",
                    ref="v1.0",
                    resolved_commit="def456",
                    source_path="src",
                    local_path="designs/libs/library2",
                    checksum="checksum2",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".analog-hub.lock"
        lock_data.to_yaml(lock_path)
        
        # Test listing
        installed = installer.list_installed_libraries()
        
        assert len(installed) == 2
        assert "library1" in installed
        assert "library2" in installed
        
        # Verify library information
        lib1_info = installed["library1"]
        assert lib1_info["path"] == lib1_path
        assert lib1_info["repo_url"] == "https://github.com/example/repo1"
        assert lib1_info["ref"] == "main"
        assert lib1_info["resolved_commit"] == "abc123"
        
        lib2_info = installed["library2"]
        assert lib2_info["path"] == lib2_path
        assert lib2_info["repo_url"] == "https://github.com/example/repo2"
        assert lib2_info["ref"] == "v1.0"
    
    @patch('analog_hub.core.installer.PathExtractor')
    def test_validate_installation_success(self, mock_extractor_class, installer, temp_project):
        """Test successful installation validation."""
        # Create sample library directory
        lib_root = temp_project / "designs" / "libs"
        lib_root.mkdir(parents=True)
        lib_path = lib_root / "test_lib"
        lib_path.mkdir()
        (lib_path / "test.sch").write_text("content")
        
        # Create lockfile entry
        lock_data = LockFile(
            library_root="designs/libs",
            entries={
                "test_lib": LockEntry(
                    repo_url="https://github.com/example/repo",
                    ref="main",
                    resolved_commit="abc123",
                    source_path="lib",
                    local_path="designs/libs/test_lib",
                    checksum="expected_checksum",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".analog-hub.lock"
        lock_data.to_yaml(lock_path)
        
        # Mock extractor to return matching checksum
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.validate_library.return_value = "expected_checksum"
        
        # Re-initialize installer to use mock
        installer.path_extractor = mock_extractor
        
        # Test validation
        result = installer.validate_installation("test_lib")
        
        assert result is True
        mock_extractor.validate_library.assert_called_once_with(lib_path)
    
    def test_validate_installation_missing_directory(self, installer, temp_project):
        """Test validation when library directory is missing."""
        # Create lockfile entry for non-existent library
        lock_data = LockFile(
            library_root="designs/libs",
            entries={
                "missing_lib": LockEntry(
                    repo_url="https://github.com/example/repo",
                    ref="main",
                    resolved_commit="abc123",
                    source_path="lib",
                    local_path="designs/libs/missing_lib",
                    checksum="expected_checksum",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".analog-hub.lock"
        lock_data.to_yaml(lock_path)
        
        # Test validation
        result = installer.validate_installation("missing_lib")
        
        assert result is False
    
    @patch('analog_hub.core.installer.RepositoryMirror')
    def test_clean_unused_mirrors(self, mock_mirror_class, installer, temp_project):
        """Test cleaning unused mirror directories."""
        # Create lockfile with one entry
        lock_data = LockFile(
            library_root="designs/libs",
            entries={
                "active_lib": LockEntry(
                    repo_url="https://github.com/example/active-repo",
                    ref="main",
                    resolved_commit="abc123",
                    source_path="lib",
                    local_path="designs/libs/active_lib",
                    checksum="checksum1",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".analog-hub.lock"
        lock_data.to_yaml(lock_path)
        
        # Mock mirror manager
        mock_mirror = Mock()
        mock_mirror_class.return_value = mock_mirror
        mock_mirror.clean_unused_mirrors.return_value = ["unused_repo_hash1", "unused_repo_hash2"]
        
        # Re-initialize installer to use mock
        installer.mirror_manager = mock_mirror
        
        # Test cleanup
        removed = installer.clean_unused_mirrors()
        
        # Verify cleanup was called with active repos
        mock_mirror.clean_unused_mirrors.assert_called_once_with({"https://github.com/example/active-repo"})
        
        # Verify return value
        assert removed == ["unused_repo_hash1", "unused_repo_hash2"]