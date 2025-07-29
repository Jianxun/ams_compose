"""Unit tests for PathExtractor three-tier filtering system."""

import tempfile
import shutil
from pathlib import Path

import pytest

from ams_compose.core.extractor import PathExtractor
from ams_compose.core.config import ImportSpec


class TestThreeTierFiltering:
    """Test PathExtractor three-tier filtering system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "project"
        self.project_root.mkdir()
        
        self.extractor = PathExtractor(self.project_root)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_builtin_ignore_patterns_constants(self):
        """Test that built-in ignore patterns are properly defined."""
        # Test VCS patterns
        assert '.git' in self.extractor.VCS_IGNORE_PATTERNS
        assert '.svn' in self.extractor.VCS_IGNORE_PATTERNS
        assert '.hg' in self.extractor.VCS_IGNORE_PATTERNS
        
        # Test development tool patterns
        assert '.ipynb_checkpoints' in self.extractor.DEV_TOOL_IGNORE_PATTERNS
        assert '__pycache__' in self.extractor.DEV_TOOL_IGNORE_PATTERNS
        assert 'node_modules' in self.extractor.DEV_TOOL_IGNORE_PATTERNS
        
        # Test OS patterns
        assert '.DS_Store' in self.extractor.OS_IGNORE_PATTERNS
        assert 'Thumbs.db' in self.extractor.OS_IGNORE_PATTERNS
    
    def test_get_builtin_ignore_patterns(self):
        """Test the get_builtin_ignore_patterns class method."""
        all_patterns = self.extractor.get_builtin_ignore_patterns()
        
        # Should include patterns from all categories
        assert '.git' in all_patterns
        assert '.ipynb_checkpoints' in all_patterns
        assert '.DS_Store' in all_patterns
        
        # Should be the union of all pattern sets
        expected_size = (
            len(self.extractor.VCS_IGNORE_PATTERNS) +
            len(self.extractor.DEV_TOOL_IGNORE_PATTERNS) +
            len(self.extractor.OS_IGNORE_PATTERNS)
        )
        assert len(all_patterns) == expected_size
    
    def test_load_global_ignore_patterns_no_file(self):
        """Test loading global ignore patterns when file doesn't exist."""
        patterns = self.extractor._load_global_ignore_patterns()
        assert patterns == []
    
    def test_load_global_ignore_patterns_with_file(self):
        """Test loading global ignore patterns from file."""
        # Create .analog-hub-ignore file
        ignore_file = self.project_root / self.extractor.GLOBAL_IGNORE_FILE
        ignore_content = """# Global ignore patterns
*.log
*.tmp
build/
# Comments should be ignored

# Empty lines should be ignored
*.backup
"""
        ignore_file.write_text(ignore_content)
        
        patterns = self.extractor._load_global_ignore_patterns()
        
        expected_patterns = ['*.log', '*.tmp', 'build/', '*.backup']
        assert patterns == expected_patterns
    
    def test_tier1_builtin_filtering(self):
        """Test tier 1 built-in filtering (exact filename matches)."""
        ignore_func = self.extractor._create_ignore_function()
        
        test_filenames = [
            'library.v', 'readme.txt', '.git', '.gitignore', 
            '.svn', '.hg', '.ipynb_checkpoints', '__pycache__',
            '.DS_Store', 'Thumbs.db', 'normal_file.txt'
        ]
        
        ignored = ignore_func('/some/dir', test_filenames)
        
        # All built-in patterns should be ignored
        builtin_patterns = self.extractor.get_builtin_ignore_patterns()
        for pattern in builtin_patterns:
            if pattern in test_filenames:
                assert pattern in ignored
        
        # Normal files should not be ignored
        assert 'library.v' not in ignored
        assert 'readme.txt' not in ignored
        assert 'normal_file.txt' not in ignored
    
    def test_tier2_global_ignore_patterns(self):
        """Test tier 2 global .analog-hub-ignore patterns."""
        # Create global ignore file
        ignore_file = self.project_root / self.extractor.GLOBAL_IGNORE_FILE
        ignore_file.write_text("*.log\n*.tmp\nbuild/\n")
        
        # Create test directory structure in project
        test_dir = self.project_root / "libs" / "test_lib"
        test_dir.mkdir(parents=True)
        
        ignore_func = self.extractor._create_ignore_function()
        
        test_filenames = [
            'library.v', 'debug.log', 'temp.tmp', 'normal.txt'
        ]
        
        # Test from libs/test_lib directory
        ignored = ignore_func(str(test_dir), test_filenames)
        
        # Global patterns should be ignored
        assert 'debug.log' in ignored  # matches *.log
        assert 'temp.tmp' in ignored   # matches *.tmp
        
        # Non-matching files should not be ignored
        assert 'library.v' not in ignored
        assert 'normal.txt' not in ignored
    
    def test_tier3_library_ignore_patterns(self):
        """Test tier 3 per-library ignore patterns."""
        # Create test directory structure
        test_dir = self.project_root / "libs" / "test_lib"
        test_dir.mkdir(parents=True)
        
        library_patterns = ['*.sim', 'testbench/']
        ignore_func = self.extractor._create_ignore_function(
            library_ignore_patterns=library_patterns
        )
        
        test_filenames = [
            'library.v', 'simulation.sim', 'normal.txt'
        ]
        
        ignored = ignore_func(str(test_dir), test_filenames)
        
        # Library patterns should be ignored
        assert 'simulation.sim' in ignored  # matches *.sim
        
        # Non-matching files should not be ignored
        assert 'library.v' not in ignored
        assert 'normal.txt' not in ignored
    
    def test_all_three_tiers_combined(self):
        """Test all three tiers working together."""
        # Create global ignore file
        ignore_file = self.project_root / self.extractor.GLOBAL_IGNORE_FILE
        ignore_file.write_text("*.log\nbuild/\n")
        
        # Create test directory
        test_dir = self.project_root / "libs" / "test_lib"
        test_dir.mkdir(parents=True)
        
        library_patterns = ['*.sim', '*.waveform']
        ignore_func = self.extractor._create_ignore_function(
            library_ignore_patterns=library_patterns
        )
        
        test_filenames = [
            'library.v',        # Should NOT be ignored
            '.git',             # Tier 1: Built-in VCS ignore
            '__pycache__',      # Tier 1: Built-in dev tool ignore  
            '.DS_Store',        # Tier 1: Built-in OS ignore
            'debug.log',        # Tier 2: Global pattern *.log
            'simulation.sim',   # Tier 3: Library pattern *.sim
            'output.waveform',  # Tier 3: Library pattern *.waveform
            'normal.txt'        # Should NOT be ignored
        ]
        
        ignored = ignore_func(str(test_dir), test_filenames)
        
        # All three tiers should be applied
        assert '.git' in ignored           # Tier 1
        assert '__pycache__' in ignored    # Tier 1
        assert '.DS_Store' in ignored      # Tier 1
        assert 'debug.log' in ignored      # Tier 2
        assert 'simulation.sim' in ignored # Tier 3
        assert 'output.waveform' in ignored # Tier 3
        
        # Normal files should not be ignored
        assert 'library.v' not in ignored
        assert 'normal.txt' not in ignored
    
    def test_backward_compatibility_custom_hook(self):
        """Test backward compatibility with custom ignore hook."""
        def custom_hook(directory: str, filenames: set) -> set:
            return {f for f in filenames if f.endswith('.bak')}
        
        ignore_func = self.extractor._create_ignore_function(custom_hook)
        
        test_filenames = [
            'library.v', 'backup.bak', '.git', 'normal.txt'
        ]
        
        ignored = ignore_func('/some/dir', test_filenames)
        
        # Should apply both built-in and custom ignores
        assert '.git' in ignored       # Built-in
        assert 'backup.bak' in ignored # Custom hook
        assert 'library.v' not in ignored
        assert 'normal.txt' not in ignored
    
    def test_pathspec_error_handling(self):
        """Test graceful handling of pathspec errors."""
        # Test with invalid patterns that might cause pathspec to fail
        library_patterns = ['[invalid regex']  # Invalid pattern
        
        # Should not raise exception
        ignore_func = self.extractor._create_ignore_function(
            library_ignore_patterns=library_patterns
        )
        
        # Should still work with built-in patterns
        test_filenames = ['.git', 'normal.txt']
        ignored = ignore_func('/some/dir', test_filenames)
        
        assert '.git' in ignored  # Built-in still works
        assert 'normal.txt' not in ignored
    
    def test_global_ignore_file_read_error(self):
        """Test graceful handling of global ignore file read errors."""
        # Create a directory instead of a file (will cause read error)
        ignore_path = self.project_root / self.extractor.GLOBAL_IGNORE_FILE
        ignore_path.mkdir()
        
        # Should not raise exception
        patterns = self.extractor._load_global_ignore_patterns()
        assert patterns == []
        
        # Should still work for creating ignore function
        ignore_func = self.extractor._create_ignore_function()
        test_filenames = ['.git', 'normal.txt']
        ignored = ignore_func('/some/dir', test_filenames)
        
        assert '.git' in ignored
        assert 'normal.txt' not in ignored