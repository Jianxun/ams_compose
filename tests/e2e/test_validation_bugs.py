"""End-to-end tests for validation fixes.

Test Case 1: Orphaned libraries - libraries in lockfile but removed from config are warned about, not validated
Test Case 2: File vs directory checksum - validation uses correct checksum method for files vs directories
"""

import tempfile
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any

import pytest
import git

from analog_hub.core.installer import LibraryInstaller
from analog_hub.core.config import AnalogHubConfig


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
        """Create analog-hub.yaml configuration file.
        
        Args:
            config_data: Configuration data to write
            
        Returns:
            Path to created config file
        """
        config_path = self.project_root / "analog-hub.yaml"
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
        valid_libraries, invalid_libraries = self.installer.validate_installation()
        
        # FIXED: Only libraries in current config should be validated
        assert 'lib_a' in valid_libraries, "lib_a should be validated (in current config)"
        assert 'single_file' in valid_libraries, "single_file should be validated (in current config)"
        
        # FIXED: lib_b should be warned about as orphaned, not validated
        orphaned_warning_found = any('WARNING' in msg and 'orphaned' in msg for msg in invalid_libraries)
        assert orphaned_warning_found, "Should warn about orphaned libraries"
        
        lib_b_mentioned_in_warning = any('lib_b' in msg for msg in invalid_libraries)
        assert lib_b_mentioned_in_warning, "lib_b should be mentioned in orphaned warning"
        
        fix_suggestion_found = any('analog-hub clean' in msg for msg in invalid_libraries) 
        assert fix_suggestion_found, "Should suggest running 'analog-hub clean' to fix"

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
        valid_libraries, invalid_libraries = self.installer.validate_installation()
        
        # FIXED: Both file and directory libraries should validate correctly
        assert 'lib_file' in valid_libraries, "File library should validate correctly with proper checksum method"
        assert 'lib_directory' in valid_libraries, "Directory library should validate correctly"
        
        # FIXED: No invalid libraries when everything is properly installed
        # Filter out any warning messages (which might be present for other reasons)
        actual_invalid_libraries = [lib for lib in invalid_libraries if not lib.startswith('WARNING')]
        assert len(actual_invalid_libraries) == 0, f"Should have no invalid libraries, but got: {actual_invalid_libraries}"