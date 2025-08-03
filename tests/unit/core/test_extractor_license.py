"""Test license file inclusion and provenance metadata generation."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import yaml

from ams_compose.core.extractor import PathExtractor
from ams_compose.core.config import ImportSpec
from ams_compose.utils.license import LicenseInfo


class TestLicenseFileInclusion:
    """Test license file preservation during extraction."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def temp_mirror(self):
        """Create temporary mirror directory with test content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mirror_path = Path(temp_dir)
            
            # Create test library structure
            lib_dir = mirror_path / "test_lib"
            lib_dir.mkdir()
            
            # Create some regular files
            (lib_dir / "main.py").write_text("# Main file")
            (lib_dir / "config.yaml").write_text("setting: value")
            
            # Create LICENSE file
            (lib_dir / "LICENSE").write_text("MIT License\n\nCopyright (c) 2024")
            
            # Create some files that should be ignored
            (lib_dir / ".git").mkdir()
            (lib_dir / ".git" / "config").write_text("git config")
            (lib_dir / "__pycache__").mkdir()
            (lib_dir / "__pycache__" / "cache.pyc").write_text("cache")
            
            yield mirror_path
    
    @pytest.fixture
    def extractor(self, temp_project):
        """Create PathExtractor instance."""
        return PathExtractor(temp_project)
    
    def test_license_file_preserved_when_checkin_true(self, extractor, temp_mirror, temp_project):
        """Test that LICENSE files are preserved when checkin=True."""
        import_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path="test_lib",
            checkin=True  # Enable checkin
        )
        
        with patch.object(extractor.license_detector, 'detect_license') as mock_detect:
            mock_detect.return_value = LicenseInfo(
                license_type="MIT",
                license_file="LICENSE",
                content_snippet="MIT License\n\nCopyright (c) 2024"
            )
            
            result = extractor.extract_library(
                library_name="test_lib",
                import_spec=import_spec,
                mirror_path=temp_mirror,
                library_root="libs",
                repo_hash="abc123",
                resolved_commit="commit123"
            )
        
        # Check that extraction was successful
        local_path = temp_project / result.local_path
        assert local_path.exists()
        
        # Check that LICENSE file was preserved
        license_file = local_path / "LICENSE"
        assert license_file.exists()
        assert "MIT License" in license_file.read_text()
        
        # Check that git and cache files were ignored
        assert not (local_path / ".git").exists()
        assert not (local_path / "__pycache__").exists()
        
        # Check that metadata file was created
        metadata_file = local_path / ".ams-compose-metadata.yaml"
        assert metadata_file.exists()
    
    def test_license_file_ignored_when_checkin_false(self, extractor, temp_mirror, temp_project):
        """Test that LICENSE files follow normal ignore rules when checkin=False."""
        import_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path="test_lib",
            checkin=False,  # Disable checkin
            ignore_patterns=['LICENSE']  # Explicitly ignore LICENSE
        )
        
        result = extractor.extract_library(
            library_name="test_lib",
            import_spec=import_spec,
            mirror_path=temp_mirror,
            library_root="libs",
            repo_hash="abc123",
            resolved_commit="commit123"
        )
        
        # Check that extraction was successful
        local_path = temp_project / result.local_path
        assert local_path.exists()
        
        # Check that LICENSE file was ignored due to ignore_patterns
        license_file = local_path / "LICENSE"
        assert not license_file.exists()
        
        # Check that metadata file was created (even for checkin=false)
        metadata_file = local_path / ".ams-compose-metadata.yaml"
        assert metadata_file.exists()
    
    def test_license_file_preserved_despite_ignore_patterns_when_checkin_true(self, extractor, temp_mirror, temp_project):
        """Test that LICENSE files are preserved even if listed in ignore patterns when checkin=True."""
        import_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path="test_lib",
            checkin=True,  # Enable checkin
            ignore_patterns=['LICENSE', '*.md']  # Try to ignore LICENSE
        )
        
        with patch.object(extractor.license_detector, 'detect_license') as mock_detect:
            mock_detect.return_value = LicenseInfo(
                license_type="MIT",
                license_file="LICENSE",
                content_snippet="MIT License"
            )
            
            result = extractor.extract_library(
                library_name="test_lib",
                import_spec=import_spec,
                mirror_path=temp_mirror,
                library_root="libs",
                repo_hash="abc123",
                resolved_commit="commit123"
            )
        
        # Check that extraction was successful
        local_path = temp_project / result.local_path
        assert local_path.exists()
        
        # Check that LICENSE file was preserved despite being in ignore_patterns
        license_file = local_path / "LICENSE"
        assert license_file.exists()
        assert "MIT License" in license_file.read_text()
    
    def test_multiple_license_files_preserved(self, extractor, temp_project):
        """Test that multiple LICENSE file formats are preserved."""
        # Create mirror with multiple license files
        with tempfile.TemporaryDirectory() as temp_dir:
            mirror_path = Path(temp_dir)
            lib_dir = mirror_path / "test_lib"
            lib_dir.mkdir()
            
            # Create multiple license files
            (lib_dir / "LICENSE").write_text("MIT License")
            (lib_dir / "LICENSE.txt").write_text("MIT License Text")
            (lib_dir / "COPYING").write_text("GPL License")
            (lib_dir / "regular_file.py").write_text("print('hello')")
            
            import_spec = ImportSpec(
                repo="https://github.com/test/repo.git",
                ref="main",
                source_path="test_lib",
                checkin=True
            )
            
            with patch.object(extractor.license_detector, 'detect_license') as mock_detect:
                mock_detect.return_value = LicenseInfo(
                    license_type="MIT",
                    license_file="LICENSE",
                    content_snippet="MIT License"
                )
                
                result = extractor.extract_library(
                    library_name="test_lib",
                    import_spec=import_spec,
                    mirror_path=mirror_path,
                    library_root="libs",
                    repo_hash="abc123",
                    resolved_commit="commit123"
                )
            
            # Check that all license files were preserved
            local_path = temp_project / result.local_path
            assert (local_path / "LICENSE").exists()
            assert (local_path / "LICENSE.txt").exists()
            assert (local_path / "COPYING").exists()
            assert (local_path / "regular_file.py").exists()


class TestProvenanceMetadata:
    """Test provenance metadata generation."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def temp_mirror(self):
        """Create temporary mirror directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mirror_path = Path(temp_dir)
            lib_dir = mirror_path / "test_lib"
            lib_dir.mkdir()
            (lib_dir / "main.py").write_text("print('hello')")
            (lib_dir / "LICENSE").write_text("MIT License\n\nCopyright (c) 2024")
            yield mirror_path
    
    @pytest.fixture
    def extractor(self, temp_project):
        """Create PathExtractor instance."""
        return PathExtractor(temp_project)
    
    def test_provenance_metadata_generated_for_checkin_true(self, extractor, temp_mirror, temp_project):
        """Test that provenance metadata is generated when checkin=True."""
        import_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="v1.0.0",
            source_path="test_lib",
            checkin=True
        )
        
        with patch.object(extractor.license_detector, 'detect_license') as mock_detect:
            mock_detect.return_value = LicenseInfo(
                license_type="MIT",
                license_file="LICENSE",
                content_snippet="MIT License\n\nCopyright (c) 2024"
            )
            
            result = extractor.extract_library(
                library_name="my_library",
                import_spec=import_spec,
                mirror_path=temp_mirror,
                library_root="libs",
                repo_hash="abc123",
                resolved_commit="commit456"
            )
        
        # Check that metadata file was created
        local_path = temp_project / result.local_path
        metadata_file = local_path / ".ams-compose-metadata.yaml"
        assert metadata_file.exists()
        
        # Parse and validate provenance content
        with open(provenance_file, 'r') as f:
            provenance = yaml.safe_load(f)
        
        # Validate structure and content
        assert 'ams_compose_version' in provenance
        assert 'extraction_timestamp' in provenance
        assert provenance['library_name'] == 'my_library'
        
        assert provenance['source']['repository'] == 'https://github.com/test/repo.git'
        assert provenance['source']['reference'] == 'v1.0.0'
        assert provenance['source']['commit'] == 'commit456'
        assert provenance['source']['source_path'] == 'test_lib'
        
        assert provenance['license']['type'] == 'MIT'
        assert provenance['license']['file'] == 'LICENSE'
        assert 'MIT License' in provenance['license']['snippet']
        
        assert isinstance(provenance['compliance_notes'], list)
        assert len(provenance['compliance_notes']) > 0
        
        # Check timestamp format (ISO 8601 with Z suffix)
        assert provenance['extraction_timestamp'].endswith('Z')
    
    def test_provenance_metadata_not_generated_for_checkin_false(self, extractor, temp_mirror, temp_project):
        """Test that provenance metadata is not generated when checkin=False."""
        import_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path="test_lib",
            checkin=False  # Disable checkin
        )
        
        result = extractor.extract_library(
            library_name="my_library",
            import_spec=import_spec,
            mirror_path=temp_mirror,
            library_root="libs",
            repo_hash="abc123",
            resolved_commit="commit456"
        )
        
        # Check that metadata file was created (even for checkin=false)
        local_path = temp_project / result.local_path
        metadata_file = local_path / ".ams-compose-metadata.yaml"
        assert metadata_file.exists()
    
    def test_provenance_metadata_not_generated_for_single_file(self, extractor, temp_project):
        """Test that provenance metadata is not generated for single file extractions."""
        # Create single file mirror
        with tempfile.TemporaryDirectory() as temp_dir:
            mirror_path = Path(temp_dir)
            single_file = mirror_path / "script.py"
            single_file.write_text("print('hello world')")
            
            import_spec = ImportSpec(
                repo="https://github.com/test/repo.git",
                ref="main",
                source_path="script.py",
                checkin=True  # Even with checkin=True
            )
            
            result = extractor.extract_library(
                library_name="my_script",
                import_spec=import_spec,
                mirror_path=mirror_path,
                library_root="libs",
                repo_hash="abc123",
                resolved_commit="commit456"
            )
            
            # Single file should be extracted
            local_path = temp_project / result.local_path
            assert local_path.exists()
            assert local_path.is_file()
            
            # But no metadata file should be created (only for directories)
            metadata_file = local_path.parent / ".ams-compose-metadata.yaml"
            assert not metadata_file.exists()
    
    def test_provenance_handles_license_detection_failure(self, extractor, temp_mirror, temp_project):
        """Test provenance generation when license detection fails."""
        import_spec = ImportSpec(
            repo="https://github.com/test/repo.git",
            ref="main",
            source_path="test_lib",
            checkin=True
        )
        
        with patch.object(extractor.license_detector, 'detect_license') as mock_detect:
            # Simulate license detection failure
            mock_detect.return_value = LicenseInfo(
                license_type=None,
                license_file=None,
                content_snippet=None
            )
            
            result = extractor.extract_library(
                library_name="my_library",
                import_spec=import_spec,
                mirror_path=temp_mirror,
                library_root="libs",
                repo_hash="abc123",
                resolved_commit="commit456"
            )
        
        # Check that metadata file was still created
        local_path = temp_project / result.local_path
        metadata_file = local_path / ".ams-compose-metadata.yaml"
        assert metadata_file.exists()
        
        # Parse and validate that None values are handled properly
        with open(provenance_file, 'r') as f:
            provenance = yaml.safe_load(f)
        
        assert provenance['license']['type'] is None
        assert provenance['license']['file'] is None
        assert provenance['license']['snippet'] is None