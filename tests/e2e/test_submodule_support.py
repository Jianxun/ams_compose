"""E2E tests for submodule support in ams-compose."""

import tempfile
import shutil
import subprocess
import yaml
from pathlib import Path

import pytest
import git

from ams_compose.core.installer import LibraryInstaller


class TestSubmoduleSupport:
    """Test end-to-end submodule functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "project"
        self.project_root.mkdir()
        
        # Configure Git to allow file transport for local testing
        subprocess.run(['git', 'config', '--global', 'protocol.file.allow', 'always'], 
                      check=True, capture_output=True)
        
        # Create test repositories with submodules
        self.repo_root = Path(self.temp_dir) / "test_repos"
        self.repo_root.mkdir()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
        # Reset Git configuration to default (unset the file protocol setting)
        subprocess.run(['git', 'config', '--global', '--unset', 'protocol.file.allow'], 
                      capture_output=True)  # Don't check=True since unsetting non-existent key is OK
    
    def _create_repo_with_submodule(self) -> tuple[Path, Path]:
        """Create a parent repo and a submodule repo for testing.
        
        Returns:
            Tuple of (parent_repo_path, submodule_repo_path)
        """
        # Create submodule repository first
        submodule_path = self.repo_root / "test_submodule"
        submodule_path.mkdir()
        
        sub_repo = git.Repo.init(submodule_path)
        
        # Add content to submodule
        (submodule_path / "submodule_file.txt").write_text("This is content from submodule")
        (submodule_path / "sub_circuit.v").write_text("// Verilog from submodule\nmodule sub_circuit();\nendmodule")
        
        sub_repo.index.add(["submodule_file.txt", "sub_circuit.v"])
        sub_repo.index.commit("Initial submodule commit")
        
        # Create parent repository
        parent_path = self.repo_root / "test_parent"
        parent_path.mkdir()
        
        parent_repo = git.Repo.init(parent_path)
        
        # Add content to parent repo
        (parent_path / "main_file.txt").write_text("This is content from main repo")
        (parent_path / "main_circuit.v").write_text("// Verilog from main repo\nmodule main_circuit();\nendmodule")
        
        parent_repo.index.add(["main_file.txt", "main_circuit.v"])
        parent_repo.index.commit("Initial parent commit")
        
        # Add submodule to parent repository
        parent_repo.create_submodule(
            name="test_submodule",
            path="libs/test_submodule",
            url=str(submodule_path),
            branch="main"
        )
        parent_repo.index.commit("Add submodule")
        
        return parent_path, submodule_path
    
    def test_install_library_with_submodules(self):
        """Test installing a library that contains submodules."""
        # Arrange
        parent_repo, submodule_repo = self._create_repo_with_submodule()
        
        config_content = {
            'library_root': 'libs',
            'imports': {
                'parent_with_sub': {
                    'repo': str(parent_repo),
                    'ref': 'main',
                    'source_path': '.',
                    'local_path': 'parent_lib'
                }
            }
        }
        
        # Write config file
        config_path = self.project_root / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f, default_flow_style=False)
        
        installer = LibraryInstaller(self.project_root)
        
        # Act
        installer.install_all()
        
        # Assert
        # Debug: Print actual directory structure  
        import os
        print(f"\nDEBUG: Project root contents ({self.project_root}):")
        if self.project_root.exists():
            for item in self.project_root.iterdir():
                print(f"  {item.name}")
                if item.is_dir():
                    for subitem in item.iterdir():
                        print(f"    {subitem.name}")
                        if subitem.is_dir():
                            for subsubitem in subitem.iterdir():
                                print(f"      {subsubitem.name}")
        
        # Check that main repo content is extracted  
        main_file = self.project_root / "parent_lib" / "main_file.txt"
        assert main_file.exists(), f"Expected main_file.txt at {main_file}"
        assert "main repo" in main_file.read_text()
        
        main_circuit = self.project_root / "parent_lib" / "main_circuit.v"
        assert main_circuit.exists()
        assert "main_circuit" in main_circuit.read_text()
        
        # Check that submodule content is extracted (this was the bug!)
        sub_file = self.project_root / "parent_lib" / "libs" / "test_submodule" / "submodule_file.txt"
        assert sub_file.exists(), "Submodule content should be extracted, not left as empty directory"
        assert "submodule" in sub_file.read_text()
        
        sub_circuit = self.project_root / "parent_lib" / "libs" / "test_submodule" / "sub_circuit.v"
        assert sub_circuit.exists()
        assert "sub_circuit" in sub_circuit.read_text()
    
    def test_submodule_content_accessible_after_extraction(self):
        """Test that extracted submodule content is fully accessible."""
        # Arrange
        parent_repo, submodule_repo = self._create_repo_with_submodule()
        
        config_content = {
            'library_root': 'deps',
            'imports': {
                'analog_lib': {
                    'repo': str(parent_repo),
                    'ref': 'main',
                    'source_path': '.',
                    'local_path': 'analog_blocks'
                }
            }
        }
        
        config_path = self.project_root / "ams-compose.yaml"
        # Write config file
        config_path = self.project_root / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f, default_flow_style=False)
        
        installer = LibraryInstaller(self.project_root)
        
        # Act
        installer.install_all()
        
        # Assert - verify directory structure is complete
        analog_lib = self.project_root / "analog_blocks"  # Library installed directly, not under deps/
        assert analog_lib.exists()
        
        # Main repo files
        assert (analog_lib / "main_file.txt").exists()
        assert (analog_lib / "main_circuit.v").exists()
        
        # Submodule directory should exist and contain files (not be empty)
        submodule_dir = analog_lib / "libs" / "test_submodule"
        assert submodule_dir.exists()
        assert submodule_dir.is_dir()
        
        # This is the key test - submodule files should exist, not just empty directories
        submodule_files = list(submodule_dir.glob("*"))
        assert len(submodule_files) > 0, f"Submodule directory should contain files, got: {submodule_files}"
        
        # Specific submodule content
        assert (submodule_dir / "submodule_file.txt").exists()
        assert (submodule_dir / "sub_circuit.v").exists()
    
    def test_mixed_repo_content_and_submodule_extraction(self):
        """Test extraction of repositories with both main content and submodules."""
        # Arrange
        parent_repo, submodule_repo = self._create_repo_with_submodule()
        
        # Add more complex content to test filtering
        complex_dir = parent_repo / "complex"
        complex_dir.mkdir()
        (complex_dir / "important.v").write_text("// Important Verilog file")
        
        parent_git_repo = git.Repo(parent_repo)
        parent_git_repo.index.add(["complex/important.v"])
        parent_git_repo.index.commit("Add complex content")
        
        config_content = {
            'library_root': 'external',
            'imports': {
                'complex_lib': {
                    'repo': str(parent_repo),
                    'ref': 'main',
                    'source_path': '.',
                    'local_path': 'complex_analog_lib',
                    'ignore_patterns': ['*.txt']  # Only extract .v files
                }
            }
        }
        
        config_path = self.project_root / "ams-compose.yaml"
        # Write config file
        config_path = self.project_root / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f, default_flow_style=False)
        
        installer = LibraryInstaller(self.project_root)
        
        # Act
        installer.install_all()
        
        # Assert
        lib_path = self.project_root / "complex_analog_lib"  # Library installed directly, not under external/
        
        # Main repo content (filtered by ignore_patterns)
        assert (lib_path / "main_circuit.v").exists()  # Should exist (.v file)
        assert not (lib_path / "main_file.txt").exists()  # Should be filtered out (.txt file)
        
        # Complex content
        assert (lib_path / "complex" / "important.v").exists()
        
        # Submodule content (also filtered)
        submodule_path = lib_path / "libs" / "test_submodule"
        assert submodule_path.exists()
        assert (submodule_path / "sub_circuit.v").exists()  # Should exist (.v file)
        assert not (submodule_path / "submodule_file.txt").exists()  # Should be filtered out (.txt file)
    
    def test_submodule_update_detection(self):
        """Test that updates to submodules are detected and extracted."""
        # Arrange
        parent_repo, submodule_repo = self._create_repo_with_submodule()
        
        config_content = {
            'library_root': 'libs',
            'imports': {
                'evolving_lib': {
                    'repo': str(parent_repo),
                    'ref': 'main',
                    'source_path': '.',
                    'local_path': 'evolving_analog_lib'
                }
            }
        }
        
        # Write config file
        config_path = self.project_root / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f, default_flow_style=False)
        
        installer = LibraryInstaller(self.project_root)
        
        # Initial install
        installer.install_all()
        
        # Update submodule content
        sub_repo = git.Repo(submodule_repo)
        (submodule_repo / "new_sub_file.v").write_text("// New submodule file\nmodule new_sub();\nendmodule")
        sub_repo.index.add(["new_sub_file.v"])
        sub_repo.index.commit("Add new submodule file")
        
        # Update parent repo to reference new submodule commit
        parent_git_repo = git.Repo(parent_repo)
        submodule = parent_git_repo.submodules[0]
        submodule.update(to_latest_revision=True)
        parent_git_repo.index.add([submodule.path])
        parent_git_repo.index.commit("Update submodule reference")
        
        # Act - reinstall (should detect updates)
        installer.install_all()
        
        # Assert - new submodule content should be present
        lib_path = self.project_root / "evolving_analog_lib"
        submodule_path = lib_path / "libs" / "test_submodule"
        
        # Original content should still exist
        assert (submodule_path / "sub_circuit.v").exists()
        
        # New content should now exist
        new_file = submodule_path / "new_sub_file.v"
        assert new_file.exists(), "Updated submodule content should be extracted"
        assert "new_sub" in new_file.read_text()