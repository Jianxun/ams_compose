"""End-to-end tests for license file inclusion and provenance metadata."""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any

from ams_compose.core.installer import LibraryInstaller
from ams_compose.core.config import ComposeConfig


class TestLicenseFileInclusionE2E:
    """End-to-end tests for license file inclusion feature."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            yield project_path
    
    @pytest.fixture
    def mock_repo(self):
        """Create mock repository with license files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create library directory with various files
            lib_dir = repo_path / "analog_lib"
            lib_dir.mkdir()
            
            # Create main library files
            (lib_dir / "main.sv").write_text("// Main SystemVerilog file\nmodule main();\nendmodule")
            (lib_dir / "config.yaml").write_text("library_version: 1.0\nsettings:\n  voltage: 3.3V")
            (lib_dir / "README.md").write_text("# Analog Library\nThis is a test library.")
            
            # Create LICENSE file in library directory
            license_content = """MIT License

Copyright (c) 2024 Analog IC Design Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:"""
            (lib_dir / "LICENSE").write_text(license_content)
            
            # Also create LICENSE at repo root for license detection
            (repo_path / "LICENSE").write_text(license_content)
            
            # Create files that should be ignored
            vcs_dir = lib_dir / ".git"
            vcs_dir.mkdir()
            (vcs_dir / "config").write_text("git config content")
            
            cache_dir = lib_dir / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "cache.pyc").write_text("cache content")
            
            (lib_dir / ".DS_Store").write_text("mac metadata")
            
            yield repo_path
    
    def _create_test_config(self, project_path: Path, imports_config: Dict[str, Any]) -> None:
        """Create test configuration file."""
        config_data = {
            'library_root': 'designs/libs',
            'imports': imports_config
        }
        
        config_path = project_path / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
    
    def _create_mock_mirror(self, installer: LibraryInstaller, repo_url: str, mock_repo_path: Path):
        """Create mock mirror by copying mock repo."""
        mirror_path = installer.mirror_manager.get_mirror_path(repo_url)
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing mirror if it exists
        if mirror_path.exists():
            shutil.rmtree(mirror_path)
            
        shutil.copytree(mock_repo_path, mirror_path)
        
        # Create minimal git structure for mirror validation
        git_dir = mirror_path / ".git"
        git_dir.mkdir(exist_ok=True)
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    
    def test_license_preserved_for_checkin_true_library(self, temp_project, mock_repo):
        """Test that LICENSE files are preserved for checkin=true libraries."""
        # Create configuration with checkin=true library
        imports_config = {
            'analog_design_lib': {
                'repo': 'https://github.com/test/analog-lib.git',
                'ref': 'main',
                'source_path': 'analog_lib',
                'checkin': True  # Enable checkin
            }
        }
        self._create_test_config(temp_project, imports_config)
        
        # Create installer and mock mirror
        installer = LibraryInstaller(temp_project)
        self._create_mock_mirror(installer, imports_config['analog_design_lib']['repo'], mock_repo)
        
        # Mock the mirror manager's update_mirror method
        from unittest.mock import patch, MagicMock
        mock_metadata = MagicMock()
        mock_metadata.resolved_commit = 'abc123commit'
        
        with patch.object(installer.mirror_manager, 'update_mirror', return_value=mock_metadata):
            # Install the library
            installed_libraries = installer.install_all()
        
        # Verify installation
        assert 'analog_design_lib' in installed_libraries
        
        # Check library was extracted to correct location
        lib_path = temp_project / "designs" / "libs" / "analog_design_lib"
        assert lib_path.exists()
        assert lib_path.is_dir()
        
        # Verify main files were extracted
        assert (lib_path / "main.sv").exists()
        assert (lib_path / "config.yaml").exists()
        assert (lib_path / "README.md").exists()
        
        # Verify LICENSE file was preserved
        license_file = lib_path / "LICENSE"
        assert license_file.exists()
        license_content = license_file.read_text()
        assert "MIT License" in license_content
        assert "Copyright (c) 2024 Analog IC Design Team" in license_content
        
        # Verify ignored files were not extracted
        assert not (lib_path / ".git").exists()
        assert not (lib_path / "__pycache__").exists()
        assert not (lib_path / ".DS_Store").exists()
        
        # Verify metadata was created
        metadata_file = lib_path / ".ams-compose-metadata.yaml"
        assert metadata_file.exists()
        
        with open(metadata_file, 'r') as f:
            provenance = yaml.safe_load(f)
        
        # Validate provenance content
        assert provenance['library_name'] == 'analog_design_lib'
        assert provenance['source']['repository'] == 'https://github.com/test/analog-lib.git'
        assert provenance['source']['reference'] == 'main'
        assert provenance['source']['commit'] == 'abc123commit'
        assert provenance['source']['source_path'] == 'analog_lib'
        
        # Validate license detection
        assert provenance['license']['type'] == 'MIT'
        assert provenance['license']['file'] == 'LICENSE'
        assert 'MIT License' in provenance['license']['snippet']
        
        # Validate compliance notes
        assert isinstance(provenance['compliance_notes'], list)
        assert len(provenance['compliance_notes']) > 0
        assert any('LICENSE file' in note for note in provenance['compliance_notes'])
    
    def test_license_not_preserved_for_checkin_false_library(self, temp_project, mock_repo):
        """Test that LICENSE files follow normal ignore rules for checkin=false libraries."""
        # Create configuration with checkin=false library and explicit LICENSE ignore
        imports_config = {
            'temp_lib': {
                'repo': 'https://github.com/test/temp-lib.git',
                'ref': 'main',
                'source_path': 'analog_lib',
                'checkin': False,  # Disable checkin
                'ignore_patterns': ['LICENSE', '*.md']  # Ignore LICENSE and markdown files
            }
        }
        self._create_test_config(temp_project, imports_config)
        
        # Create installer and mock mirror
        installer = LibraryInstaller(temp_project)
        self._create_mock_mirror(installer, imports_config['temp_lib']['repo'], mock_repo)
        
        # Mock the mirror manager's update_mirror method
        from unittest.mock import patch, MagicMock
        mock_metadata = MagicMock()
        mock_metadata.resolved_commit = 'def456commit'
        
        with patch.object(installer.mirror_manager, 'update_mirror', return_value=mock_metadata):
            # Install the library
            installed_libraries = installer.install_all()
        
        # Verify installation
        assert 'temp_lib' in installed_libraries
        
        # Check library was extracted to correct location
        lib_path = temp_project / "designs" / "libs" / "temp_lib"
        assert lib_path.exists()
        
        # Verify main files were extracted
        assert (lib_path / "main.sv").exists()
        assert (lib_path / "config.yaml").exists()
        
        # Verify LICENSE and README were ignored due to ignore_patterns
        assert not (lib_path / "LICENSE").exists()
        assert not (lib_path / "README.md").exists()
        
        # Verify metadata was created (even for checkin=false)
        metadata_file = lib_path / ".ams-compose-metadata.yaml"
        assert metadata_file.exists()
    
    def test_mixed_checkin_libraries(self, temp_project, mock_repo):
        """Test mixed scenario with both checkin=true and checkin=false libraries."""
        # Create configuration with mixed checkin settings
        imports_config = {
            'stable_lib': {
                'repo': 'https://github.com/test/stable-lib.git',
                'ref': 'v1.0.0',
                'source_path': 'analog_lib',
                'checkin': True  # Will be checked in
            },
            'experimental_lib': {
                'repo': 'https://github.com/test/experimental-lib.git',
                'ref': 'develop',
                'source_path': 'analog_lib',
                'checkin': False,  # Will not be checked in
                'ignore_patterns': ['LICENSE']  # Explicitly ignore license
            }
        }
        self._create_test_config(temp_project, imports_config)
        
        # Create installer and mock mirrors
        installer = LibraryInstaller(temp_project)
        self._create_mock_mirror(installer, imports_config['stable_lib']['repo'], mock_repo)
        self._create_mock_mirror(installer, imports_config['experimental_lib']['repo'], mock_repo)
        
        # Mock the mirror manager's update_mirror method
        from unittest.mock import patch, MagicMock
        mock_metadata = MagicMock()
        mock_metadata.resolved_commit = 'commit789'
        
        with patch.object(installer.mirror_manager, 'update_mirror', return_value=mock_metadata):
            # Install all libraries
            installed_libraries = installer.install_all()
        
        # Verify both libraries were installed
        assert 'stable_lib' in installed_libraries
        assert 'experimental_lib' in installed_libraries
        
        # Check stable_lib (checkin=true)
        stable_path = temp_project / "designs" / "libs" / "stable_lib"
        assert stable_path.exists()
        assert (stable_path / "LICENSE").exists()  # LICENSE preserved
        assert (stable_path / ".ams-compose-metadata.yaml").exists()  # Metadata created
        
        # Check experimental_lib (checkin=false)  
        experimental_path = temp_project / "designs" / "libs" / "experimental_lib"
        assert experimental_path.exists()
        assert not (experimental_path / "LICENSE").exists()  # LICENSE ignored
        assert (experimental_path / ".ams-compose-metadata.yaml").exists()  # Metadata always created
    
    def test_provenance_metadata_content_validation(self, temp_project, mock_repo):
        """Test detailed validation of provenance metadata content."""
        imports_config = {
            'validation_lib': {
                'repo': 'https://github.com/example/validation-lib.git',
                'ref': 'v2.1.0',
                'source_path': 'analog_lib',
                'checkin': True
            }
        }
        self._create_test_config(temp_project, imports_config)
        
        installer = LibraryInstaller(temp_project)
        self._create_mock_mirror(installer, imports_config['validation_lib']['repo'], mock_repo)
        
        from unittest.mock import patch, MagicMock
        mock_metadata = MagicMock()
        mock_metadata.resolved_commit = 'commit_validation_123'
        
        with patch.object(installer.mirror_manager, 'update_mirror', return_value=mock_metadata):
            installed_libraries = installer.install_all()
        
        # Load and validate metadata
        lib_path = temp_project / "designs" / "libs" / "validation_lib"
        metadata_file = lib_path / ".ams-compose-metadata.yaml"
        
        with open(metadata_file, 'r') as f:
            provenance = yaml.safe_load(f)
        
        # Validate all required fields are present
        required_fields = ['ams_compose_version', 'extraction_timestamp', 'library_name', 'source', 'license', 'compliance_notes']
        for field in required_fields:
            assert field in provenance, f"Missing required field: {field}"
        
        # Validate timestamps (ISO format with Z suffix)
        timestamp = provenance['extraction_timestamp']
        assert timestamp.endswith('Z')
        assert 'T' in timestamp  # ISO format includes T separator
        
        # Validate source information completeness
        source = provenance['source']
        assert source['repository'] == 'https://github.com/example/validation-lib.git'
        assert source['reference'] == 'v2.1.0'
        assert source['commit'] == 'commit_validation_123'
        assert source['source_path'] == 'analog_lib'
        
        # Validate compliance notes are helpful
        notes = provenance['compliance_notes']
        assert len(notes) >= 3
        assert any('extracted from' in note.lower() for note in notes)
        assert any('license' in note.lower() for note in notes)
        assert any('ip compliance' in note.lower() for note in notes)
    
    def test_license_preserved_for_checkin_false_without_ignore(self, temp_project, mock_repo):
        """Test that LICENSE files are preserved even for checkin=false libraries when not explicitly ignored."""
        # Create configuration with checkin=false library but NO explicit LICENSE ignore
        imports_config = {
            'unchecked_lib': {
                'repo': 'https://github.com/test/unchecked-lib.git',
                'ref': 'main',
                'source_path': 'analog_lib',
                'checkin': False,  # Will not be checked in
                'ignore_patterns': ['*.tmp', '*.bak']  # Ignore patterns but NOT LICENSE
            }
        }
        self._create_test_config(temp_project, imports_config)
        
        # Create installer and mock mirror
        installer = LibraryInstaller(temp_project)
        self._create_mock_mirror(installer, imports_config['unchecked_lib']['repo'], mock_repo)
        
        # Mock the mirror manager's update_mirror method
        from unittest.mock import patch, MagicMock
        mock_metadata = MagicMock()
        mock_metadata.resolved_commit = 'unchecked123commit'
        
        with patch.object(installer.mirror_manager, 'update_mirror', return_value=mock_metadata):
            # Install the library
            installed_libraries = installer.install_all()
        
        # Verify installation
        assert 'unchecked_lib' in installed_libraries
        
        # Check library was extracted to correct location
        lib_path = temp_project / "designs" / "libs" / "unchecked_lib"
        assert lib_path.exists()
        
        # Verify main library files were extracted
        assert (lib_path / "main.sv").exists()
        assert (lib_path / "config.yaml").exists()
        assert (lib_path / "README.md").exists()
        
        # Verify LICENSE file was preserved despite checkin=false (legal compliance)
        license_file = lib_path / "LICENSE"
        assert license_file.exists(), "LICENSE should be preserved for legal compliance even when checkin=false"
        license_content = license_file.read_text()
        assert "MIT License" in license_content
        assert "Analog IC Design Team" in license_content
        
        # Verify metadata was created (even for checkin=false)
        metadata_file = lib_path / ".ams-compose-metadata.yaml"
        assert metadata_file.exists(), "Metadata should always be created for traceability"