"""End-to-end tests for validation fixes.

Test Case 1: Orphaned libraries - libraries in lockfile but removed from config are warned about, not validated
Test Case 2: File vs directory checksum - validation uses correct checksum method for files vs directories
"""

import tempfile
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any

import git

from ams_compose.core.installer import LibraryInstaller


class TestValidationBugs:
    """End-to-end tests for validation fixes."""
    
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

    def test_orphaned_libraries_in_lockfile(self):
        """Test Fix 1: Libraries removed from config are warned about, not validated.
        
        Fixed behavior: Only validate libraries in current config, warn about orphaned libraries
        """
        # Create mock repository with multiple libraries
        mock_repo = self._create_mock_repo("test_repo", {
            "lib_a/module.txt": "Library A content",
            "lib_b/module.txt": "Library B content", 
            "single_file.txt": "Single file content"
        })
        
        # Create initial config with 3 libraries
        initial_config = {
            'library-root': 'libs',
            'imports': {
                'lib_a': {
                    'repo': str(mock_repo),
                    'ref': 'main',
                    'source_path': 'lib_a',
                    'local_path': 'libs/lib_a'
                },
                'lib_b': {
                    'repo': str(mock_repo),
                    'ref': 'main', 
                    'source_path': 'lib_b',
                    'local_path': 'libs/lib_b'
                },
                'single_file': {
                    'repo': str(mock_repo),
                    'ref': 'main',
                    'source_path': 'single_file.txt',
                    'local_path': 'single_file.txt'
                }
            }
        }
        
        self._create_config_file(initial_config)
        
        # Install all 3 libraries
        self.installer.install_all()
        
        # Verify all are installed and lockfile has 3 entries
        lockfile = self.installer.load_lock_file()
        assert len(lockfile.libraries) == 3
        assert 'lib_a' in lockfile.libraries
        assert 'lib_b' in lockfile.libraries
        assert 'single_file' in lockfile.libraries
        
        # Remove lib_b from config (simulating user editing config)
        updated_config = {
            'library-root': 'libs',
            'imports': {
                'lib_a': {
                    'repo': str(mock_repo),
                    'ref': 'main',
                    'source_path': 'lib_a', 
                    'local_path': 'libs/lib_a'
                },
                'single_file': {
                    'repo': str(mock_repo),
                    'ref': 'main',
                    'source_path': 'single_file.txt',
                    'local_path': 'single_file.txt'
                }
            }
        }
        
        self._create_config_file(updated_config)
        
        # Test fixed behavior - validation only checks libraries in current config
        validation_results = self.installer.validate_installation()
        
        # Extract valid libraries and check statuses
        valid_libraries = [name for name, entry in validation_results.items() if entry.validation_status == "valid"]
        orphaned_libraries = [name for name, entry in validation_results.items() if entry.validation_status == "orphaned"]
        
        # FIXED: Only libraries in current config should be validated
        assert 'lib_a' in valid_libraries, "lib_a should be validated (in current config)"
        assert 'single_file' in valid_libraries, "single_file should be validated (in current config)"
        assert 'lib_b' in orphaned_libraries, "lib_b should be marked as orphaned (not in current config)"
        
        # FIXED: lib_b should be marked as orphaned in the new validation system
        # With the new unified architecture, orphaned libraries are identified by validation_status
        assert len(orphaned_libraries) == 1, "Should have exactly 1 orphaned library"
        assert 'lib_b' in orphaned_libraries, "lib_b should be marked as orphaned"
        
        # Verify that current config libraries are properly validated
        assert len(valid_libraries) == 2, "Should have 2 valid libraries from current config"

    def test_file_vs_directory_checksum_bug(self):
        """Test Fix 2: Validation uses correct checksum method for files and directories.
        
        Fixed behavior: Use calculate_file_checksum() for files, calculate_directory_checksum() for directories
        """
        # Create mock repository with both file and directory
        mock_repo = self._create_mock_repo("test_repo", {
            "lib_dir/module.txt": "Directory library content",
            "lib_dir/subdir/file.txt": "Nested file content",
            "single_file.txt": "Single file library content"
        })
        
        # Create config with both file and directory library
        config = {
            'library-root': 'libs',
            'imports': {
                'lib_directory': {
                    'repo': str(mock_repo),
                    'ref': 'main',
                    'source_path': 'lib_dir',
                    'local_path': 'libs/lib_directory'
                },
                'lib_file': {
                    'repo': str(mock_repo),
                    'ref': 'main',
                    'source_path': 'single_file.txt',
                    'local_path': 'lib_file.txt'
                }
            }
        }
        
        self._create_config_file(config)
        
        # Install both libraries
        self.installer.install_all()
        
        # Verify installation
        lib_dir_path = self.project_root / "libs/lib_directory"
        lib_file_path = self.project_root / "lib_file.txt"
        
        assert lib_dir_path.exists() and lib_dir_path.is_dir()
        assert lib_file_path.exists() and lib_file_path.is_file()
        
        # Test fixed behavior - both file and directory validation work correctly
        validation_results = self.installer.validate_installation()
        
        # Extract valid libraries
        valid_libraries = [name for name, entry in validation_results.items() if entry.validation_status == "valid"]
        
        # FIXED: Both file and directory libraries should validate correctly
        assert 'lib_file' in valid_libraries, "File library should validate correctly with proper checksum method"
        assert 'lib_directory' in valid_libraries, "Directory library should validate correctly"
        
        # FIXED: No invalid libraries when everything is properly installed
        # Check that all libraries have valid status
        invalid_libraries = [name for name, entry in validation_results.items() if entry.validation_status != "valid"]
        assert len(invalid_libraries) == 0, f"Should have no invalid libraries, but got: {invalid_libraries}"

    def test_git_directory_filtering_fix(self):
        """Test Fix: .git directory is properly filtered when source_path is '.' to prevent version control issues.
        
        Fixed behavior: When using source_path: '.', the extractor now filters out .git and other 
        VCS directories, allowing clean extraction while preventing version control conflicts.
        """
        # Create mock repository with git metadata and library files
        mock_repo = self._create_mock_repo("test_repo", {
            "library_file.v": "// Verilog library content\nmodule test();\nendmodule",
            "docs/readme.txt": "Library documentation",
            "models/model.sp": "* SPICE model\n.model test_model nmos",
            "subdir/nested_file.txt": "Nested library content"
        })
        
        # Add additional git metadata to the existing .git directory
        git_dir = mock_repo / ".git"
        # git_dir already exists from _create_mock_repo, just add more content
        (git_dir / "config").write_text("[core]\n\trepositoryformatversion = 0")
        (git_dir / "objects").mkdir(exist_ok=True)
        (git_dir / "objects" / "test_object").write_text("git object content")
        
        # Add other git-related files
        (mock_repo / ".gitignore").write_text("*.log\n*.tmp")
        (mock_repo / ".gitmodules").write_text("[submodule \"test\"]\n\tpath = test")
        (mock_repo / ".gitattributes").write_text("*.v text eol=lf")
        
        # Create config using source_path: '.' to extract entire repository
        config = {
            'library-root': 'libs',
            'imports': {
                'full_repo_library': {
                    'repo': str(mock_repo),
                    'ref': 'main',
                    'source_path': '.',  # This causes the bug - copies everything including .git
                    'local_path': 'libs/full_repo_library'
                }
            }
        }
        
        self._create_config_file(config)
        
        # Install the library
        self.installer.install_all()
        
        # Verify library was installed
        library_path = self.project_root / "libs/full_repo_library"
        assert library_path.exists() and library_path.is_dir()
        
        # Verify library files are properly extracted
        assert (library_path / "library_file.v").exists(), "Library files should be extracted"
        assert (library_path / "docs/readme.txt").exists(), "Documentation should be extracted"
        assert (library_path / "models/model.sp").exists(), "Models should be extracted"
        assert (library_path / "subdir/nested_file.txt").exists(), "Nested files should be extracted"
        
        # BUG REPRODUCTION: Check that .git directory is incorrectly copied
        git_copied = (library_path / ".git").exists()
        gitignore_copied = (library_path / ".gitignore").exists()
        gitmodules_copied = (library_path / ".gitmodules").exists()
        gitattributes_copied = (library_path / ".gitattributes").exists()
        
        # Document the fixed behavior
        print(f"\\n=== FIXED BEHAVIOR VERIFICATION ===")
        print(f".git directory copied: {git_copied}")
        print(f".gitignore copied: {gitignore_copied}")
        print(f".gitmodules copied: {gitmodules_copied}")
        print(f".gitattributes copied: {gitattributes_copied}")
        
        # FIXED BEHAVIOR: .git directory is properly filtered out
        assert not git_copied, "FIXED: .git directory should NOT be copied and now it isn't"
        assert not gitignore_copied, "FIXED: .gitignore should NOT be copied and now it isn't"
        assert not gitmodules_copied, "FIXED: .gitmodules should NOT be copied and now it isn't"
        assert not gitattributes_copied, "FIXED: .gitattributes should NOT be copied and now it isn't"
        
        # Verify that installation still works functionally (checksum validation)
        validation_results = self.installer.validate_installation()
        
        # Extract valid libraries
        valid_libraries = [name for name, entry in validation_results.items() if entry.validation_status == "valid"]
        invalid_libraries = [name for name, entry in validation_results.items() if entry.validation_status != "valid"]
        
        assert 'full_repo_library' in valid_libraries, "Library should still validate functionally"
        assert len(invalid_libraries) == 0, "Installation should be functionally valid despite git files"
        
        print(f"\\n=== SECURITY/WORKFLOW BENEFITS ===")
        print(f"- Extracted library is clean of version control metadata")
        print(f"- Libraries can now be committed to version control without conflicts")
        print(f"- No security risk from exposed git history")
        print(f"- Clean workspace without unnecessary VCS files")