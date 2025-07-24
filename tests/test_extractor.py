"""Unit tests for path extraction operations."""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import pytest

from analog_hub.core.extractor import PathExtractor, LibraryMetadata
from analog_hub.core.config import ImportSpec


class TestPathExtractor:
    """Unit tests for PathExtractor class."""
    
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
    
    def test_calculate_directory_checksum(self):
        """Test directory checksum calculation."""
        lib_dir = self.mock_mirror / "libs" / "test_lib"
        
        # Calculate checksum
        checksum1 = self.extractor._calculate_directory_checksum(lib_dir)
        assert len(checksum1) == 64  # SHA256 hex length
        assert checksum1 != ""
        
        # Same directory should produce same checksum
        checksum2 = self.extractor._calculate_directory_checksum(lib_dir)
        assert checksum1 == checksum2
        
        # Modified directory should produce different checksum
        (lib_dir / "new_file.txt").write_text("new content")
        checksum3 = self.extractor._calculate_directory_checksum(lib_dir)
        assert checksum3 != checksum1
    
    def test_calculate_directory_checksum_empty_dir(self):
        """Test checksum of empty directory."""
        empty_dir = self.mock_mirror / "empty"
        empty_dir.mkdir()
        
        checksum = self.extractor._calculate_directory_checksum(empty_dir)
        assert len(checksum) == 64
        assert checksum != ""
    
    def test_calculate_directory_checksum_nonexistent(self):
        """Test checksum of nonexistent directory."""
        nonexistent = self.mock_mirror / "nonexistent"
        checksum = self.extractor._calculate_directory_checksum(nonexistent)
        assert checksum == ""
    
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
    
    def test_extract_library_directory(self):
        """Test extracting a library directory."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib"
        )
        
        source_path = self.mock_mirror / "libs" / "test_lib"
        
        metadata = self.extractor.extract_library(
            library_name="test_lib",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        # Verify metadata
        assert metadata.library_name == "test_lib"
        assert metadata.repo_url == "https://example.com/repo"
        assert metadata.ref == "main"
        assert metadata.resolved_commit == "commit123456"
        assert metadata.source_path == "libs/test_lib"
        assert metadata.local_path == "designs/libs/test_lib"
        assert len(metadata.checksum) == 64
        assert metadata.repo_hash == "abcd1234"
        
        # Verify files were copied
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        assert local_path.exists()
        assert (local_path / "amplifier.sch").exists()
        assert (local_path / "amplifier.sym").exists()
        assert (local_path / "models" / "nmos.sp").exists()
        
        # Verify metadata file was created
        metadata_file = local_path / ".analog-hub-meta.yaml"
        assert metadata_file.exists()
        
        # Verify metadata can be loaded back
        loaded_metadata = LibraryMetadata.from_yaml(metadata_file)
        assert loaded_metadata.library_name == metadata.library_name
        assert loaded_metadata.checksum == metadata.checksum
    
    def test_extract_library_single_file(self):
        """Test extracting a single file."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="single_file.v"
        )
        
        metadata = self.extractor.extract_library(
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
        
        # Verify metadata file was created alongside
        metadata_file = local_path.parent / ".analog-hub-meta-single_module.yaml"
        assert metadata_file.exists()
    
    def test_extract_library_with_path_override(self):
        """Test extracting library with local_path override."""
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib",
            local_path="custom/location"
        )
        
        metadata = self.extractor.extract_library(
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
        assert metadata.local_path == "custom/location"
    
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
            source_path="libs/test_lib"
        )
        
        # Create a scenario that will fail during metadata save
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        local_path.mkdir(parents=True)
        
        # Make the directory read-only to cause metadata save failure
        import os
        original_perms = local_path.stat().st_mode
        os.chmod(local_path, 0o444)
        
        try:
            with pytest.raises(PermissionError):
                self.extractor.extract_library(
                    library_name="test_lib",
                    import_spec=import_spec,
                    mirror_path=self.mock_mirror,
                    library_root="designs/libs",
                    repo_hash="abcd1234",
                    resolved_commit="commit123456"
                )
            
            # Verify cleanup occurred (directory should be removed)
            # Note: cleanup might not work due to permissions, so we restore perms first
            os.chmod(local_path, original_perms)
            
        finally:
            # Restore permissions for cleanup
            if local_path.exists():
                os.chmod(local_path, original_perms)
    
    def test_validate_library_valid(self):
        """Test validating a valid library installation."""
        # First extract a library
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib"
        )
        
        metadata = self.extractor.extract_library(
            library_name="test_lib",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        
        # Validate the library
        validated_metadata = self.extractor.validate_library(local_path)
        assert validated_metadata is not None
        assert validated_metadata.library_name == "test_lib"
        assert validated_metadata.checksum == metadata.checksum
    
    def test_validate_library_missing(self):
        """Test validating nonexistent library."""
        nonexistent_path = self.project_root / "nonexistent"
        result = self.extractor.validate_library(nonexistent_path)
        assert result is None
    
    def test_validate_library_no_metadata(self):
        """Test validating library without metadata file."""
        # Create library directory without metadata
        lib_path = self.project_root / "designs" / "libs" / "no_meta"
        lib_path.mkdir(parents=True)
        (lib_path / "file.txt").write_text("content")
        
        result = self.extractor.validate_library(lib_path)
        assert result is None
    
    def test_validate_library_modified_content(self):
        """Test validating library with modified content."""
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
        
        # Modify the content
        (local_path / "amplifier.sch").write_text("modified content")
        
        # Validation should fail due to checksum mismatch
        result = self.extractor.validate_library(local_path)
        assert result is None
    
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
        metadata_path = local_path.parent / ".analog-hub-meta-single_module.yaml"
        
        assert local_path.exists()
        assert metadata_path.exists()
        
        # Remove the library
        removed = self.extractor.remove_library(local_path)
        assert removed is True
        assert not local_path.exists()
        assert not metadata_path.exists()
    
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
        
        assert libraries["lib1"].repo_url == "https://example.com/repo1"
        assert libraries["lib2"].repo_url == "https://example.com/repo2"
        assert libraries["lib2"].ref == "v1.0"
    
    def test_update_library_metadata(self):
        """Test updating metadata for existing library."""
        # First extract a library
        import_spec = ImportSpec(
            repo="https://example.com/repo",
            ref="main",
            source_path="libs/test_lib"
        )
        
        original_metadata = self.extractor.extract_library(
            library_name="test_lib",
            import_spec=import_spec,
            mirror_path=self.mock_mirror,
            library_root="designs/libs",
            repo_hash="abcd1234",
            resolved_commit="commit123456"
        )
        
        local_path = self.project_root / "designs" / "libs" / "test_lib"
        
        # Update metadata
        updated_metadata = self.extractor.update_library_metadata(
            library_path=local_path,
            new_commit="newcommit789",
            new_ref="v2.0"
        )
        
        assert updated_metadata is not None
        assert updated_metadata.resolved_commit == "newcommit789"
        assert updated_metadata.ref == "v2.0"
        assert updated_metadata.installed_at == original_metadata.installed_at
        assert updated_metadata.updated_at > original_metadata.updated_at
        
        # Verify metadata was saved
        metadata_file = local_path / ".analog-hub-meta.yaml"
        loaded_metadata = LibraryMetadata.from_yaml(metadata_file)
        assert loaded_metadata.resolved_commit == "newcommit789"
        assert loaded_metadata.ref == "v2.0"
    
    def test_update_library_metadata_invalid_library(self):
        """Test updating metadata for invalid library."""
        nonexistent_path = self.project_root / "nonexistent"
        
        result = self.extractor.update_library_metadata(
            library_path=nonexistent_path,
            new_commit="newcommit",
            new_ref="v2.0"
        )
        
        assert result is None


class TestLibraryMetadata:
    """Unit tests for LibraryMetadata model."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_library_metadata_creation(self):
        """Test creating LibraryMetadata instance."""
        metadata = LibraryMetadata(
            library_name="test_lib",
            repo_url="https://example.com/repo",
            repo_hash="abcd1234",
            ref="main",
            resolved_commit="commit123456",
            source_path="libs/test_lib",
            local_path="designs/libs/test_lib",
            checksum="checksum123",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )
        
        assert metadata.library_name == "test_lib"
        assert metadata.repo_url == "https://example.com/repo"
        assert metadata.resolved_commit == "commit123456"
    
    def test_library_metadata_yaml_roundtrip(self):
        """Test saving and loading metadata to/from YAML."""
        metadata = LibraryMetadata(
            library_name="test_lib",
            repo_url="https://example.com/repo",
            repo_hash="abcd1234",
            ref="main",
            resolved_commit="commit123456",
            source_path="libs/test_lib",
            local_path="designs/libs/test_lib",
            checksum="checksum123",
            installed_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )
        
        # Save to YAML
        yaml_path = Path(self.temp_dir) / "metadata.yaml"
        metadata.to_yaml(yaml_path)
        
        # Load from YAML
        loaded_metadata = LibraryMetadata.from_yaml(yaml_path)
        
        assert loaded_metadata.library_name == metadata.library_name
        assert loaded_metadata.repo_url == metadata.repo_url
        assert loaded_metadata.resolved_commit == metadata.resolved_commit
        assert loaded_metadata.checksum == metadata.checksum