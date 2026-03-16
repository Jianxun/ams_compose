"""End-to-end tests for .gitignore injection functionality.

This test suite verifies that the ams-compose system correctly manages .gitignore entries
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

from ams_compose.core.installer import LibraryInstaller


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
        """Create ams-compose.yaml configuration file.
        
        Args:
            libraries: Dictionary of library configurations
        """
        config_data = {
            "library_root": "libs",
            "imports": libraries
        }
        
        config_path = self.project_root / "ams-compose.yaml"
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
    
    def test_checkin_false_library_gets_own_gitignore(self):
        """Test that libraries with checkin=false get their own .gitignore file."""
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
        
        # Check that library-specific .gitignore was created with enhanced content
        library_path = self.project_root / "libs" / "stable_library"
        library_gitignore_path = library_path / ".gitignore"
        assert library_gitignore_path.exists()
        gitignore_content = library_gitignore_path.read_text()
        assert "# Library: stable_library (checkin: false)" in gitignore_content
        assert "# This library is not checked into version control" in gitignore_content
        assert "*\n!.gitignore" in gitignore_content
        
        # Verify main .gitignore does NOT contain the library path
        if (self.project_root / ".gitignore").exists():
            gitignore_content = self._read_gitignore()
            assert "libs/stable_library/" not in gitignore_content
        
        # Verify the library files actually exist
        assert library_path.exists()
        assert (library_path / "designs" / "cell.sch").exists()
    
    def test_checkin_true_library_no_gitignore_created(self):
        """Test that libraries with checkin=true do NOT get their own .gitignore file."""
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
        
        # Check that library-specific .gitignore was NOT created
        library_path = self.project_root / "libs" / "critical_ip"
        library_gitignore_path = library_path / ".gitignore"
        assert not library_gitignore_path.exists()
        
        # Check that main .gitignore doesn't contain the library path (if exists)
        if (self.project_root / ".gitignore").exists():
            gitignore_content = self._read_gitignore()
            assert "libs/critical_ip/" not in gitignore_content
        
        # Verify the library files actually exist
        assert library_path.exists()
        assert (library_path / "custom_cell.sch").exists()
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
                "checkin": False  # Should get its own .gitignore
            },
            "custom_lib": {
                "repo": f"file://{custom_repo}",
                "ref": "main",
                "source_path": "src",
                "checkin": True   # Should NOT get .gitignore
            }
        })
        
        # Install all libraries
        installed_libs = self.installer.install_all()
        
        # Verify both libraries were installed
        assert "stable_lib" in installed_libs
        assert "custom_lib" in installed_libs
        
        # Check library-specific .gitignore files
        stable_lib_path = self.project_root / "libs" / "stable_lib"
        stable_lib_gitignore = stable_lib_path / ".gitignore"
        assert stable_lib_gitignore.exists()      # checkin=false gets .gitignore
        gitignore_content = stable_lib_gitignore.read_text()
        assert "# Library: stable_lib (checkin: false)" in gitignore_content
        assert "*\n!.gitignore" in gitignore_content
        
        custom_lib_path = self.project_root / "libs" / "custom_lib"
        custom_lib_gitignore = custom_lib_path / ".gitignore"
        assert not custom_lib_gitignore.exists()  # checkin=true does NOT get .gitignore
        
        # Check main .gitignore does NOT contain library paths
        if (self.project_root / ".gitignore").exists():
            gitignore_content = self._read_gitignore()
            assert "libs/stable_lib/" not in gitignore_content
            assert "libs/custom_lib/" not in gitignore_content
    
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
        
        # Check that existing content is preserved (main .gitignore unchanged)
        final_content = self._read_gitignore()
        assert "*.log" in final_content           # Existing content preserved
        assert "build/" in final_content          # Existing content preserved
        # Note: With new per-library .gitignore approach, main .gitignore is not modified
        
        # Check that library-specific .gitignore was created instead
        library_gitignore = self.project_root / "libs" / "test_library" / ".gitignore"
        assert library_gitignore.exists()
        library_content = library_gitignore.read_text()
        assert "checkin: false" in library_content
        assert "!.gitignore" in library_content  # Self-referential
    
    def test_checkin_setting_change_from_false_to_true(self):
        """Test changing checkin from false to true removes library-specific .gitignore."""
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
        
        # Verify library-specific .gitignore was created with enhanced content
        library_path = self.project_root / "libs" / "changeable_lib"
        library_gitignore_path = library_path / ".gitignore"
        assert library_gitignore_path.exists()
        gitignore_content = library_gitignore_path.read_text()
        assert "# Library: changeable_lib (checkin: false)" in gitignore_content
        assert "*\n!.gitignore" in gitignore_content
        
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
        
        # Verify library-specific .gitignore was removed
        assert not library_gitignore_path.exists()
        
        # Verify main .gitignore does not contain library path
        if (self.project_root / ".gitignore").exists():
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
        
        # Verify library-specific .gitignore was created (new per-library approach)
        library_gitignore = self.project_root / "libs" / "switchable_lib" / ".gitignore"
        assert library_gitignore.exists()
        library_content = library_gitignore.read_text()
        assert "checkin: false" in library_content
    
    def test_gitignore_creation_when_none_exists(self):
        """Test that library-specific .gitignore is created for checkin=false libraries."""
        # Ensure no main .gitignore exists initially
        main_gitignore_path = self.project_root / ".gitignore"
        assert not main_gitignore_path.exists()
        
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
        
        # Verify library-specific .gitignore was created (NOT main project .gitignore)
        library_path = self.project_root / "libs" / "new_library"
        library_gitignore = library_path / ".gitignore"
        
        assert library_gitignore.exists(), "Library-specific .gitignore should be created for checkin=false"
        gitignore_content = library_gitignore.read_text()
        assert "checkin: false" in gitignore_content
        assert "*\n!.gitignore" in gitignore_content
        
        # Verify main project .gitignore is NOT created (library-specific approach)
        assert not main_gitignore_path.exists(), "Main .gitignore should not be created - using library-specific approach"
    
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
        
        # Verify initial library-specific .gitignore state (NOT main .gitignore modification)
        main_gitignore_content = self._read_gitignore()
        assert "*.backup" in main_gitignore_content        # Original content preserved
        
        # Check library-specific .gitignore files
        stable_lib_gitignore = self.project_root / "libs" / "stable_lib" / ".gitignore"
        dev_lib_gitignore = self.project_root / "libs" / "dev_lib" / ".gitignore"
        critical_lib_gitignore = self.project_root / "libs" / "critical_lib" / ".gitignore"
        
        assert stable_lib_gitignore.exists(), "stable_lib should have .gitignore (checkin=false)"
        assert not dev_lib_gitignore.exists(), "dev_lib should not have .gitignore (checkin=true)"
        assert not critical_lib_gitignore.exists(), "critical_lib should not have .gitignore (default checkin=true)"
        
        # Verify stable_lib .gitignore content
        stable_content = stable_lib_gitignore.read_text()
        assert "checkin: false" in stable_content
        
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
        
        # Verify final library-specific .gitignore state
        final_main_gitignore = self._read_gitignore()
        assert "*.backup" in final_main_gitignore          # Original content still preserved
        
        # Check final library-specific .gitignore files
        stable_lib_gitignore = self.project_root / "libs" / "stable_lib" / ".gitignore"
        dev_lib_gitignore = self.project_root / "libs" / "dev_lib" / ".gitignore"
        critical_lib_gitignore = self.project_root / "libs" / "critical_lib" / ".gitignore"
        
        assert stable_lib_gitignore.exists(), "stable_lib should still have .gitignore (checkin=false)"
        assert dev_lib_gitignore.exists(), "dev_lib should now have .gitignore (changed to checkin=false)"
        assert critical_lib_gitignore.exists(), "critical_lib should now have .gitignore (changed to checkin=false)"
        
        # Verify all library .gitignore files have correct content
        for lib_name, lib_gitignore in [("stable_lib", stable_lib_gitignore), 
                                       ("dev_lib", dev_lib_gitignore),
                                       ("critical_lib", critical_lib_gitignore)]:
            content = lib_gitignore.read_text()
            assert f"Library: {lib_name} (checkin: false)" in content
            assert "*\n!.gitignore" in content
        
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
        
        # Verify IP's original .gitignore content was filtered out, but NEW library .gitignore created
        library_gitignore = library_path / ".gitignore"
        assert library_gitignore.exists(), "Library-specific .gitignore should be created for checkin=false"
        
        # Verify the library .gitignore is OUR generated one, not the IP's original
        library_gitignore_content = library_gitignore.read_text()
        assert "Library: ip_library (checkin: false)" in library_gitignore_content, "Should be our generated .gitignore"
        assert "*\n!.gitignore" in library_gitignore_content, "Should have our ignore pattern"
        
        # Verify IP's original .gitignore content was NOT copied
        assert "*.bak" not in library_gitignore_content, "IP's original .gitignore content should be filtered out"
        assert "*.tmp" not in library_gitignore_content, "IP's original .gitignore content should be filtered out"
        assert "simulation/" not in library_gitignore_content, "IP's original .gitignore content should be filtered out"
        
        # Verify project .gitignore was NOT modified (library-specific approach)
        project_gitignore_content = self._read_gitignore()
        assert "*.log" in project_gitignore_content           # Original content preserved
        assert "build/" in project_gitignore_content          # Original content preserved
        assert "libs/ip_library/" not in project_gitignore_content, "Main .gitignore should NOT be modified - using library-specific approach"
        
        # Verify expected .gitignore files exist in project workspace (excluding .mirror)
        workspace_gitignores = []
        for gitignore_path in self.project_root.rglob(".gitignore"):
            # Skip .gitignore files in the .mirror directory (those are expected)
            if ".mirror" not in str(gitignore_path):
                workspace_gitignores.append(gitignore_path)
        
        # Should have 2 .gitignore files: main project + library-specific for checkin=false
        assert len(workspace_gitignores) == 2, f"Should have project + library .gitignore files, found: {workspace_gitignores}"
        
        gitignore_paths = {str(path) for path in workspace_gitignores}
        expected_paths = {str(project_gitignore), str(library_gitignore)}
        assert gitignore_paths == expected_paths, f"Expected {expected_paths}, but found {gitignore_paths}"