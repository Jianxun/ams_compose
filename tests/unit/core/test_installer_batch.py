"""Unit tests for LibraryInstaller batch installation operations."""

import pytest
import tempfile
import shutil
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from ams_compose.core.installer import LibraryInstaller, InstallationError
from ams_compose.core.config import ComposeConfig, ImportSpec, LockEntry, LockFile


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
        """Create sample ams-compose.yaml configuration."""
        config = ComposeConfig()
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
    
    @patch('ams_compose.core.installer.LibraryInstaller.install_library')
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
        installed, up_to_date = installer.install_all()
        
        # Verify all libraries were installed
        assert len(installed) == 2
        assert "test_library" in installed
        assert "another_lib" in installed
        assert len(up_to_date) == 0  # No libraries should be up-to-date in this test
        
        # Verify install_library was called for each library
        assert mock_install_library.call_count == 2
        
        # Verify lock entries
        assert installed["test_library"].repo == "https://github.com/example/test-repo"
        assert installed["another_lib"].repo == "https://github.com/example/another-repo"
        assert installed["another_lib"].local_path == "custom/path"
    
    @patch('ams_compose.core.installer.LibraryInstaller.install_library')
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
    
    @patch('ams_compose.core.installer.LibraryInstaller.install_library')
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
    
    @patch('ams_compose.core.installer.LibraryInstaller.install_library')
    @patch('ams_compose.utils.license.LicenseDetector.get_license_compatibility_warning')
    def test_install_libraries_batch_no_print_output(self, mock_get_warning, mock_install_library, installer, sample_config):
        """Test that _install_libraries_batch() produces no print output (TDD Cycle 4 RED)."""
        # Mock license warning
        mock_get_warning.return_value = "Test license warning"
        
        # Mock successful installation
        mock_install_library.return_value = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="abc123def",
            source_path="lib/test",
            local_path="designs/libs/test_library",
            checksum="checksum1",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            license="MIT"
        )
        
        # Create libraries needing work and empty lock file
        libraries_needing_work = {
            "test_library": ImportSpec(
                repo="https://github.com/example/test-repo",
                ref="main",
                source_path="lib/test"
            )
        }
        lock_file = LockFile(library_root="designs/libs", libraries={})
        
        # Capture stdout to verify no print statements
        captured_output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            # Call the batch installation method directly
            result = installer._install_libraries_batch(
                libraries_needing_work,
                sample_config,
                lock_file
            )
            
            # Verify the method executed successfully
            assert len(result) == 1
            assert "test_library" in result
            
        finally:
            # Restore stdout
            sys.stdout = original_stdout
        
        # Assert that NO output was printed to stdout
        output = captured_output.getvalue()
        assert output == "", f"Expected no print output, but got: {repr(output)}"
        
        # Verify that status information is captured in the LockEntry
        assert result["test_library"].install_status == "installed"
        assert result["test_library"].license_warning is not None  # Should have warning for MIT license
    
    @patch('ams_compose.core.installer.LibraryInstaller.install_library')
    def test_install_libraries_batch_update_scenario_no_print(self, mock_install_library, installer, sample_config):
        """Test that _install_libraries_batch() handles updates without print output."""
        # Mock successful installation for an update
        mock_install_library.return_value = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="newcommit",
            source_path="lib/test",
            local_path="designs/libs/test_library",
            checksum="newchecksum",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T12:00:00",
            license="GPL-3.0"
        )
        
        # Create libraries needing work and lock file with existing entry
        libraries_needing_work = {
            "test_library": ImportSpec(
                repo="https://github.com/example/test-repo",
                ref="main",
                source_path="lib/test"
            )
        }
        lock_file = LockFile(
            library_root="designs/libs", 
            libraries={
                "test_library": LockEntry(
                    repo="https://github.com/example/test-repo",
                    ref="main",
                    commit="oldcommit",
                    source_path="lib/test",
                    local_path="designs/libs/test_library",
                    checksum="oldchecksum",
                    installed_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00",
                    license="MIT"
                )
            }
        )
        
        # Capture stdout to verify no print statements
        captured_output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            result = installer._install_libraries_batch(
                libraries_needing_work,
                sample_config,
                lock_file
            )
        finally:
            sys.stdout = original_stdout
        
        # Assert that NO output was printed
        output = captured_output.getvalue()
        assert output == "", f"Expected no print output, but got: {repr(output)}"
        
        # Verify update status and license change are captured
        assert result["test_library"].install_status == "updated"
        assert result["test_library"].license_change == "license changed: MIT → GPL-3.0"