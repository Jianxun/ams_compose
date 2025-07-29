"""Unit tests for LibraryInstaller gitignore injection logic."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from ams_compose.core.installer import LibraryInstaller, InstallationError
from ams_compose.core.config import AnalogHubConfig, ImportSpec, LockFile, LockEntry


class TestInstallerGitignore:
    """Test LibraryInstaller gitignore injection functionality."""
    
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
    
    def test_update_gitignore_for_checkin_false_library(self, installer, temp_project):
        """Test that checkin=false library gets its own .gitignore file."""
        # Create library directory
        library_path = temp_project / "designs/libs/test_lib"
        library_path.mkdir(parents=True)
        
        # Create main project .gitignore with some content (should remain unchanged)
        main_gitignore_path = temp_project / ".gitignore"
        main_gitignore_path.write_text("# existing content\n*.log\n")
        
        # Create library with checkin=false
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
        
        # Call method that should create library-specific .gitignore
        installer._update_gitignore_for_library("test_lib", lock_entry)
        
        # Assert library-specific .gitignore is created with '*' content
        library_gitignore_path = library_path / ".gitignore"
        assert library_gitignore_path.exists()
        assert library_gitignore_path.read_text() == "*\n"
        
        # Assert main .gitignore is unchanged
        main_gitignore_content = main_gitignore_path.read_text()
        assert "designs/libs/test_lib/" not in main_gitignore_content
        assert "*.log" in main_gitignore_content  # Existing content preserved
    
    def test_update_gitignore_for_checkin_true_library(self, installer, temp_project):
        """Test that checkin=true libraries do NOT get their own .gitignore file."""
        # Create library directory
        library_path = temp_project / "designs/libs/test_lib"
        library_path.mkdir(parents=True)
        
        # Create main project .gitignore (should remain unchanged)
        main_gitignore_path = temp_project / ".gitignore"
        main_gitignore_path.write_text("# existing content\n*.log\n")
        
        # Create library with checkin=true (default)
        lock_entry = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="abc123",
            source_path="lib/test",
            local_path="designs/libs/test_lib",
            checksum="checksum123",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            checkin=True
        )
        
        # Call method that should NOT create library-specific .gitignore
        installer._update_gitignore_for_library("test_lib", lock_entry)
        
        # Assert library-specific .gitignore is NOT created
        library_gitignore_path = library_path / ".gitignore"
        assert not library_gitignore_path.exists()
        
        # Assert main .gitignore is unchanged
        main_gitignore_content = main_gitignore_path.read_text()
        assert "designs/libs/test_lib/" not in main_gitignore_content
        assert "*.log" in main_gitignore_content  # Existing content preserved
    
    def test_create_library_gitignore_when_library_directory_exists(self, installer, temp_project):
        """Test creating library-specific .gitignore when library directory exists."""
        # Create library directory
        library_path = temp_project / "designs/libs/test_lib"
        library_path.mkdir(parents=True)
        
        # Ensure no main .gitignore exists (should not be created)
        main_gitignore_path = temp_project / ".gitignore"
        assert not main_gitignore_path.exists()
        
        # Create library with checkin=false
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
        
        # Call method that should create library-specific .gitignore
        installer._update_gitignore_for_library("test_lib", lock_entry)
        
        # Assert library-specific .gitignore was created
        library_gitignore_path = library_path / ".gitignore"
        assert library_gitignore_path.exists()
        assert library_gitignore_path.read_text() == "*\n"
        
        # Assert main .gitignore was NOT created
        assert not main_gitignore_path.exists()
    
    def test_remove_library_gitignore_when_checkin_changes_to_true(self, installer, temp_project):
        """Test removing library-specific .gitignore when checkin changes from false to true."""
        # Create library directory with existing .gitignore
        library_path = temp_project / "designs/libs/test_lib"
        library_path.mkdir(parents=True)
        library_gitignore_path = library_path / ".gitignore"
        library_gitignore_path.write_text("*\n")
        
        # Create main .gitignore (should remain unchanged)
        main_gitignore_path = temp_project / ".gitignore"
        main_gitignore_path.write_text("# ams-compose libraries\n*.log\n")
        
        # Create library with checkin=true (was previously false)
        lock_entry = LockEntry(
            repo="https://github.com/example/test-repo",
            ref="main",
            commit="abc123",
            source_path="lib/test",
            local_path="designs/libs/test_lib",
            checksum="checksum123",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            checkin=True
        )
        
        # Call method that should remove library-specific .gitignore
        installer._update_gitignore_for_library("test_lib", lock_entry)
        
        # Assert library-specific .gitignore is removed
        assert not library_gitignore_path.exists()
        
        # Assert main .gitignore is unchanged
        main_gitignore_content = main_gitignore_path.read_text()
        assert "*.log" in main_gitignore_content  # Existing content preserved
        assert "designs/libs/test_lib/" not in main_gitignore_content  # Library was never in main .gitignore