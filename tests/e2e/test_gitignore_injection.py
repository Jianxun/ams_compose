"""End-to-end tests for .gitignore injection functionality.

This test suite verifies that the analog-hub system correctly manages .gitignore entries
based on the `checkin` field in library configurations, testing from a user's perspective.

Test Cases:
1. Libraries with checkin=false are automatically added to .gitignore
2. Libraries with checkin=true are NOT added to .gitignore 
3. Changing checkin from false to true removes library from .gitignore
4. Changing checkin from true to false adds library to .gitignore
5. Multiple libraries with mixed checkin settings work correctly
6. Existing .gitignore content is preserved during updates
7. New .gitignore file is created when none exists
"""

import tempfile
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any

import git

from analog_hub.core.installer import LibraryInstaller


class TestGitignoreInjection:
    """End-to-end tests for .gitignore injection functionality."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directories and mock repositories."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "project"
        self.project_root.mkdir()
        
        # Create mock repositories directory
        self.mock_repos_dir = Path(self.temp_dir) / "mock_repos"
        self.mock_repos_dir.mkdir()
        
        # Initialize installer
        self.installer = LibraryInstaller(
            project_root=self.project_root,
            mirror_root=self.project_root / ".mirror"
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def _create_mock_repo(self, repo_name: str, initial_files: Dict[str, str]) -> Path:
        """Create a mock git repository with initial files.
        
        Args:
            repo_name: Name of the repository
            initial_files: Dictionary mapping file paths to content
            
        Returns:
            Path to the created repository
        """
        repo_path = self.mock_repos_dir / repo_name
        repo_path.mkdir()
        
        # Initialize git repository
        repo = git.Repo.init(repo_path)
        
        # Create initial files
        for file_path, content in initial_files.items():
            full_path = repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            repo.index.add([file_path])  # Use relative path instead of full path
        
        # Initial commit
        repo.index.commit("Initial commit")
        
        return repo_path
    
    def _create_config(self, libraries: Dict[str, Dict[str, Any]]) -> None:
        """Create analog-hub.yaml configuration file.
        
        Args:
            libraries: Dictionary of library configurations
        """
        config_data = {
            "library-root": "libs",
            "imports": libraries
        }
        
        config_path = self.project_root / "analog-hub.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    
    def _read_gitignore(self) -> str:
        """Read current .gitignore content.
        
        Returns:
            Content of .gitignore file, or empty string if file doesn't exist
        """
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            return gitignore_path.read_text()
        return ""
    
    def test_checkin_false_library_added_to_gitignore(self):
        """Test that libraries with checkin=false are added to .gitignore."""
        # Create mock repository with library content
        repo_path = self._create_mock_repo("test-lib-repo", {
            "lib/designs/cell.sch": "schematic content",
            "lib/designs/cell.sym": "symbol content"
        })
        
        # Create configuration with checkin=false library
        self._create_config({
            "stable_library": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False
            }
        })
        
        # Install the library
        installed_libs = self.installer.install_all()
        
        # Verify library was installed
        assert "stable_library" in installed_libs
        
        # Check that .gitignore was created and contains the library path
        gitignore_content = self._read_gitignore()
        assert "libs/stable_library/" in gitignore_content
        
        # Verify the library files actually exist
        library_path = self.project_root / "libs" / "stable_library"
        assert library_path.exists()
        assert (library_path / "designs" / "cell.sch").exists()
    
    def test_checkin_true_library_not_in_gitignore(self):
        """Test that libraries with checkin=true are NOT added to .gitignore."""
        # Create mock repository with library content
        repo_path = self._create_mock_repo("critical-ip-repo", {
            "src/custom_cell.sch": "critical design",
            "src/custom_cell.lay": "layout file"
        })
        
        # Create configuration with checkin=true library (default)
        self._create_config({
            "critical_ip": {
                "repo": f"file://{repo_path}",
                "ref": "main", 
                "source_path": "src",
                "checkin": True
            }
        })
        
        # Install the library
        installed_libs = self.installer.install_all()
        
        # Verify library was installed
        assert "critical_ip" in installed_libs
        
        # Check that .gitignore doesn't contain the library path
        gitignore_content = self._read_gitignore()
        assert "libs/critical_ip/" not in gitignore_content
        
        # Verify the library files actually exist
        library_path = self.project_root / "libs" / "critical_ip"
        assert library_path.exists()
        assert (library_path / "custom_cell.sch").exists()
    
    def test_default_checkin_behavior(self):
        """Test that libraries without explicit checkin field default to checkin=true."""
        # Create mock repository
        repo_path = self._create_mock_repo("default-repo", {
            "lib/default.sch": "default content"
        })
        
        # Create configuration without checkin field (should default to true)
        self._create_config({
            "default_library": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib"
                # No checkin field - should default to True
            }
        })
        
        # Install the library
        installed_libs = self.installer.install_all()
        
        # Verify library was installed
        assert "default_library" in installed_libs
        
        # Check that .gitignore doesn't contain the library (default checkin=true)
        gitignore_content = self._read_gitignore()
        assert "libs/default_library/" not in gitignore_content
    
    def test_mixed_checkin_settings_multiple_libraries(self):
        """Test multiple libraries with different checkin settings."""
        # Create two mock repositories
        stable_repo = self._create_mock_repo("stable-repo", {
            "lib/stable.sch": "stable content"
        })
        
        custom_repo = self._create_mock_repo("custom-repo", {
            "src/custom.sch": "custom content"
        })
        
        # Create configuration with mixed checkin settings
        self._create_config({
            "stable_lib": {
                "repo": f"file://{stable_repo}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False  # Should be in .gitignore
            },
            "custom_lib": {
                "repo": f"file://{custom_repo}",
                "ref": "main",
                "source_path": "src",
                "checkin": True   # Should NOT be in .gitignore
            }
        })
        
        # Install all libraries
        installed_libs = self.installer.install_all()
        
        # Verify both libraries were installed
        assert "stable_lib" in installed_libs
        assert "custom_lib" in installed_libs
        
        # Check .gitignore content
        gitignore_content = self._read_gitignore()
        assert "libs/stable_lib/" in gitignore_content      # checkin=false
        assert "libs/custom_lib/" not in gitignore_content  # checkin=true
    
    def test_preserve_existing_gitignore_content(self):
        """Test that existing .gitignore content is preserved."""
        # Create existing .gitignore with some content
        gitignore_path = self.project_root / ".gitignore"
        existing_content = """# Existing project ignores
*.log
*.tmp
build/
.vscode/
"""
        gitignore_path.write_text(existing_content)
        
        # Create mock repository and configuration
        repo_path = self._create_mock_repo("test-repo", {
            "lib/test.sch": "test content"
        })
        
        self._create_config({
            "test_library": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False
            }
        })
        
        # Install the library
        installed_libs = self.installer.install_all()
        assert "test_library" in installed_libs
        
        # Check that existing content is preserved and new entry is added
        final_content = self._read_gitignore()
        assert "*.log" in final_content           # Existing content preserved
        assert "build/" in final_content          # Existing content preserved
        assert "libs/test_library/" in final_content  # New entry added
    
    def test_checkin_setting_change_from_false_to_true(self):
        """Test changing checkin from false to true removes library from .gitignore."""
        # Create mock repository
        repo_path = self._create_mock_repo("changeable-repo", {
            "lib/changeable.sch": "content"
        })
        
        # Step 1: Install with checkin=false
        self._create_config({
            "changeable_lib": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False
            }
        })
        
        installed_libs = self.installer.install_all()
        assert "changeable_lib" in installed_libs
        
        # Verify library is in .gitignore
        gitignore_content = self._read_gitignore()
        assert "libs/changeable_lib/" in gitignore_content
        
        # Step 2: Change configuration to checkin=true
        self._create_config({
            "changeable_lib": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib", 
                "checkin": True
            }
        })
        
        # Reinstall with force to pick up config changes
        installed_libs = self.installer.install_all(force=True)
        assert "changeable_lib" in installed_libs
        
        # Verify library is removed from .gitignore
        final_gitignore = self._read_gitignore()
        assert "libs/changeable_lib/" not in final_gitignore
    
    def test_checkin_setting_change_from_true_to_false(self):
        """Test changing checkin from true to false adds library to .gitignore."""
        # Create mock repository
        repo_path = self._create_mock_repo("switchable-repo", {
            "lib/switchable.sch": "content"
        })
        
        # Step 1: Install with checkin=true (default)
        self._create_config({
            "switchable_lib": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib",
                "checkin": True
            }
        })
        
        installed_libs = self.installer.install_all()
        assert "switchable_lib" in installed_libs
        
        # Verify library is NOT in .gitignore
        gitignore_content = self._read_gitignore()
        assert "libs/switchable_lib/" not in gitignore_content
        
        # Step 2: Change configuration to checkin=false  
        self._create_config({
            "switchable_lib": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False
            }
        })
        
        # Reinstall with force to pick up config changes
        installed_libs = self.installer.install_all(force=True)
        assert "switchable_lib" in installed_libs
        
        # Verify library is added to .gitignore
        final_gitignore = self._read_gitignore()
        assert "libs/switchable_lib/" in final_gitignore
    
    def test_gitignore_creation_when_none_exists(self):
        """Test that .gitignore file is created when it doesn't exist."""
        # Ensure no .gitignore exists initially
        gitignore_path = self.project_root / ".gitignore"
        assert not gitignore_path.exists()
        
        # Create mock repository and configuration
        repo_path = self._create_mock_repo("new-repo", {
            "lib/new.sch": "new content"
        })
        
        self._create_config({
            "new_library": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False
            }
        })
        
        # Install the library
        installed_libs = self.installer.install_all()
        assert "new_library" in installed_libs
        
        # Verify .gitignore was created with library entry
        assert gitignore_path.exists()
        gitignore_content = self._read_gitignore()
        assert "libs/new_library/" in gitignore_content
    
    def test_complex_scenario_with_multiple_operations(self):
        """Test complex scenario with multiple libraries and configuration changes."""
        # Create multiple mock repositories
        stable_repo = self._create_mock_repo("stable-repo", {
            "lib/stable.sch": "stable design"
        })
        
        dev_repo = self._create_mock_repo("dev-repo", {
            "src/dev.sch": "development design"
        })
        
        critical_repo = self._create_mock_repo("critical-repo", {
            "ip/critical.sch": "critical IP"
        })
        
        # Create existing .gitignore
        gitignore_path = self.project_root / ".gitignore"
        gitignore_path.write_text("# Project files\n*.backup\n")
        
        # Step 1: Install mixed libraries
        self._create_config({
            "stable_lib": {
                "repo": f"file://{stable_repo}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False  # Should be ignored
            },
            "dev_lib": {
                "repo": f"file://{dev_repo}",
                "ref": "main", 
                "source_path": "src",
                "checkin": True   # Should be checked in
            },
            "critical_lib": {
                "repo": f"file://{critical_repo}",
                "ref": "main",
                "source_path": "ip"
                # No checkin field - defaults to True
            }
        })
        
        installed_libs = self.installer.install_all()
        assert len(installed_libs) == 3
        
        # Verify initial .gitignore state
        gitignore_content = self._read_gitignore()
        assert "*.backup" in gitignore_content        # Original content preserved
        assert "libs/stable_lib/" in gitignore_content    # checkin=false
        assert "libs/dev_lib/" not in gitignore_content   # checkin=true  
        assert "libs/critical_lib/" not in gitignore_content # default checkin=true
        
        # Step 2: Change dev_lib to checkin=false and critical_lib to checkin=false
        self._create_config({
            "stable_lib": {
                "repo": f"file://{stable_repo}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False  # Still ignored
            },
            "dev_lib": {
                "repo": f"file://{dev_repo}",
                "ref": "main",
                "source_path": "src", 
                "checkin": False  # Now should be ignored
            },
            "critical_lib": {
                "repo": f"file://{critical_repo}",
                "ref": "main",
                "source_path": "ip",
                "checkin": False  # Now should be ignored
            }
        })
        
        # Reinstall with changes
        installed_libs = self.installer.install_all(force=True)
        assert len(installed_libs) == 3
        
        # Verify final .gitignore state
        final_gitignore = self._read_gitignore()
        assert "*.backup" in final_gitignore          # Original content still preserved
        assert "libs/stable_lib/" in final_gitignore      # Still ignored
        assert "libs/dev_lib/" in final_gitignore         # Now ignored (changed)
        assert "libs/critical_lib/" in final_gitignore    # Now ignored (changed)
        
        # Verify all libraries still exist physically
        assert (self.project_root / "libs" / "stable_lib").exists()
        assert (self.project_root / "libs" / "dev_lib").exists()
        assert (self.project_root / "libs" / "critical_lib").exists()
    
    def test_ip_repo_gitignore_files_are_filtered_out(self):
        """Test that .gitignore files from IP repositories are filtered out during extraction."""
        # Create mock repository with its own .gitignore file
        repo_path = self._create_mock_repo("ip-with-gitignore", {
            "lib/design.sch": "design content",
            "lib/design.sym": "symbol content", 
            ".gitignore": """# IP repository ignores
*.bak
*.tmp
simulation/
""",
            "README.md": "IP documentation"
        })
        
        # Create project .gitignore with existing content
        project_gitignore = self.project_root / ".gitignore"
        project_gitignore.write_text("""# Project ignores
*.log
build/
""")
        
        # Create configuration with checkin=false library
        self._create_config({
            "ip_library": {
                "repo": f"file://{repo_path}",
                "ref": "main",
                "source_path": "lib",
                "checkin": False
            }
        })
        
        # Install the library
        installed_libs = self.installer.install_all()
        assert "ip_library" in installed_libs
        
        # Verify library files were extracted
        library_path = self.project_root / "libs" / "ip_library"
        assert library_path.exists()
        assert (library_path / "design.sch").exists()
        assert (library_path / "design.sym").exists()
        
        # Verify IP's .gitignore was NOT copied (filtered out)
        ip_gitignore_in_lib = library_path / ".gitignore"
        assert not ip_gitignore_in_lib.exists(), "IP repository .gitignore should be filtered out"
        
        # Verify project .gitignore was updated correctly
        project_gitignore_content = self._read_gitignore()
        assert "*.log" in project_gitignore_content           # Original content preserved
        assert "build/" in project_gitignore_content          # Original content preserved
        assert "libs/ip_library/" in project_gitignore_content    # Library path added
        assert "*.bak" not in project_gitignore_content       # IP's ignore rules not merged
        assert "simulation/" not in project_gitignore_content # IP's ignore rules not merged
        
        # Verify no extra .gitignore files exist in project workspace (excluding .mirror)
        workspace_gitignores = []
        for gitignore_path in self.project_root.rglob(".gitignore"):
            # Skip .gitignore files in the .mirror directory (those are expected)
            if ".mirror" not in str(gitignore_path):
                workspace_gitignores.append(gitignore_path)
        
        assert len(workspace_gitignores) == 1, f"Should only have project .gitignore in workspace, found: {workspace_gitignores}"
        assert workspace_gitignores[0] == project_gitignore