"""Unit tests for PathExtractor path resolution logic."""

import tempfile
import shutil
from pathlib import Path

import pytest

from ams_compose.core.extractor import PathExtractor
from ams_compose.core.config import ImportSpec


class TestPathResolution:
    """Test PathExtractor path resolution methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "project"
        self.project_root.mkdir()
        
        self.extractor = PathExtractor(self.project_root)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_resolve_local_path_with_library_root(self):
        """Test path resolution using library_root."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib"
        )
        
        local_path = self.extractor._resolve_local_path("my_lib", import_spec, "designs/libs")
        expected = self.project_root / "designs" / "libs" / "my_lib"
        assert local_path == expected.resolve()
    
    def test_resolve_local_path_with_override(self):
        """Test path resolution with local_path override."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib",
            local_path="custom/path/lib"
        )
        
        local_path = self.extractor._resolve_local_path("my_lib", import_spec, "designs/libs")
        expected = self.project_root / "custom" / "path" / "lib"
        assert local_path == expected.resolve()
    
    def test_resolve_local_path_absolute_override(self):
        """Test path resolution with absolute local_path override."""
        absolute_path = Path(self.temp_dir) / "absolute" / "lib"
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib",
            local_path=str(absolute_path)
        )
        
        local_path = self.extractor._resolve_local_path("my_lib", import_spec, "designs/libs")
        assert local_path == absolute_path.resolve()