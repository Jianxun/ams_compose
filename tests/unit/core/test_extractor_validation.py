"""Unit tests for PathExtractor validation and management operations."""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from analog_hub.core.extractor import PathExtractor
from analog_hub.core.config import ImportSpec


class TestValidationOperations:
    """Test PathExtractor validation and management methods."""
    
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
    
    def test_validate_library_valid(self):
        """Test validating a valid library installation."""
        # First extract a library
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
        
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        
        # Validate the library
        validated_checksum = self.extractor.validate_library(local_path)
        assert validated_checksum is not None
        assert validated_checksum == extraction_state.checksum
    
    def test_validate_library_missing(self):
        """Test validating nonexistent library."""
        nonexistent_path = self.project_root / "nonexistent"
        checksum = self.extractor.validate_library(nonexistent_path)
        assert checksum is None
    
    def test_validate_library_no_metadata(self):
        """Test validating library without metadata file."""
        # Create library directory without metadata
        lib_path = self.project_root / "designs" / "libs" / "no_meta"
        lib_path.mkdir(parents=True)
        (lib_path / "file.txt").write_text("content")
        
        checksum = self.extractor.validate_library(lib_path)
        assert checksum is not None
        assert len(checksum) == 64
    
    def test_validate_library_modified_content(self):
        """Test validating library with modified content."""
        # First extract a library
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib"
        )
        
        original_state = self.extractor.extract_library(
            library_name="test_lib",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        
        # Modify the content
        (local_path / "amplifier.sch").write_text("modified content")
        
        # Validation should return different checksum
        new_checksum = self.extractor.validate_library(local_path)
        assert new_checksum is not None
        assert new_checksum != original_state.checksum
    
    def test_remove_library_directory(self):
        """Test removing an installed library directory."""
        # First extract a library
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib"
        )
        
        self.extractor.extract_library(
            library_name="test_lib",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        assert local_path.exists()
        
        # Remove the library
        removed = self.extractor.remove_library(local_path)
        assert removed is True
        assert not local_path.exists()
        
        # Try to remove again
        removed_again = self.extractor.remove_library(local_path)
        assert removed_again is False
    
    def test_remove_library_single_file(self):
        """Test removing a single file library."""
        # First extract a single file
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="single_file.v"
        )
        
        self.extractor.extract_library(
            library_name="single_module",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        local_path = self.project_root / "designs" / "libs" / "single_module"
        
        assert local_path.exists()
        
        # Remove the library
        removed = self.extractor.remove_library(local_path)
        assert removed is True
        assert not local_path.exists()
    
    def test_list_installed_libraries_empty(self):
        """Test listing libraries from empty directory."""
        libraries = self.extractor.list_installed_libraries("designs/libs")
        assert libraries == {}
    
    def test_list_installed_libraries_multiple(self):
        """Test listing multiple installed libraries."""
        # Extract multiple libraries
        import_specs = [
            ("lib1", ImportSpec(repo="https://example.com/repo1", ref="main", source_path="libs/test_lib")),
            ("lib2", ImportSpec(repo="https://example.com/repo2", ref="v1.0", source_path="single_file.v")),
        ]
        
        for lib_name, spec in import_specs:
            self.extractor.extract_library(
                library_name=lib_name,
                import_spec=spec,
                mirror_path=self.mock_mirror,
                library_root="designs/libs",
                repo_hash="abcd1234",
                resolved_commit="commit123456"
            )
        
        # List libraries
        libraries = self.extractor.list_installed_libraries("designs/libs")
        
        assert len(libraries) == 2
        assert "lib1" in libraries
        assert "lib2" in libraries
        
        # Verify they are Path objects pointing to the right locations
        assert libraries["lib1"].resolve() == (self.project_root / "designs" / "libs" / "lib1").resolve()
        assert libraries["lib2"].resolve() == (self.project_root / "designs" / "libs" / "lib2").resolve()
    
    def test_validate_library_exception_handling_directory(self):
        """Test exception handling during directory validation."""
        # Create a test library directory
        lib_path = self.project_root / "designs" / "libs" / "test_lib"
        lib_path.mkdir(parents=True)
        (lib_path / "file.txt").write_text("content")
        
        # Mock ChecksumCalculator to raise exception
        with patch('analog_hub.core.extractor.ChecksumCalculator.calculate_directory_checksum') as mock_calc:
            mock_calc.side_effect = OSError("Permission denied")
            
            checksum = self.extractor.validate_library(lib_path)
            assert checksum is None
    
    def test_validate_library_exception_handling_file(self):
        """Test exception handling during single file validation."""
        # Create a test single file library
        lib_path = self.project_root / "designs" / "libs" / "single.sp"
        lib_path.parent.mkdir(parents=True)
        lib_path.write_text("spice content")
        
        # Mock ChecksumCalculator to raise exception
        with patch('analog_hub.core.extractor.ChecksumCalculator.calculate_file_checksum') as mock_calc:
            mock_calc.side_effect = OSError("Permission denied")
            
            checksum = self.extractor.validate_library(lib_path)
            assert checksum is None
    
    def test_remove_library_exception_handling_directory(self):
        """Test exception handling during directory removal."""
        # Create a test library directory
        lib_path = self.project_root / "designs" / "libs" / "test_lib"
        lib_path.mkdir(parents=True)
        (lib_path / "file.txt").write_text("content")
        
        # Verify it exists
        assert lib_path.exists()
        
        # Mock shutil.rmtree to raise exception
        with patch('shutil.rmtree') as mock_rmtree:
            mock_rmtree.side_effect = OSError("Permission denied")
            
            result = self.extractor.remove_library(lib_path)
            assert result is False
            # Directory should still exist since removal failed
            assert lib_path.exists()
    
    def test_remove_library_exception_handling_file(self):
        """Test exception handling during file removal."""
        # Create a test single file library
        lib_path = self.project_root / "designs" / "libs" / "single.sp"
        lib_path.parent.mkdir(parents=True)
        lib_path.write_text("spice content")
        
        # Verify it exists
        assert lib_path.exists()
        
        # Mock Path.unlink to raise exception
        with patch.object(Path, 'unlink') as mock_unlink:
            mock_unlink.side_effect = OSError("Permission denied")
            
            result = self.extractor.remove_library(lib_path)
            assert result is False
            # File should still exist since removal failed
            assert lib_path.exists()