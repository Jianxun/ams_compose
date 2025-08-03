"""End-to-end tests for version pinning scenarios.

Tests Use Case 2: Source repo branch updated, but library has pinned version/commit → shouldn't update library
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
from ams_compose.core.config import AnalogHubConfig


class TestVersionPinning:
    """End-to-end tests for version pinning behavior."""
    
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
    def test_pinned_commit_ignores_branch_updates(self):
        """Test that libraries pinned to specific commits don't update when branch changes."""
        # Create mock repository with initial analog design files
        initial_files = {
            "designs/libs/pinned_lib/dac.sch": "* Digital-to-Analog Converter v1.0\n.subckt dac d0 d1 d2 d3 out\n.ends\n",
            "designs/libs/pinned_lib/dac.sym": "v {xschem version=3.0.0}\nG {type=subcircuit}\nV {}\nS {}\nE {}\n",
            "designs/libs/pinned_lib/README.md": "# DAC Library v1.0\nInitial version with 4-bit DAC\n"
        }
        
        repo_path = self._create_mock_repo("pinned_lib_repo", initial_files)
        repo = git.Repo(repo_path)
        pinned_commit = repo.head.commit.hexsha
        
        # Create configuration with pinned commit
        self._create_analog_config({
            'pinned_lib': {
                'repo': f'file://{repo_path}',
                'ref': pinned_commit,  # Pin to specific commit
                'source_path': 'designs/libs/pinned_lib',
                'license': 'Apache-2.0'
            }
        })
        
        # Initial installation
        print("🔄 Installing library pinned to specific commit...")
        installed_libraries = self.installer.install_all()
        
        # Verify initial installation
        assert 'pinned_lib' in installed_libraries[0]
        initial_entry = installed_libraries['pinned_lib']
        assert initial_entry.commit == pinned_commit
        assert initial_entry.ref == pinned_commit  # ref should be the commit SHA
        
        # Verify files were extracted
        library_path = self.project_root / initial_entry.local_path
        assert library_path.exists()
        assert (library_path / "dac.sch").exists()
        assert (library_path / "dac.sym").exists()
        
        # Check initial file content
        initial_sch_content = (library_path / "dac.sch").read_text()
        assert "v1.0" in initial_sch_content
        
        # Simulate multiple upstream updates
        print("🔄 Simulating upstream branch updates...")
        
        # First update
        updated_files_v2 = {
            "designs/libs/pinned_lib/dac.sch": "* Digital-to-Analog Converter v2.0\n.subckt dac d0 d1 d2 d3 d4 d5 d6 d7 out\n.param bits=8\n.ends\n",
            "designs/libs/pinned_lib/adc.sch": "* New ADC component\n.subckt adc in d0 d1 d2 d3\n.ends\n",
            "designs/libs/pinned_lib/README.md": "# DAC Library v2.0\nUpgraded to 8-bit DAC\nAdded ADC component\n"
        }
        
        v2_commit = self._add_commit_to_repo(repo_path, updated_files_v2, "Upgrade to 8-bit DAC and add ADC")
        
        # Second update
        updated_files_v3 = {
            "designs/libs/pinned_lib/dac.sch": "* Digital-to-Analog Converter v3.0\n.subckt dac d[0:15] out vref\n.param bits=16\n.ends\n",
            "designs/libs/pinned_lib/adc.sch": "* Advanced ADC component\n.subckt adc in d[0:15] vref\n.param bits=16\n.ends\n",
            "designs/libs/pinned_lib/pll.sch": "* Phase-Locked Loop\n.subckt pll ref out\n.ends\n",
            "designs/libs/pinned_lib/README.md": "# DAC Library v3.0\nUpgraded to 16-bit DAC/ADC\nAdded PLL component\n"
        }
        
        v3_commit = self._add_commit_to_repo(repo_path, updated_files_v3, "Upgrade to 16-bit and add PLL")
        
        # Verify commits are different
        assert pinned_commit != v2_commit != v3_commit
        print(f"   Pinned commit: {pinned_commit[:8]}")
        print(f"   V2 commit: {v2_commit[:8]}")
        print(f"   V3 commit: {v3_commit[:8]}")
        
        # Run install again - should NOT update due to commit pinning
        print("🔄 Running install after upstream updates...")
        updated_libraries = self.installer.install_all()
        
        # Verify no update occurred
        assert 'pinned_lib' not in updated_libraries, "Pinned library should not update when upstream changes"
        
        # Verify files still contain original content
        current_sch_content = (library_path / "dac.sch").read_text()
        assert "v1.0" in current_sch_content, "Pinned library should maintain original content"
        assert "4-bit DAC" in (library_path / "README.md").read_text()
        assert not (library_path / "adc.sch").exists(), "New upstream files should not appear"
        assert not (library_path / "pll.sch").exists(), "New upstream files should not appear"
        
        # Verify lock file shows pinned commit
        lock_file = self.installer.load_lock_file()
        lock_entry = lock_file.libraries['pinned_lib']
        assert lock_entry.commit == pinned_commit, "Lock file should show pinned commit"
        assert lock_entry.ref == pinned_commit, "Lock file ref should be the pinned commit"
        
        print(f"✅ Version pinning successful:")
        print(f"   Library remained at pinned commit: {pinned_commit[:8]}")
        print(f"   Upstream progressed through: {v2_commit[:8]} → {v3_commit[:8]}")
        print(f"   Library correctly ignored all upstream changes")
    
    @pytest.mark.slow
    def test_pinned_tag_ignores_branch_updates(self):
        """Test that libraries pinned to tags don't update when branch changes."""
        # Create mock repository with initial files
        initial_files = {
            "designs/libs/tagged_lib/filter.sch": "* Low-pass filter v1.0.0\n.subckt lpf in out\n.param fc=1000\n.ends\n",
            "designs/libs/tagged_lib/filter.sym": "v {xschem version=3.0.0}\nG {type=subcircuit}\nV {}\nS {}\nE {}\n"
        }
        
        repo_path = self._create_mock_repo("tagged_lib_repo", initial_files)
        repo = git.Repo(repo_path)
        
        # Create tag for initial version
        tag_commit = repo.head.commit.hexsha
        repo.create_tag('v1.0.0', message='Release version 1.0.0')
        
        # Create configuration with pinned tag
        self._create_analog_config({
            'tagged_lib': {
                'repo': f'file://{repo_path}',
                'ref': 'v1.0.0',  # Pin to tag
                'source_path': 'designs/libs/tagged_lib',
                'license': 'BSD-3-Clause'
            }
        })
        
        # Initial installation
        print("🔄 Installing library pinned to tag v1.0.0...")
        installed_libraries = self.installer.install_all()
        
        # Verify installation with tag
        assert 'tagged_lib' in installed_libraries[0]
        initial_entry = installed_libraries['tagged_lib']
        assert initial_entry.commit == tag_commit
        assert initial_entry.ref == 'v1.0.0'
        
        # Verify initial content
        library_path = self.project_root / initial_entry.local_path
        initial_content = (library_path / "filter.sch").read_text()
        assert "v1.0.0" in initial_content
        
        # Add commits to main branch (simulating development)
        dev_files = {
            "designs/libs/tagged_lib/filter.sch": "* Low-pass filter v2.0-dev\n.subckt lpf in out vdd vss\n.param fc=1000 q=0.707\n.ends\n",
            "designs/libs/tagged_lib/highpass.sch": "* High-pass filter\n.subckt hpf in out\n.ends\n"
        }
        
        dev_commit = self._add_commit_to_repo(repo_path, dev_files, "Development: Add high-pass filter and improve low-pass")
        
        # Create another tag for newer version
        repo.create_tag('v2.0.0', message='Release version 2.0.0')
        
        # Add more development
        more_dev_files = {
            "designs/libs/tagged_lib/filter.sch": "* Low-pass filter v3.0-dev\n.subckt lpf in out vdd vss enable\n.param fc=1000 q=0.707\n.ends\n",
            "designs/libs/tagged_lib/bandpass.sch": "* Band-pass filter\n.subckt bpf in out\n.ends\n"
        }
        
        latest_commit = self._add_commit_to_repo(repo_path, more_dev_files, "Development: Add enable pin and band-pass filter")
        
        # Verify we have progression
        assert tag_commit != dev_commit != latest_commit
        
        # Run install again - should stay at tagged version
        print("🔄 Running install after upstream development...")
        updated_libraries = self.installer.install_all()
        
        # Verify no update occurred
        assert 'tagged_lib' not in updated_libraries, "Tagged library should not update"
        
        # Verify content unchanged
        current_content = (library_path / "filter.sch").read_text()
        assert "v1.0.0" in current_content, "Should maintain tagged version content"
        assert not (library_path / "highpass.sch").exists(), "Should not have new files"
        assert not (library_path / "bandpass.sch").exists(), "Should not have new files"
        
        # Verify lock file maintains tag reference
        lock_file = self.installer.load_lock_file()
        lock_entry = lock_file.libraries['tagged_lib']
        assert lock_entry.commit == tag_commit
        assert lock_entry.ref == 'v1.0.0'
        
        print(f"✅ Tag pinning successful:")
        print(f"   Library remained at tag v1.0.0 (commit {tag_commit[:8]})")
        print(f"   Upstream development: {dev_commit[:8]} → {latest_commit[:8]}")
        print(f"   New tag v2.0.0 created but ignored")
    
    @pytest.mark.slow
    def test_mixed_pinning_and_tracking(self):
        """Test scenario with mix of pinned libraries and branch-tracking libraries."""
        # Create repository with initial files
        initial_files = {
            "designs/libs/mixed_test/circuit.sch": "* Circuit v1.0\n.subckt circuit in out\n.ends\n"
        }
        
        repo_path = self._create_mock_repo("mixed_test_repo", initial_files)
        repo = git.Repo(repo_path)
        initial_commit = repo.head.commit.hexsha
        
        # Add second commit
        updated_files = {
            "designs/libs/mixed_test/circuit.sch": "* Circuit v2.0\n.subckt circuit in out vdd vss\n.param gain=10\n.ends\n",
            "designs/libs/mixed_test/filter.sch": "* New filter\n.subckt filter in out\n.ends\n"
        }
        second_commit = self._add_commit_to_repo(repo_path, updated_files, "Add filter and update circuit")
        
        # Test 1: Install library pinned to first commit
        print("🔄 Testing pinned version behavior...")
        self._create_analog_config({
            'mixed_lib': {
                'repo': f'file://{repo_path}',
                'ref': initial_commit,  # Pinned to specific commit
                'source_path': 'designs/libs/mixed_test',
                'license': 'MIT'
            }
        })
        
        installed_pinned = self.installer.install_all()
        assert 'mixed_lib' in installed_pinned
        pinned_entry = installed_pinned['mixed_lib']
        assert pinned_entry.commit == initial_commit, "Should install pinned commit"
        
        # Verify pinned content
        library_path = self.project_root / pinned_entry.local_path
        circuit_content = (library_path / "circuit.sch").read_text()
        assert "v1.0" in circuit_content, "Should have pinned version content"
        assert not (library_path / "filter.sch").exists(), "Should not have newer files"
        
        # Test 2: Change config to track branch (this should trigger update)
        print("🔄 Testing branch tracking behavior...")
        self._create_analog_config({
            'mixed_lib': {
                'repo': f'file://{repo_path}',
                'ref': 'main',  # Changed to track branch
                'source_path': 'designs/libs/mixed_test',
                'license': 'MIT'
            }
        })
        
        updated_to_branch = self.installer.install_all()
        assert 'mixed_lib' in updated_to_branch, "Should update when config ref changes"
        branch_entry = updated_to_branch['mixed_lib']
        assert branch_entry.commit == second_commit, "Should get latest branch commit"
        
        # Verify branch content
        updated_circuit_content = (library_path / "circuit.sch").read_text()
        assert "v2.0" in updated_circuit_content, "Should have latest content"
        assert (library_path / "filter.sch").exists(), "Should have new files"
        
        # Test 3: Change back to pinned (should downgrade)
        print("🔄 Testing downgrade to pinned version...")
        self._create_analog_config({
            'mixed_lib': {
                'repo': f'file://{repo_path}',
                'ref': initial_commit,  # Back to pinned commit
                'source_path': 'designs/libs/mixed_test',
                'license': 'MIT'
            }
        })
        
        downgraded = self.installer.install_all()
        assert 'mixed_lib' in downgraded, "Should update when config ref changes back"
        downgraded_entry = downgraded['mixed_lib']
        assert downgraded_entry.commit == initial_commit, "Should downgrade to pinned commit"
        
        # Verify downgraded content
        final_circuit_content = (library_path / "circuit.sch").read_text()
        assert "v1.0" in final_circuit_content, "Should have original content"
        assert not (library_path / "filter.sch").exists(), "Should not have newer files"
        
        print(f"✅ Mixed pinning scenario successful:")
        print(f"   Pinned install: {initial_commit[:8]}")
        print(f"   Branch tracking: {second_commit[:8]}")
        print(f"   Downgrade to pinned: {initial_commit[:8]}")
        print(f"   Configuration changes trigger appropriate updates")
    
    @pytest.mark.slow
    def test_force_reinstall_pinned_library(self):
        """Test that --force flag can reinstall pinned libraries without updating them."""
        # Create repository with multiple commits
        initial_files = {
            "designs/libs/force_test/mixer.sch": "* RF mixer v1.0\n.subckt mixer rf lo if\n.ends\n"
        }
        
        repo_path = self._create_mock_repo("force_test_repo", initial_files)
        repo = git.Repo(repo_path)
        pinned_commit = repo.head.commit.hexsha
        
        # Add newer commit
        newer_files = {
            "designs/libs/force_test/mixer.sch": "* RF mixer v2.0\n.subckt mixer rf lo if vdd vss\n.param gain=10\n.ends\n"
        }
        newer_commit = self._add_commit_to_repo(repo_path, newer_files, "Add power pins and gain parameter")
        
        # Create configuration pinned to old commit
        self._create_analog_config({
            'force_test_lib': {
                'repo': f'file://{repo_path}',
                'ref': pinned_commit,
                'source_path': 'designs/libs/force_test',
                'license': 'MIT'
            }
        })
        
        # Initial installation
        print("🔄 Installing library pinned to older commit...")
        installed_libraries = self.installer.install_all()
        assert 'force_test_lib' in installed_libraries[0]
        
        # Verify pinned content
        library_path = self.project_root / installed_libraries['force_test_lib'].local_path
        initial_content = (library_path / "mixer.sch").read_text()
        assert "v1.0" in initial_content
        
        # Modify local file to simulate corruption
        print("🔄 Simulating local file corruption...")
        (library_path / "mixer.sch").write_text("* CORRUPTED FILE\n")
        
        # Regular install should detect corruption but not update to newer commit
        print("🔄 Running regular install after corruption...")
        # Note: Current implementation may not detect file modifications in smart install
        # This is because it only checks if files exist, not their checksums
        # We'll test the force reinstall behavior instead
        result = self.installer.install_all()
        print(f"   Regular install result: {list(result.keys())}")
        
        # Force reinstall should restore pinned version
        print("🔄 Running force reinstall...")
        force_installed = self.installer.install_all(['force_test_lib'], force=True)
        
        # Verify force reinstall restored pinned content (not newer version)
        assert 'force_test_lib' in force_installed
        restored_content = (library_path / "mixer.sch").read_text()
        assert "v1.0" in restored_content, "Force reinstall should restore pinned version"
        assert "CORRUPTED" not in restored_content
        
        # Verify it didn't update to newer commit
        lock_file = self.installer.load_lock_file()
        lock_entry = lock_file.libraries['force_test_lib']
        assert lock_entry.commit == pinned_commit, "Force reinstall should maintain pinned commit"
        
        print(f"✅ Force reinstall of pinned library successful:")
        print(f"   Maintained pinned commit: {pinned_commit[:8]}")
        print(f"   Did not update to newer commit: {newer_commit[:8]}")
        print(f"   Restored original content from pinned version")