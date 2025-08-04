"""Unit tests for LibraryInstaller management operations."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from ams_compose.core.installer import LibraryInstaller
from ams_compose.core.config import ComposeConfig, LockFile, LockEntry


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
            libraries={
                "library1": LockEntry(
                    repo="https://github.com/example/repo1",
                    ref="main",
                    commit="abc123",
                    source_path="lib",
                    local_path="designs/libs/library1",
                    checksum="checksum1",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                ),
                "library2": LockEntry(
                    repo="https://github.com/example/repo2",
                    ref="v1.0",
                    commit="def456",
                    source_path="src",
                    local_path="designs/libs/library2",
                    checksum="checksum2",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".ams-compose.lock"
        lock_data.to_yaml(lock_path)
        
        # Test listing
        installed = installer.list_installed_libraries()
        
        assert len(installed) == 2
        assert "library1" in installed
        assert "library2" in installed
        
        # Verify library information
        lib1_info = installed["library1"]
        assert lib1_info.repo == "https://github.com/example/repo1"
        assert lib1_info.ref == "main"
        assert lib1_info.commit == "abc123"
        
        lib2_info = installed["library2"]
        assert lib2_info.repo == "https://github.com/example/repo2"
        assert lib2_info.ref == "v1.0"
    
    @patch('ams_compose.core.installer.ChecksumCalculator')
    def test_validate_installation_success(self, mock_checksum_class, installer, temp_project):
        """Test successful installation validation with new Dict[str, LockEntry] return type."""
        # Create sample library directory
        lib_root = temp_project / "designs" / "libs"
        lib_root.mkdir(parents=True)
        lib_path = lib_root / "test_lib"
        lib_path.mkdir()
        (lib_path / "test.sch").write_text("content")
        
        # Create lockfile entry
        lock_data = LockFile(
            library_root="designs/libs",
            libraries={
                "test_lib": LockEntry(
                    repo="https://github.com/example/repo",
                    ref="main",
                    commit="abc123",
                    source_path="lib",
                    local_path="designs/libs/test_lib",
                    checksum="expected_checksum",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".ams-compose.lock"
        lock_data.to_yaml(lock_path)
        
        # Create matching config file with the library
        config_path = temp_project / "ams-compose.yaml"
        config_content = """library_root: designs/libs
imports:
  test_lib:
    repo: https://github.com/example/repo
    ref: main
    source_path: lib
"""
        config_path.write_text(config_content)
        
        # Mock checksum calculator to return matching checksum
        mock_checksum_class.calculate_directory_checksum.return_value = "expected_checksum"
        
        # Test validation - expecting Dict[str, LockEntry] instead of tuple
        validation_results = installer.validate_installation()
        
        # Verify return type is dict
        assert isinstance(validation_results, dict)
        assert "test_lib" in validation_results
        
        # Verify validation_status is set correctly
        test_lib_entry = validation_results["test_lib"]
        assert test_lib_entry.validation_status == "valid"
        assert test_lib_entry.repo == "https://github.com/example/repo"
        assert test_lib_entry.checksum == "expected_checksum"
        
        # Check that checksum calculation was called with the resolved library path
        # Use resolve() to handle macOS symlink issues (/var -> /private/var)
        expected_path = lib_path.resolve()
        mock_checksum_class.calculate_directory_checksum.assert_called_once_with(expected_path)
    
    def test_validate_installation_missing_directory(self, installer, temp_project):
        """Test validation when library directory is missing with new Dict[str, LockEntry] return type."""
        # Create lockfile entry for non-existent library
        lock_data = LockFile(
            library_root="designs/libs",
            libraries={
                "missing_lib": LockEntry(
                    repo="https://github.com/example/repo",
                    ref="main",
                    commit="abc123",
                    source_path="lib",
                    local_path="designs/libs/missing_lib",
                    checksum="expected_checksum",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".ams-compose.lock"
        lock_data.to_yaml(lock_path)
        
        # Create matching config file with the library
        config_path = temp_project / "ams-compose.yaml"
        config_content = """library_root: designs/libs
imports:
  missing_lib:
    repo: https://github.com/example/repo
    ref: main
    source_path: lib
"""
        config_path.write_text(config_content)
        
        # Test validation - expecting Dict[str, LockEntry] instead of tuple
        validation_results = installer.validate_installation()
        
        # Verify return type is dict
        assert isinstance(validation_results, dict)
        assert "missing_lib" in validation_results
        
        # Verify validation_status shows missing
        missing_lib_entry = validation_results["missing_lib"]
        assert missing_lib_entry.validation_status == "missing"
        assert missing_lib_entry.repo == "https://github.com/example/repo"
    
    @patch('ams_compose.core.installer.RepositoryMirror')
    def test_clean_unused_mirrors(self, mock_mirror_class, installer, temp_project):
        """Test cleaning unused mirror directories."""
        # Create lockfile with one entry
        lock_data = LockFile(
            library_root="designs/libs",
            libraries={
                "active_lib": LockEntry(
                    repo="https://github.com/example/active-repo",
                    ref="main",
                    commit="abc123",
                    source_path="lib",
                    local_path="designs/libs/active_lib",
                    checksum="checksum1",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00"
                )
            }
        )
        
        lock_path = temp_project / ".ams-compose.lock"
        lock_data.to_yaml(lock_path)
        
        # Mock mirror manager
        mock_mirror = Mock()
        mock_mirror_class.return_value = mock_mirror
        mock_mirror.list_mirrors.return_value = ["repo_hash1", "repo_hash2", "active_repo_hash"]
        mock_mirror.remove_mirror.return_value = True
        
        # Re-initialize installer to use mock
        installer.mirror_manager = mock_mirror
        
        # Test cleanup
        removed = installer.clean_unused_mirrors()
        
        # Verify list_mirrors was called
        mock_mirror.list_mirrors.assert_called_once()
        
        # We can't easily test the exact removed repos without knowing the hash generation,
        # but we can verify the method completed
        assert isinstance(removed, list)
    
    @patch('ams_compose.core.installer.ChecksumCalculator')
    def test_validate_library_valid(self, mock_checksum_class, installer, temp_project):
        """Test validate_library method with valid library."""
        # Create sample library directory
        lib_root = temp_project / "designs" / "libs"
        lib_root.mkdir(parents=True)
        lib_path = lib_root / "test_lib"
        lib_path.mkdir()
        (lib_path / "test.sch").write_text("content")
        
        # Create LockEntry for validation
        lock_entry = LockEntry(
            repo="https://github.com/example/repo",
            ref="main",
            commit="abc123",
            source_path="lib",
            local_path="designs/libs/test_lib",
            checksum="expected_checksum",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            validation_status="unknown"
        )
        
        # Mock checksum calculator to return matching checksum
        mock_checksum_class.calculate_directory_checksum.return_value = "expected_checksum"
        
        # Test validate_library method
        result = installer.validate_library("test_lib", lock_entry)
        
        assert result.validation_status == "valid"
        assert result.repo == lock_entry.repo
        assert result.checksum == lock_entry.checksum
        
        # Check that checksum calculation was called with the resolved library path
        expected_path = lib_path.resolve()
        mock_checksum_class.calculate_directory_checksum.assert_called_once_with(expected_path)
    
    @patch('ams_compose.core.installer.ChecksumCalculator')
    def test_validate_library_modified(self, mock_checksum_class, installer, temp_project):
        """Test validate_library method with modified library."""
        # Create sample library directory
        lib_root = temp_project / "designs" / "libs"
        lib_root.mkdir(parents=True)
        lib_path = lib_root / "test_lib"
        lib_path.mkdir()
        (lib_path / "test.sch").write_text("modified_content")
        
        # Create LockEntry for validation
        lock_entry = LockEntry(
            repo="https://github.com/example/repo",
            ref="main",
            commit="abc123",
            source_path="lib",
            local_path="designs/libs/test_lib",
            checksum="expected_checksum",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            validation_status="unknown"
        )
        
        # Mock checksum calculator to return different checksum
        mock_checksum_class.calculate_directory_checksum.return_value = "different_checksum"
        
        # Test validate_library method
        result = installer.validate_library("test_lib", lock_entry)
        
        assert result.validation_status == "modified"
        assert result.repo == lock_entry.repo
        assert result.checksum == lock_entry.checksum  # Original checksum preserved
        
        # Check that checksum calculation was called with the resolved library path
        expected_path = lib_path.resolve()
        mock_checksum_class.calculate_directory_checksum.assert_called_once_with(expected_path)
    
    def test_validate_library_missing(self, installer, temp_project):
        """Test validate_library method with missing library."""
        # Create LockEntry for non-existent library
        lock_entry = LockEntry(
            repo="https://github.com/example/repo",
            ref="main",
            commit="abc123",
            source_path="lib",
            local_path="designs/libs/missing_lib",
            checksum="expected_checksum",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            validation_status="unknown"
        )
        
        # Test validate_library method
        result = installer.validate_library("missing_lib", lock_entry)
        
        assert result.validation_status == "missing"
        assert result.repo == lock_entry.repo
        assert result.checksum == lock_entry.checksum
    
    def test_validate_library_error(self, installer, temp_project):
        """Test validate_library method with validation error."""
        # Create sample library directory
        lib_root = temp_project / "designs" / "libs"
        lib_root.mkdir(parents=True)
        lib_path = lib_root / "test_lib"
        lib_path.mkdir()
        
        # Create LockEntry for validation
        lock_entry = LockEntry(
            repo="https://github.com/example/repo",
            ref="main",
            commit="abc123",
            source_path="lib",
            local_path="designs/libs/test_lib",
            checksum="expected_checksum",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            validation_status="unknown"
        )
        
        # Mock checksum calculator to raise exception
        with patch('ams_compose.core.installer.ChecksumCalculator.calculate_directory_checksum') as mock_checksum:
            mock_checksum.side_effect = Exception("Checksum calculation failed")
            
            # Test validate_library method
            result = installer.validate_library("test_lib", lock_entry)
            
            assert result.validation_status == "error"
            assert result.repo == lock_entry.repo
            assert result.checksum == lock_entry.checksum