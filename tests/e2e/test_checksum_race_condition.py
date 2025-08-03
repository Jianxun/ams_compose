"""End-to-end test for checksum calculation race condition bug.

Test Case: Checksum calculated before .gitignore injection causes validation failures
- Install library with checkin=false
- .gitignore gets injected AFTER checksum calculation
- Later validation fails because checksum includes .gitignore file
"""

import tempfile
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any

import git

from ams_compose.core.installer import LibraryInstaller


class TestChecksumRaceCondition:
    """Test for checksum calculation race condition bug."""
    
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
            repo.index.add([file_path])
        
        # Initial commit
        repo.index.commit("Initial commit")
        
        return repo_path
    
    def _create_config_file(self, config_data: Dict[str, Any]) -> Path:
        """Create ams-compose.yaml configuration file.
        
        Args:
            config_data: Configuration data to write
            
        Returns:
            Path to created config file
        """
        config_path = self.project_root / "ams-compose.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        return config_path

    def test_checksum_race_condition_with_checkin_false(self):
        """Test that demonstrates the checksum calculation race condition.
        
        BUG REPRODUCTION:
        1. Install library with checkin=false
        2. Checksum is calculated BEFORE .gitignore injection
        3. .gitignore file is added AFTER checksum calculation  
        4. Validation fails because recalculated checksum includes .gitignore
        """
        # Create mock repository with library content
        mock_repo = self._create_mock_repo("race-condition-repo", {
            "lib/design.sch": "schematic content for analog design",
            "lib/layout.gds": "layout binary data",
            "lib/models/model.sp": "SPICE model content",
            "docs/README.md": "Library documentation"
        })
        
        # Create configuration with checkin=false library (triggers .gitignore injection)
        config = {
            'library_root': 'libs',
            'imports': {
                'analog_lib': {
                    'repo': f"file://{mock_repo}",
                    'ref': 'main',
                    'source_path': 'lib',
                    'local_path': 'libs/analog_lib',
                    'checkin': False  # This triggers .gitignore injection AFTER checksum
                }
            }
        }
        
        self._create_config_file(config)
        
        # Step 1: Install the library
        print("\\n=== STEP 1: Installing library with checkin=false ===")
        self.installer.install_all()
        
        # Verify installation completed
        library_path = self.project_root / "libs/analog_lib"
        assert library_path.exists(), "Library should be installed"
        assert (library_path / "design.sch").exists(), "Library files should be extracted"
        
        # Verify .gitignore was injected
        library_gitignore = library_path / ".gitignore"
        assert library_gitignore.exists(), "Library .gitignore should be injected for checkin=false"
        
        gitignore_content = library_gitignore.read_text()
        assert "checkin: false" in gitignore_content, ".gitignore should indicate checkin=false"
        assert "*\n!.gitignore" in gitignore_content, ".gitignore should ignore all except itself"
        
        # Check the lockfile entry
        lockfile = self.installer.load_lock_file()
        assert 'analog_lib' in lockfile.libraries, "Library should be in lockfile"
        
        original_checksum = lockfile.libraries['analog_lib'].checksum
        print(f"Original checksum from installation: {original_checksum}")
        
        # Step 2: Validate installation (this should pass but currently fails due to race condition)
        print("\\n=== STEP 2: Validating installation ===")
        validation_results = self.installer.validate_installation()
        
        # Extract valid and invalid libraries
        valid_libraries = [name for name, entry in validation_results.items() if entry.validation_status == "valid"]
        invalid_libraries = [name for name, entry in validation_results.items() if entry.validation_status != "valid"]
        
        print(f"Valid libraries: {valid_libraries}")
        print(f"Invalid libraries: {invalid_libraries}")
        
        # BUG DEMONSTRATION: This assertion will currently FAIL due to race condition
        # The checksum was calculated before .gitignore injection, but validation
        # recalculates checksum with .gitignore present, causing mismatch
        try:
            assert 'analog_lib' in valid_libraries, "Library should validate successfully"
            assert len(actual_invalid) == 0, f"Should have no validation failures, but got: {actual_invalid}"
            print("✅ BUG IS FIXED: Checksum race condition resolved!")
        except AssertionError as e:
            print(f"🐛 BUG REPRODUCED: {e}")
            print("This demonstrates the checksum calculation race condition:")
            print("1. Checksum calculated without .gitignore file")
            print("2. .gitignore injected after checksum calculation") 
            print("3. Validation recalculates checksum with .gitignore present")
            print("4. Checksums don't match, causing validation failure")
            
            # Show the checksum mismatch details
            if actual_invalid:
                for invalid_msg in actual_invalid:
                    if 'checksum' in invalid_msg.lower():
                        print(f"Checksum mismatch details: {invalid_msg}")
            
            # This test is expected to fail until the bug is fixed
            # Re-raise to show the bug exists
            raise
    
    def test_checksum_race_condition_with_checkin_true(self):
        """Control test: checkin=true libraries should validate correctly (no .gitignore injection)."""
        # Create mock repository with library content
        mock_repo = self._create_mock_repo("control-repo", {
            "lib/design.sch": "schematic content for analog design",
            "lib/layout.gds": "layout binary data"
        })
        
        # Create configuration with checkin=true library (no .gitignore injection)
        config = {
            'library_root': 'libs',
            'imports': {
                'control_lib': {
                    'repo': f"file://{mock_repo}",
                    'ref': 'main',
                    'source_path': 'lib',
                    'local_path': 'libs/control_lib',
                    'checkin': True  # No .gitignore injection, should validate fine
                }
            }
        }
        
        self._create_config_file(config)
        
        # Install and validate
        self.installer.install_all()
        validation_results = self.installer.validate_installation()
        
        # Extract valid and invalid libraries  
        valid_libraries = [name for name, entry in validation_results.items() if entry.validation_status == "valid"]
        invalid_libraries = [name for name, entry in validation_results.items() if entry.validation_status != "valid"]
        
        # This should work fine - no race condition with checkin=true
        assert 'control_lib' in valid_libraries, "checkin=true library should validate successfully"
        assert len(invalid_libraries) == 0, f"checkin=true should have no validation issues: {invalid_libraries}"
        
        # Verify no .gitignore was injected
        library_path = self.project_root / "libs/control_lib" 
        library_gitignore = library_path / ".gitignore"
        assert not library_gitignore.exists(), "checkin=true should not have library .gitignore"