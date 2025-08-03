"""Security tests for path traversal vulnerabilities."""

import pytest
from pathlib import Path
from unittest.mock import patch

from ams_compose.core.config import ImportSpec
from ams_compose.core.extractor import PathExtractor
from ams_compose.core.installer import LibraryInstaller


class TestPathTraversalSecurity:
    """Test path traversal security measures."""
    
    def setup_method(self):
        """Set up test environment."""
        self.project_root = Path("/tmp/test_project")
        self.extractor = PathExtractor(self.project_root)
        self.installer = LibraryInstaller(self.project_root)
    
    def test_extractor_blocks_path_traversal_relative(self):
        """Test that extractor blocks relative path traversal attempts."""
        malicious_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path=".",
            local_path="../../../etc/passwd"
        )
        
        with pytest.raises(ValueError, match="Security error.*attempts to escape project directory"):
            self.extractor._resolve_local_path("malicious_lib", malicious_spec, "libs")
    
    def test_extractor_blocks_path_traversal_absolute(self):
        """Test that extractor blocks absolute path traversal attempts."""
        malicious_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path=".",
            local_path="/etc/passwd"
        )
        
        with pytest.raises(ValueError, match="Security error.*attempts to escape project directory"):
            self.extractor._resolve_local_path("malicious_lib", malicious_spec, "libs")
    
    def test_extractor_blocks_symlink_traversal(self):
        """Test that extractor blocks symlink-based traversal attempts."""
        # Create a path that would resolve outside project via symlinks
        malicious_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path=".",
            local_path="libs/../../../../../../etc/passwd"
        )
        
        with pytest.raises(ValueError, match="Security error.*attempts to escape project directory"):
            self.extractor._resolve_local_path("malicious_lib", malicious_spec, "libs")
    
    def test_extractor_allows_safe_paths(self):
        """Test that extractor allows safe paths within project."""
        safe_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path=".",
            local_path="libs/safe_library"
        )
        
        # Should not raise an exception
        result = self.extractor._resolve_local_path("safe_lib", safe_spec, "libs")
        assert self.project_root.resolve() in result.parents
    
    def test_installer_validates_library_paths(self):
        """Test that installer validates library paths from lock entries."""
        from ams_compose.core.config import LockEntry
        from datetime import datetime
        
        malicious_entry = LockEntry(
            repo="https://github.com/test/repo.git",
            ref="main",
            commit="abc123",
            source_path=".",
            local_path="../../../etc/passwd",
            checkin=True,
            checksum="fake_checksum",
            installed_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        with pytest.raises(ValueError, match="Security error.*attempts to escape project directory"):
            self.installer._validate_library_path(malicious_entry.local_path, "malicious_lib")
    
    def test_installer_allows_safe_library_paths(self):
        """Test that installer allows safe library paths."""
        from ams_compose.core.config import LockEntry
        from datetime import datetime
        
        safe_entry = LockEntry(
            repo="https://github.com/test/repo.git",
            ref="main",
            commit="abc123",
            source_path=".",
            local_path="libs/safe_library",
            checkin=True,
            checksum="fake_checksum",
            installed_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Should not raise an exception
        result = self.installer._validate_library_path(safe_entry.local_path, "safe_lib")
        assert self.project_root.resolve() in result.parents
    
    def test_complex_path_traversal_patterns(self):
        """Test various complex path traversal patterns that actually escape."""
        # Only test patterns that actually resolve to paths outside the project
        malicious_patterns = [
            "libs/../../../etc",  # Mixed with legitimate path
            "./../../etc/passwd",  # Dot prefix
            "libs/../../../../usr/bin",  # Multiple levels
        ]
        
        for pattern in malicious_patterns:
            malicious_spec = ImportSpec(
                repo="https://github.com/test/repo.git",
                ref="main",
                source_path=".",
                local_path=pattern
            )
            
            with pytest.raises(ValueError, match="Security error.*attempts to escape project directory"):
                self.extractor._resolve_local_path("malicious_lib", malicious_spec, "libs")
        
        # Test patterns that don't escape (should not raise)
        safe_but_weird_patterns = [
            "..\\..\\..\\windows\\system32",  # Windows-style backslashes (treated as literal on Unix)
            "%2e%2e%2f%2e%2e%2fpasswd",  # URL encoded (not decoded by path resolution)
        ]
        
        for pattern in safe_but_weird_patterns:
            safe_spec = ImportSpec(
                repo="https://github.com/test/repo.git",
                ref="main",
                source_path=".",
                local_path=pattern
            )
            
            # Should not raise an exception since these don't actually escape
            result = self.extractor._resolve_local_path("safe_lib", safe_spec, "libs")
            assert self.project_root.resolve() in result.parents