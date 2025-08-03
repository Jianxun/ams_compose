"""End-to-end tests for branch update detection scenarios.

Tests Use Case 1: Source repo branch updated → ams-compose install should update library
"""

import tempfile
import shutil
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any

import pytest
import git

from ams_compose.core.installer import LibraryInstaller
from ams_compose.core.config import ComposeConfig


class TestBranchUpdateDetection:
    """End-to-end tests for automatic branch update detection."""
    
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
        
        # Initial commit
        repo.index.add(list(initial_files.keys()))
        repo.index.commit("Initial commit")
        
        return repo_path
    
    def _add_commit_to_repo(self, repo_path: Path, new_files: Dict[str, str], 
                           commit_message: str = "Update files") -> str:
        """Add new commit to existing repository.
        
        Args:
            repo_path: Path to the repository
            new_files: Dictionary mapping file paths to new content
            commit_message: Commit message
            
        Returns:
            SHA of the new commit
        """
        repo = git.Repo(repo_path)
        
        # Add/modify files
        for file_path, content in new_files.items():
            full_path = repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        # Commit changes
        repo.index.add(list(new_files.keys()))
        commit = repo.index.commit(commit_message)
        
        return commit.hexsha
    
    def _create_analog_config(self, imports_config: Dict[str, Any]) -> None:
        """Create ams-compose.yaml configuration file.
        
        Args:
            imports_config: Dictionary of import specifications
        """
        config_data = {
            'library-root': 'designs/libs',
            'imports': imports_config
        }
        
        config_path = self.project_root / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
    
    @pytest.mark.slow
    def test_branch_update_single_library(self):
        """Test that branch updates trigger library reinstallation."""
        # Create mock repository with initial analog design files
        initial_files = {
            "designs/libs/analog_lib/amplifier.sch": "* Initial amplifier schematic\n.subckt amp in out\n.ends\n",
            "designs/libs/analog_lib/amplifier.sym": "v {xschem version=3.0.0}\nG {type=subcircuit}\nV {}\nS {}\nE {}\n",
            "designs/libs/analog_lib/README.md": "# Analog Library v1.0\nInitial version\n"
        }
        
        repo_path = self._create_mock_repo("analog_lib_repo", initial_files)
        initial_commit = git.Repo(repo_path).head.commit.hexsha
        
        # Create configuration pointing to main branch
        self._create_analog_config({
            'analog_lib': {
                'repo': f'file://{repo_path}',
                'ref': 'main',
                'source_path': 'designs/libs/analog_lib',
                'license': 'MIT'
            }
        })
        
        # Initial installation
        print("🔄 Initial installation...")
        installed_libraries = self.installer.install_all()
        
        # Verify initial installation
        assert 'analog_lib' in installed_libraries
        initial_entry = installed_libraries['analog_lib']
        assert initial_entry.commit == initial_commit
        assert initial_entry.ref == 'main'
        
        # Verify files were extracted
        library_path = self.project_root / initial_entry.local_path
        assert library_path.exists()
        assert (library_path / "amplifier.sch").exists()
        assert (library_path / "amplifier.sym").exists()
        
        # Check initial file content
        initial_sch_content = (library_path / "amplifier.sch").read_text()
        assert "Initial amplifier schematic" in initial_sch_content
        
        # Simulate upstream branch update
        print("🔄 Simulating upstream branch update...")
        updated_files = {
            "designs/libs/analog_lib/amplifier.sch": "* Updated amplifier schematic v2.0\n.subckt amp in out vdd vss\n.param gain=10\n.ends\n",
            "designs/libs/analog_lib/bandgap.sch": "* New bandgap reference\n.subckt bgr vout vdd vss\n.ends\n",
            "designs/libs/analog_lib/bandgap.sym": "v {xschem version=3.0.0}\nG {type=subcircuit}\nV {}\nS {}\nE {}\n",
            "designs/libs/analog_lib/README.md": "# Analog Library v2.0\nAdded bandgap reference\nUpdated amplifier\n"
        }
        
        new_commit = self._add_commit_to_repo(repo_path, updated_files, "Add bandgap reference and update amplifier")
        assert new_commit != initial_commit
        
        # Run install again - should detect branch update
        print("🔄 Running install after upstream update...")
        updated_libraries = self.installer.install_all()
        
        # Verify update was detected and library was reinstalled
        assert 'analog_lib' in updated_libraries, "Library should be updated when branch has new commits"
        updated_entry = updated_libraries['analog_lib']
        assert updated_entry.commit == new_commit, f"Expected new commit {new_commit}, got {updated_entry.commit}"
        assert updated_entry.ref == 'main'
        
        # Verify updated files are present
        updated_sch_content = (library_path / "amplifier.sch").read_text()
        assert "Updated amplifier schematic v2.0" in updated_sch_content, "File content should be updated"
        assert (library_path / "bandgap.sch").exists(), "New file should be extracted" 
        assert (library_path / "bandgap.sym").exists(), "New symbol should be extracted"
        
        # Verify README was updated
        readme_content = (library_path / "README.md").read_text()
        assert "v2.0" in readme_content
        assert "Added bandgap reference" in readme_content
        
        # Verify lock file was updated
        lock_file = self.installer.load_lock_file()
        lock_entry = lock_file.libraries['analog_lib']
        assert lock_entry.commit == new_commit
        assert lock_entry.updated_at > lock_entry.installed_at
        
        print(f"✅ Branch update detection successful:")
        print(f"   Initial commit: {initial_commit}")
        print(f"   Updated commit: {new_commit}")
        print(f"   Files updated: amplifier.sch, README.md")
        print(f"   Files added: bandgap.sch, bandgap.sym")
    
    @pytest.mark.slow
    def test_no_update_when_branch_unchanged(self):
        """Test that no update occurs when branch hasn't changed."""
        # Create mock repository
        initial_files = {
            "designs/libs/stable_lib/opamp.sch": "* Stable operational amplifier\n.subckt opamp inp inn out\n.ends\n",
            "designs/libs/stable_lib/opamp.sym": "v {xschem version=3.0.0}\nG {type=subcircuit}\nV {}\nS {}\nE {}\n"
        }
        
        repo_path = self._create_mock_repo("stable_lib_repo", initial_files)
        initial_commit = git.Repo(repo_path).head.commit.hexsha
        
        # Create configuration
        self._create_analog_config({
            'stable_lib': {
                'repo': f'file://{repo_path}',
                'ref': 'main',
                'source_path': 'designs/libs/stable_lib',
                'license': 'MIT'
            }
        })
        
        # Initial installation
        print("🔄 Initial installation...")
        installed_libraries = self.installer.install_all()
        assert 'stable_lib' in installed_libraries
        
        # Get installation timestamp
        lock_file = self.installer.load_lock_file()
        initial_lock_entry = lock_file.libraries['stable_lib']
        initial_updated_at = initial_lock_entry.updated_at
        
        # Run install again immediately - no upstream changes
        print("🔄 Running install again with no upstream changes...")
        updated_libraries = self.installer.install_all()
        
        # Verify no update occurred
        assert 'stable_lib' not in updated_libraries, "Library should not be updated when branch is unchanged"
        
        # Verify lock file timestamp unchanged
        lock_file_after = self.installer.load_lock_file()
        lock_entry_after = lock_file_after.libraries['stable_lib']
        assert lock_entry_after.updated_at == initial_updated_at, "Timestamp should not change if no update needed"
        assert lock_entry_after.commit == initial_commit
        
        print(f"✅ No-update behavior correct:")
        print(f"   Commit unchanged: {initial_commit}")
        print(f"   Library skipped with '[up to date]' message")
    
    @pytest.mark.slow  
    def test_multiple_libraries_mixed_updates(self):
        """Test mixed scenario: some libraries update, others don't."""
        # Create two repositories
        stable_files = {
            "designs/libs/stable/resistor.sch": "* Stable resistor model\n.subckt resistor p n\n.ends\n"
        }
        updating_files = {
            "designs/libs/updating/capacitor.sch": "* Capacitor model v1.0\n.subckt cap p n\n.ends\n"
        }
        
        stable_repo = self._create_mock_repo("stable_repo", stable_files)
        updating_repo = self._create_mock_repo("updating_repo", updating_files)
        
        stable_commit = git.Repo(stable_repo).head.commit.hexsha
        initial_updating_commit = git.Repo(updating_repo).head.commit.hexsha
        
        # Create configuration with both libraries
        self._create_analog_config({
            'stable_lib': {
                'repo': f'file://{stable_repo}',
                'ref': 'main', 
                'source_path': 'designs/libs/stable',
                'license': 'MIT'
            },
            'updating_lib': {
                'repo': f'file://{updating_repo}',
                'ref': 'main',
                'source_path': 'designs/libs/updating', 
                'license': 'MIT'
            }
        })
        
        # Initial installation
        print("🔄 Installing both libraries...")
        installed_libraries = self.installer.install_all()
        assert len(installed_libraries) == 2
        assert 'stable_lib' in installed_libraries
        assert 'updating_lib' in installed_libraries
        
        # Update only the updating repository
        print("🔄 Updating only one upstream repository...")
        updated_files = {
            "designs/libs/updating/capacitor.sch": "* Capacitor model v2.0 - improved accuracy\n.subckt cap p n\n.param c=1e-12\n.ends\n",
            "designs/libs/updating/inductor.sch": "* New inductor model\n.subckt ind p n\n.ends\n"
        }
        
        new_updating_commit = self._add_commit_to_repo(updating_repo, updated_files, "Add inductor and improve capacitor")
        
        # Run install again
        print("🔄 Running install after partial upstream update...")
        updated_libraries = self.installer.install_all()
        
        # Verify only updating_lib was reinstalled
        assert 'updating_lib' in updated_libraries, "Updated library should be reinstalled"
        assert 'stable_lib' not in updated_libraries, "Unchanged library should be skipped"
        
        # Verify commits
        updated_entry = updated_libraries['updating_lib']
        assert updated_entry.commit == new_updating_commit
        
        # Verify stable library unchanged in lock file
        lock_file = self.installer.load_lock_file()
        stable_entry = lock_file.libraries['stable_lib']
        assert stable_entry.commit == stable_commit
        
        # Verify files
        updating_path = self.project_root / updated_entry.local_path
        assert (updating_path / "inductor.sch").exists(), "New file should be added"
        cap_content = (updating_path / "capacitor.sch").read_text()
        assert "v2.0" in cap_content, "File should be updated"
        
        print(f"✅ Mixed update scenario successful:")
        print(f"   stable_lib: unchanged at {stable_commit[:8]}")
        print(f"   updating_lib: updated to {new_updating_commit[:8]}")
        print(f"   Only 1 of 2 libraries required reinstallation")
    
    @pytest.mark.slow
    def test_branch_to_branch_ref_change(self):
        """Test updating when ref changes from one branch to another."""
        # Create repository with multiple branches
        initial_files = {
            "designs/libs/multi_branch/core.sch": "* Core circuit main branch\n.subckt core in out\n.ends\n"
        }
        
        repo_path = self._create_mock_repo("multi_branch_repo", initial_files)
        repo = git.Repo(repo_path)
        main_commit = repo.head.commit.hexsha
        
        # Create development branch with different content
        dev_branch = repo.create_head('development')
        repo.heads.development.checkout()
        
        dev_files = {
            "designs/libs/multi_branch/core.sch": "* Core circuit development branch\n.subckt core in out vdd vss\n.param gain=20\n.ends\n",
            "designs/libs/multi_branch/experimental.sch": "* Experimental feature\n.subckt exp in out\n.ends\n"
        }
        
        for file_path, content in dev_files.items():
            full_path = repo_path / file_path  
            full_path.write_text(content)
        
        repo.index.add(list(dev_files.keys()))
        dev_commit = repo.index.commit("Development branch features").hexsha
        
        # Switch back to main for initial install
        repo.heads.main.checkout()
        
        # Create configuration pointing to main branch
        self._create_analog_config({
            'multi_branch_lib': {
                'repo': f'file://{repo_path}',
                'ref': 'main',
                'source_path': 'designs/libs/multi_branch',
                'license': 'MIT'
            }
        })
        
        # Install from main branch
        print("🔄 Installing from main branch...")
        installed_libraries = self.installer.install_all()
        assert 'multi_branch_lib' in installed_libraries
        
        main_entry = installed_libraries['multi_branch_lib']
        assert main_entry.commit == main_commit
        assert main_entry.ref == 'main'
        
        # Verify main branch content
        library_path = self.project_root / main_entry.local_path
        core_content = (library_path / "core.sch").read_text()
        assert "main branch" in core_content
        assert not (library_path / "experimental.sch").exists()
        
        # Update configuration to point to development branch
        print("🔄 Updating configuration to development branch...")
        self._create_analog_config({
            'multi_branch_lib': {
                'repo': f'file://{repo_path}',
                'ref': 'development',  # Changed ref
                'source_path': 'designs/libs/multi_branch',
                'license': 'MIT'
            }
        })
        
        # Install again - should detect ref change
        print("🔄 Installing after ref change to development...")
        updated_libraries = self.installer.install_all()
        
        # Verify library was updated due to ref change
        assert 'multi_branch_lib' in updated_libraries, "Library should update when ref changes"
        updated_entry = updated_libraries['multi_branch_lib']
        assert updated_entry.commit == dev_commit
        assert updated_entry.ref == 'development'
        
        # Verify development branch content
        updated_core_content = (library_path / "core.sch").read_text()
        assert "development branch" in updated_core_content
        assert (library_path / "experimental.sch").exists(), "Development branch files should be present"
        
        print(f"✅ Branch ref change detection successful:")
        print(f"   main branch commit: {main_commit[:8]}")
        print(f"   development branch commit: {dev_commit[:8]}")
        print(f"   Library correctly switched branches")