"""Unit tests for PathExtractor extraction operations."""

import tempfile
import shutil
from pathlib import Path

import pytest

from analog_hub.core.extractor import PathExtractor, ExtractionState
from analog_hub.core.config import ImportSpec
from analog_hub.utils.checksum import ChecksumCalculator


class TestExtractionOperations:
    """Test PathExtractor extraction methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "project"
        self.project_root.mkdir()
        
        self.mirror_root = Path(self.temp_dir) / "mirror"
        self.mirror_root.mkdir()
        
        self.extractor = PathExtractor(self.project_root)
        
        # Create mock mirror structure
        self.mock_mirror = self.mirror_root / "test_repo"
        self.mock_mirror.mkdir()
        
        # Create test source files/directories
        self.create_mock_library_structure()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def create_mock_library_structure(self):
        """Create mock library files in mirror for testing."""
        # Create a mock library directory
        lib_dir = self.mock_mirror / "libs" / "test_lib"
        lib_dir.mkdir(parents=True)
        
        # Create some mock analog design files
        (lib_dir / "amplifier.sch").write_text("* Amplifier schematic\n.subckt amp in out\n.ends")
        (lib_dir / "amplifier.sym").write_text("v {xschem version=3.4.4}\nG {type=symbol}")
        (lib_dir / "testbench.sch").write_text("* Testbench\n.include amplifier.sch")
        
        # Create subdirectory with more files
        models_dir = lib_dir / "models"
        models_dir.mkdir()
        (models_dir / "nmos.sp").write_text(".model nmos_model nmos")
        (models_dir / "pmos.sp").write_text(".model pmos_model pmos")
        
        # Create a single file for single-file extraction tests
        (self.mock_mirror / "single_file.v").write_text("module test_module;\nendmodule")
    
    def test_extract_library_directory(self):
        """Test extracting a library directory."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib"
        )
        
        extraction_state = self.extractor.extract_library(
            library_name="test_lib",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        # Verify extraction state
        assert extraction_state.local_path == "designs/libs/test_lib"
        assert len(extraction_state.checksum) == 64
        
        # Verify files were copied
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        assert local_path.exists()
        assert (local_path / "amplifier.sch").exists()
        assert (local_path / "amplifier.sym").exists()
        assert (local_path / "models" / "nmos.sp").exists()
        
        # Verify checksum matches extraction state
        actual_checksum = ChecksumCalculator.calculate_directory_checksum(local_path)
        assert actual_checksum == extraction_state.checksum
    
    def test_extract_library_single_file(self):
        """Test extracting a single file."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="single_file.v"
        )
        
        extraction_state = self.extractor.extract_library(
            library_name="single_module",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        # Verify files were copied
        local_path = self.project_root / "designs" / "libs" / "single_module"
        assert local_path.exists()
        assert local_path.is_file()
        
        content = local_path.read_text()
        assert "module test_module" in content
        
        # Verify extraction state
        assert extraction_state.local_path == "designs/libs/single_module"
        assert len(extraction_state.checksum) == 64
    
    def test_extract_library_with_path_override(self):
        """Test extracting library with local_path override."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib",
            local_path="custom/location"
        )
        
        extraction_state = self.extractor.extract_library(
            library_name="test_lib",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        # Verify extraction to custom location
        local_path = self.project_root / "custom" / "location"
        assert local_path.exists()
        assert (local_path / "amplifier.sch").exists()
        assert extraction_state.local_path == "custom/location"
    
    def test_extract_library_missing_source(self):
        """Test extracting from nonexistent source path."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="nonexistent/path"
        )
        
        with pytest.raises(FileNotFoundError, match="Source path 'nonexistent/path' not found"):
            self.extractor.extract_library(
                library_name="test_lib",
                import_spec=import_spec,
                mirror_path=self.mock_mirror,
                library_root="designs/libs",
                repo_hash="abcd1234",
                resolved_commit="commit123456"
            )
    
    def test_extract_library_cleanup_on_failure(self):
        """Test that partial extraction is cleaned up on failure."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/nonexistent"  # Use nonexistent path to force failure
        )
        
        # This should fail because source_path doesn't exist in mock mirror
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_library(
                library_name="test_lib",
                import_spec=import_spec,
                mirror_path=self.mock_mirror,
                library_root="designs/libs",
                repo_hash="abcd1234",
                resolved_commit="commit123456"
            )
        
        # Verify cleanup occurred - library directory should not have been created
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        assert not local_path.exists(), "Library directory should not exist after extraction failure"