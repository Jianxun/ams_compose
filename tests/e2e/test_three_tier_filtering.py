"""E2E tests for three-tier filtering system."""

import tempfile
import shutil
from pathlib import Path

import pytest

from ams_compose.core.config import AnalogHubConfig, ImportSpec
from ams_compose.core.extractor import PathExtractor


class TestThreeTierFilteringE2E:
    """End-to-end tests for three-tier filtering system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "project"
        self.project_root.mkdir()
        
        # Change to project directory
        self.original_cwd = Path.cwd()
        
        # Create mock repository with various file types
        self.mock_repo = self._create_mock_repo()
        
        # Initialize extractor
        self.extractor = PathExtractor(self.project_root)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def _create_mock_repo(self) -> Path:
        """Create a mock repository with various file types for testing filtering."""
        repo_path = Path(self.temp_dir) / "mock_repo"
        repo_path.mkdir()
        
        # Create library directory structure
        lib_dir = repo_path / "analog_library"
        lib_dir.mkdir()
        
        # Analog design files (should be copied)
        (lib_dir / "amplifier.sch").write_text("* Amplifier schematic")
        (lib_dir / "amplifier.sym").write_text("v {xschem version=3.4.4}")
        (lib_dir / "layout.gds").write_text("GDSII layout data")
        (lib_dir / "spice.sp").write_text(".subckt amplifier")
        
        # Built-in ignore patterns (should be filtered)
        (lib_dir / ".git").mkdir()
        (lib_dir / ".git" / "config").write_text("git config")
        (lib_dir / "__pycache__").mkdir()
        (lib_dir / "__pycache__" / "cache.pyc").write_text("cached")
        (lib_dir / ".DS_Store").write_text("mac metadata")
        (lib_dir / ".ipynb_checkpoints").mkdir()
        (lib_dir / ".ipynb_checkpoints" / "notebook-checkpoint.ipynb").write_text("{}")
        
        # Files that match global patterns (should be filtered with global config)
        (lib_dir / "simulation.log").write_text("simulation output")
        (lib_dir / "debug.log").write_text("debug info")
        (lib_dir / "temp.tmp").write_text("temporary file")
        (lib_dir / "build").mkdir()
        (lib_dir / "build" / "output.o").write_text("compiled object")
        
        # Files that match library patterns (should be filtered with library config)
        (lib_dir / "test.sim").write_text("simulation file")
        (lib_dir / "waveform.waveform").write_text("waveform data")
        (lib_dir / "large_dataset.raw").write_text("raw simulation data")
        
        return repo_path
    
    def test_filtering_with_global_ignore_only(self):
        """Test filtering with only global .ams-compose-ignore file."""
        # Create global ignore file
        global_ignore = self.project_root / ".ams-compose-ignore"
        global_ignore.write_text("""
# Global ignore patterns
*.log
*.tmp
build/
*.raw
""")
        
        # Create configuration without library-specific patterns
        config = AnalogHubConfig(
            library_root="libs",
            imports={
                "test_lib": ImportSpec(
                    repo=str(self.mock_repo),
                    ref="main",
                    source_path="analog_library"
                )
            }
        )
        
        # Create config file
        config_path = self.project_root / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            # Convert to dict and write YAML manually for simplicity
            import yaml
            config_dict = {
                "library-root": config.library_root,
                "imports": {
                    "test_lib": {
                        "repo": config.imports["test_lib"].repo,
                        "ref": config.imports["test_lib"].ref,
                        "source_path": config.imports["test_lib"].source_path
                    }
                }
            }
            yaml.dump(config_dict, f)
        
        # Simulate extraction using PathExtractor directly
        extractor = PathExtractor(self.project_root)
        
        # Test ignore function
        ignore_func = extractor._create_ignore_function()
        
        # Get list of files from mock repo
        lib_path = self.mock_repo / "analog_library"
        all_files = [f.name for f in lib_path.iterdir()]
        
        ignored = ignore_func(str(lib_path), all_files)
        
        # Verify built-in patterns are ignored
        assert ".git" in ignored
        assert "__pycache__" in ignored
        assert ".DS_Store" in ignored
        assert ".ipynb_checkpoints" in ignored
        
        # Verify global patterns are ignored
        assert "simulation.log" in ignored  # *.log
        assert "debug.log" in ignored       # *.log
        assert "temp.tmp" in ignored        # *.tmp
        assert "build" in ignored           # build/
        assert "large_dataset.raw" in ignored  # *.raw
        
        # Verify analog design files are NOT ignored
        assert "amplifier.sch" not in ignored
        assert "amplifier.sym" not in ignored
        assert "layout.gds" not in ignored
        assert "spice.sp" not in ignored
        
        # Verify library-specific patterns are NOT ignored (no library config)
        assert "test.sim" not in ignored
        assert "waveform.waveform" not in ignored
    
    def test_filtering_with_library_ignore_patterns(self):
        """Test filtering with library-specific ignore patterns."""
        # Create configuration with library-specific patterns
        config = AnalogHubConfig(
            library_root="libs",
            imports={
                "test_lib": ImportSpec(
                    repo=str(self.mock_repo),
                    ref="main",
                    source_path="analog_library",
                    ignore_patterns=["*.sim", "*.waveform", "*.raw"]
                )
            }
        )
        
        # Create config file
        config_path = self.project_root / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            import yaml
            config_dict = {
                "library-root": config.library_root,
                "imports": {
                    "test_lib": {
                        "repo": config.imports["test_lib"].repo,
                        "ref": config.imports["test_lib"].ref,
                        "source_path": config.imports["test_lib"].source_path,
                        "ignore_patterns": config.imports["test_lib"].ignore_patterns
                    }
                }
            }
            yaml.dump(config_dict, f)
        
        # Test extraction
        extractor = PathExtractor(self.project_root)
        import_spec = config.imports["test_lib"]
        
        ignore_func = extractor._create_ignore_function(
            library_ignore_patterns=import_spec.ignore_patterns
        )
        
        # Get list of files from mock repo
        lib_path = self.mock_repo / "analog_library"
        all_files = [f.name for f in lib_path.iterdir()]
        
        ignored = ignore_func(str(lib_path), all_files)
        
        # Verify built-in patterns are ignored
        assert ".git" in ignored
        assert "__pycache__" in ignored
        assert ".DS_Store" in ignored
        
        # Verify library patterns are ignored
        assert "test.sim" in ignored           # *.sim
        assert "waveform.waveform" in ignored  # *.waveform
        assert "large_dataset.raw" in ignored # *.raw
        
        # Verify analog design files are NOT ignored
        assert "amplifier.sch" not in ignored
        assert "amplifier.sym" not in ignored
        assert "layout.gds" not in ignored
        assert "spice.sp" not in ignored
        
        # Files not matching library patterns should not be ignored by library tier
        # (but may be ignored by global tier if global file exists)
        # Since no global file exists, these should not be ignored
        assert "simulation.log" not in ignored
        assert "debug.log" not in ignored
    
    def test_all_three_tiers_combined(self):
        """Test all three filtering tiers working together."""
        # Create global ignore file
        global_ignore = self.project_root / ".ams-compose-ignore"
        global_ignore.write_text("""
# Global ignore patterns
*.log
build/
""")
        
        # Create configuration with library-specific patterns
        config = AnalogHubConfig(
            library_root="libs",
            imports={
                "test_lib": ImportSpec(
                    repo=str(self.mock_repo),
                    ref="main",
                    source_path="analog_library",
                    ignore_patterns=["*.sim", "*.waveform"]
                )
            }
        )
        
        # Test extraction
        extractor = PathExtractor(self.project_root)
        import_spec = config.imports["test_lib"]
        
        ignore_func = extractor._create_ignore_function(
            library_ignore_patterns=import_spec.ignore_patterns
        )
        
        # Get list of files from mock repo
        lib_path = self.mock_repo / "analog_library"
        all_files = [f.name for f in lib_path.iterdir()]
        
        ignored = ignore_func(str(lib_path), all_files)
        
        # Tier 1: Built-in patterns should be ignored
        assert ".git" in ignored
        assert "__pycache__" in ignored
        assert ".DS_Store" in ignored
        assert ".ipynb_checkpoints" in ignored
        
        # Tier 2: Global patterns should be ignored
        assert "simulation.log" in ignored  # *.log
        assert "debug.log" in ignored       # *.log
        assert "build" in ignored           # build/
        
        # Tier 3: Library patterns should be ignored
        assert "test.sim" in ignored           # *.sim
        assert "waveform.waveform" in ignored  # *.waveform
        
        # Files not matching any pattern should NOT be ignored
        assert "amplifier.sch" not in ignored
        assert "amplifier.sym" not in ignored
        assert "layout.gds" not in ignored
        assert "spice.sp" not in ignored
        assert "temp.tmp" not in ignored      # Not in global patterns
        assert "large_dataset.raw" not in ignored  # Not in library patterns
    
    def test_empty_patterns_graceful_handling(self):
        """Test graceful handling of empty or missing pattern configurations."""
        # No global ignore file, no library patterns
        config = AnalogHubConfig(
            library_root="libs",
            imports={
                "test_lib": ImportSpec(
                    repo=str(self.mock_repo),
                    ref="main",
                    source_path="analog_library"
                    # No ignore_patterns specified (defaults to empty list)
                )
            }
        )
        
        extractor = PathExtractor(self.project_root)
        import_spec = config.imports["test_lib"]
        
        ignore_func = extractor._create_ignore_function(
            library_ignore_patterns=import_spec.ignore_patterns
        )
        
        # Get list of files from mock repo
        lib_path = self.mock_repo / "analog_library"
        all_files = [f.name for f in lib_path.iterdir()]
        
        ignored = ignore_func(str(lib_path), all_files)
        
        # Only built-in patterns should be ignored
        assert ".git" in ignored
        assert "__pycache__" in ignored
        assert ".DS_Store" in ignored
        
        # Everything else should NOT be ignored
        assert "simulation.log" not in ignored
        assert "test.sim" not in ignored
        assert "amplifier.sch" not in ignored