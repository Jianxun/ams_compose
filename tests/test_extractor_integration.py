"""Integration tests for path extraction with real repositories and analog-hub.yaml."""

import tempfile
import shutil
from pathlib import Path

import pytest

from analog_hub.core.extractor import PathExtractor
from analog_hub.core.mirror import RepositoryMirror
from analog_hub.core.config import AnalogHubConfig


class TestExtractorIntegration:
    """Integration tests using real repositories and analog-hub.yaml configuration."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "project"
        self.project_root.mkdir()
        
        self.mirror_root = Path(self.temp_dir) / "mirrors"
        self.mirror = RepositoryMirror(self.mirror_root)
        self.extractor = PathExtractor(self.project_root)
        
        # Load the actual analog-hub.yaml configuration
        config_path = Path("analog-hub.yaml")
        if config_path.exists():
            self.config = AnalogHubConfig.from_yaml(config_path)
        else:
            pytest.skip("analog-hub.yaml configuration file not found")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.slow
    def test_extract_model_pll_from_config(self):
        """Test extracting model_pll library using analog-hub.yaml configuration."""
        # Get the model_pll import specification
        assert "model_pll" in self.config.imports, "model_pll not found in analog-hub.yaml"
        import_spec = self.config.imports["model_pll"]
        
        print(f"Testing extraction of {import_spec.repo}")
        print(f"  Branch: {import_spec.ref}")
        print(f"  Source path: {import_spec.source_path}")
        
        # Create mirror for the repository
        mirror_metadata = self.mirror.create_mirror(import_spec.repo, import_spec.ref)
        mirror_path = self.mirror.get_mirror_path(import_spec.repo)
        
        # Verify mirror was created successfully
        assert mirror_path.exists()
        assert mirror_metadata.resolved_commit
        
        # Extract the library
        library_metadata = self.extractor.extract_library(
            library_name="model_pll",
            import_spec=import_spec,
            mirror_path=mirror_path,
            library_root=self.config.library_root,
            repo_hash=mirror_metadata.repo_hash,
            resolved_commit=mirror_metadata.resolved_commit
        )
        
        # Verify extraction results
        assert library_metadata.library_name == "model_pll"
        assert library_metadata.repo_url == import_spec.repo
        assert library_metadata.ref == import_spec.ref
        assert library_metadata.source_path == import_spec.source_path
        
        # Verify local installation path
        expected_local_path = self.project_root / self.config.library_root / "model_pll"
        actual_local_path = self.project_root / library_metadata.local_path
        assert actual_local_path == expected_local_path
        assert actual_local_path.exists()
        assert actual_local_path.is_dir()
        
        # Verify specific analog design files were extracted
        expected_files = [
            "amplifier.sch", "amplifier.sym",  # Common analog design files
            "CP_model.sch", "CP_model.sym",    # Charge pump files
            "vco_model.sch", "vco_model.sym",  # VCO files
            "pfd_model.sch", "pfd_model.sym"   # Phase-frequency detector files
        ]
        
        found_files = []
        for pattern in ["*.sch", "*.sym", "*.sp", "*.cir"]:
            found_files.extend([f.name for f in actual_local_path.rglob(pattern)])
        
        print(f"✅ Found {len(found_files)} analog design files:")
        for file_name in sorted(found_files):
            print(f"  - {file_name}")
        
        # Verify we found some expected PLL modeling files
        pll_files = [f for f in found_files if any(keyword in f.lower() for keyword in ["pll", "vco", "pfd", "cp"])]
        assert len(pll_files) > 0, f"Expected PLL-related files, found: {found_files}"
        
        # Verify metadata file was created
        metadata_file = actual_local_path / ".analog-hub-meta.yaml"
        assert metadata_file.exists()
        
        # Test validation
        validated_metadata = self.extractor.validate_library(actual_local_path)
        assert validated_metadata is not None
        assert validated_metadata.library_name == "model_pll"
        
        print(f"✅ Model PLL extraction successful:")
        print(f"  Repository: {library_metadata.repo_url}")
        print(f"  Commit: {library_metadata.resolved_commit}")
        print(f"  Local path: {library_metadata.local_path}")
        print(f"  Files extracted: {len(found_files)}")
        print(f"  Checksum: {library_metadata.checksum[:16]}...")
    
    @pytest.mark.slow
    def test_extract_switch_matrix_from_config(self):
        """Test extracting switch_matrix_gf180mcu_9t5v0 library using analog-hub.yaml."""
        # Get the switch matrix import specification
        assert "switch_matrix_gf180mcu_9t5v0" in self.config.imports
        import_spec = self.config.imports["switch_matrix_gf180mcu_9t5v0"]
        
        print(f"Testing extraction of {import_spec.repo}")
        print(f"  Branch: {import_spec.ref}")
        print(f"  Source path: {import_spec.source_path}")
        
        # Create mirror for the repository
        mirror_metadata = self.mirror.create_mirror(import_spec.repo, import_spec.ref)
        mirror_path = self.mirror.get_mirror_path(import_spec.repo)
        
        # Extract the library (entire repository since source_path is ".")
        library_metadata = self.extractor.extract_library(
            library_name="switch_matrix_gf180mcu_9t5v0",
            import_spec=import_spec,
            mirror_path=mirror_path,
            library_root=self.config.library_root,
            repo_hash=mirror_metadata.repo_hash,
            resolved_commit=mirror_metadata.resolved_commit
        )
        
        # Verify extraction results
        assert library_metadata.library_name == "switch_matrix_gf180mcu_9t5v0"
        assert library_metadata.source_path == "."
        
        # Verify local installation
        expected_local_path = self.project_root / self.config.library_root / "switch_matrix_gf180mcu_9t5v0"
        actual_local_path = self.project_root / library_metadata.local_path
        assert actual_local_path == expected_local_path
        assert actual_local_path.exists()
        
        # Look for typical analog design files
        design_files = []
        for pattern in ["*.v", "*.sv", "*.spice", "*.cir", "*.sch", "*.mag", "*.gds", "*.lef", "*.lib"]:
            design_files.extend([f.name for f in actual_local_path.rglob(pattern)])
        
        print(f"✅ Found {len(design_files)} design files:")
        for file_name in sorted(design_files)[:10]:  # Show first 10 files
            print(f"  - {file_name}")
        if len(design_files) > 10:
            print(f"  ... and {len(design_files) - 10} more files")
        
        # Verify we found analog design files
        assert len(design_files) > 0, "Expected to find analog design files"
        
        # Verify metadata file was created
        metadata_file = actual_local_path / ".analog-hub-meta.yaml"
        assert metadata_file.exists()
        
        print(f"✅ Switch Matrix extraction successful:")
        print(f"  Repository: {library_metadata.repo_url}")
        print(f"  Commit: {library_metadata.resolved_commit}")
        print(f"  Local path: {library_metadata.local_path}")
        print(f"  Design files: {len(design_files)}")
    
    @pytest.mark.slow
    def test_extract_multiple_libraries_from_config(self):
        """Test extracting multiple libraries from analog-hub.yaml configuration."""
        extracted_libraries = {}
        
        # Extract all libraries defined in config
        for library_name, import_spec in self.config.imports.items():
            print(f"\n🔄 Extracting {library_name}...")
            
            # Create mirror
            mirror_metadata = self.mirror.create_mirror(import_spec.repo, import_spec.ref)
            mirror_path = self.mirror.get_mirror_path(import_spec.repo)
            
            # Extract library
            library_metadata = self.extractor.extract_library(
                library_name=library_name,
                import_spec=import_spec,
                mirror_path=mirror_path,
                library_root=self.config.library_root,
                repo_hash=mirror_metadata.repo_hash,
                resolved_commit=mirror_metadata.resolved_commit
            )
            
            extracted_libraries[library_name] = library_metadata
            
            # Verify installation
            local_path = self.project_root / library_metadata.local_path
            assert local_path.exists()
            
            # Count files
            all_files = list(local_path.rglob("*"))
            file_count = len([f for f in all_files if f.is_file()])
            
            print(f"  ✅ {library_name}: {file_count} files extracted to {library_metadata.local_path}")
        
        # Verify all libraries were extracted
        assert len(extracted_libraries) == len(self.config.imports)
        
        # Test listing installed libraries
        installed_libraries = self.extractor.list_installed_libraries(self.config.library_root)
        assert len(installed_libraries) == len(self.config.imports)
        
        for library_name in self.config.imports.keys():
            assert library_name in installed_libraries
            metadata = installed_libraries[library_name]
            assert metadata.library_name == library_name
            assert len(metadata.resolved_commit) == 40  # SHA hash length
        
        print(f"\n✅ Multiple library extraction successful:")
        print(f"  Libraries extracted: {len(extracted_libraries)}")
        print(f"  Configuration libraries: {len(self.config.imports)}")
        for name, metadata in installed_libraries.items():
            print(f"  - {name}: {metadata.resolved_commit[:8]}... -> {metadata.local_path}")
    
    @pytest.mark.slow
    def test_library_update_workflow(self):
        """Test updating an existing library installation."""
        # Use model_pll for this test
        library_name = "model_pll"
        import_spec = self.config.imports[library_name]
        
        # Initial extraction
        mirror_metadata = self.mirror.create_mirror(import_spec.repo, import_spec.ref)
        mirror_path = self.mirror.get_mirror_path(import_spec.repo)
        
        initial_metadata = self.extractor.extract_library(
            library_name=library_name,
            import_spec=import_spec,
            mirror_path=mirror_path,
            library_root=self.config.library_root,
            repo_hash=mirror_metadata.repo_hash,
            resolved_commit=mirror_metadata.resolved_commit
        )
        
        local_path = self.project_root / initial_metadata.local_path
        assert local_path.exists()
        
        # Simulate update by "updating" mirror (refetch)
        updated_mirror_metadata = self.mirror.update_mirror(import_spec.repo, import_spec.ref)
        
        # Re-extract (simulating update)
        updated_library_metadata = self.extractor.extract_library(
            library_name=library_name,
            import_spec=import_spec,
            mirror_path=mirror_path,
            library_root=self.config.library_root,
            repo_hash=updated_mirror_metadata.repo_hash,
            resolved_commit=updated_mirror_metadata.resolved_commit
        )
        
        # Verify update
        assert updated_library_metadata.resolved_commit == initial_metadata.resolved_commit  # Same ref
        assert updated_library_metadata.updated_at >= initial_metadata.updated_at
        assert local_path.exists()
        
        # Verify library can still be validated
        validated_metadata = self.extractor.validate_library(local_path)
        assert validated_metadata is not None
        assert validated_metadata.resolved_commit == updated_library_metadata.resolved_commit
        
        print(f"✅ Library update workflow successful:")
        print(f"  Library: {library_name}")
        print(f"  Initial commit: {initial_metadata.resolved_commit}")
        print(f"  Updated commit: {updated_library_metadata.resolved_commit}")
        print(f"  Install time: {initial_metadata.installed_at}")
        print(f"  Update time: {updated_library_metadata.updated_at}")
    
    def test_config_loading_and_validation(self):
        """Test that analog-hub.yaml loads correctly and has expected structure."""
        # Verify config was loaded
        assert self.config is not None
        assert hasattr(self.config, 'library_root')
        assert hasattr(self.config, 'imports')
        
        # Verify library_root
        assert self.config.library_root == "designs/libs"
        
        # Verify expected imports exist
        expected_imports = ["model_pll", "switch_matrix_gf180mcu_9t5v0"]
        for import_name in expected_imports:
            assert import_name in self.config.imports, f"Missing import: {import_name}"
            
            import_spec = self.config.imports[import_name]
            assert hasattr(import_spec, 'repo')
            assert hasattr(import_spec, 'ref')
            assert hasattr(import_spec, 'source_path')
            
            # Verify URLs are valid
            assert import_spec.repo.startswith(('https://', 'git@'))
            assert len(import_spec.ref) > 0
            assert len(import_spec.source_path) > 0
        
        # Verify specific configurations
        model_pll = self.config.imports["model_pll"]
        assert model_pll.repo == "https://github.com/peterkinget/testing-project-template"
        assert model_pll.ref == "PK_PLL_modeling"
        assert model_pll.source_path == "designs/libs/model_pll"
        
        switch_matrix = self.config.imports["switch_matrix_gf180mcu_9t5v0"]
        assert switch_matrix.repo == "https://github.com/mosbiuschip/switch_matrix_gf180mcu_9t5v0"
        assert switch_matrix.ref == "main"
        assert switch_matrix.source_path == "."
        
        print(f"✅ Configuration validation successful:")
        print(f"  Library root: {self.config.library_root}")
        print(f"  Imports defined: {len(self.config.imports)}")
        for name, spec in self.config.imports.items():
            print(f"  - {name}: {spec.repo} ({spec.ref}) -> {spec.source_path}")