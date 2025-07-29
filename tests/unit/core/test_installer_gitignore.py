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
        """Test gitignore injection for checkin=false library."""
        # This test will fail until we implement the functionality
        gitignore_path = temp_project / ".gitignore"
        
        # Create initial .gitignore with some content
        gitignore_path.write_text("# existing content\n*.log\n")
        
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
        
        # Call method that should update .gitignore (to be implemented)
        installer._update_gitignore_for_library("test_lib", lock_entry)
        
        # Assert library path is in .gitignore
        gitignore_content = gitignore_path.read_text()
        assert "designs/libs/test_lib/" in gitignore_content
        assert "*.log" in gitignore_content  # Existing content preserved
    
    def test_update_gitignore_for_checkin_true_library(self, installer, temp_project):
        """Test that checkin=true libraries are NOT added to .gitignore."""
        gitignore_path = temp_project / ".gitignore"
        
        # Create initial .gitignore
        gitignore_path.write_text("# existing content\n*.log\n")
        
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
        
        # Call method that should NOT update .gitignore
        installer._update_gitignore_for_library("test_lib", lock_entry)
        
        # Assert library path is NOT in .gitignore
        gitignore_content = gitignore_path.read_text()
        assert "designs/libs/test_lib/" not in gitignore_content
        assert "*.log" in gitignore_content  # Existing content preserved
    
    def test_create_new_gitignore_for_checkin_false_library(self, installer, temp_project):
        """Test creating new .gitignore when none exists."""
        gitignore_path = temp_project / ".gitignore"
        
        # Ensure no .gitignore exists
        assert not gitignore_path.exists()
        
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
        
        # Call method that should create .gitignore
        installer._update_gitignore_for_library("test_lib", lock_entry)
        
        # Assert .gitignore was created with library path
        assert gitignore_path.exists()
        gitignore_content = gitignore_path.read_text()
        assert "designs/libs/test_lib/" in gitignore_content
    
    def test_remove_library_from_gitignore_when_checkin_changes_to_true(self, installer, temp_project):
        """Test removing library from .gitignore when checkin changes from false to true."""
        gitignore_path = temp_project / ".gitignore"
        
        # Create .gitignore with library already ignored
        gitignore_path.write_text("""# analog-hub libraries
*.log
designs/libs/test_lib/
designs/libs/other_lib/
""")
        
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
        
        # Call method that should remove library from .gitignore
        installer._update_gitignore_for_library("test_lib", lock_entry)
        
        # Assert library path is removed but other content preserved
        gitignore_content = gitignore_path.read_text()
        assert "designs/libs/test_lib/" not in gitignore_content
        assert "designs/libs/other_lib/" in gitignore_content  # Other ignored libs preserved
        assert "*.log" in gitignore_content  # Existing content preserved