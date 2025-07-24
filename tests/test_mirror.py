"""Tests for repository mirroring operations."""

import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import git
import yaml

from analog_hub.core.mirror import RepositoryMirror, MirrorMetadata


class TestRepositoryMirror:
    """Test cases for RepositoryMirror class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mirror_root = Path(self.temp_dir) / "mirrors"
        self.mirror = RepositoryMirror(self.mirror_root)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_normalize_repo_url(self):
        """Test URL normalization for consistent hashing."""
        test_cases = [
            # (input, expected_output)
            ("https://github.com/user/repo", "https://github.com/user/repo"),
            ("https://github.com/user/repo/", "https://github.com/user/repo"),
            ("https://github.com/user/repo.git", "https://github.com/user/repo"),
            ("https://github.com/user/repo.git/", "https://github.com/user/repo"),
            ("git@github.com:user/repo.git", "https://github.com/user/repo"),
            ("git@gitlab.com:user/repo", "https://gitlab.com/user/repo"),
            ("HTTPS://GitHub.com/User/Repo", "https://github.com/user/repo"),
        ]
        
        for input_url, expected in test_cases:
            result = self.mirror._normalize_repo_url(input_url)
            assert result == expected, f"Failed for {input_url}: got {result}, expected {expected}"
    
    def test_generate_repo_hash(self):
        """Test repository hash generation."""
        repo_url = "https://github.com/example/test"
        hash1 = self.mirror._generate_repo_hash(repo_url)
        hash2 = self.mirror._generate_repo_hash(repo_url)
        
        # Hashes should be consistent
        assert hash1 == hash2
        
        # Hash should be 16 hex characters
        assert len(hash1) == 16
        assert all(c in '0123456789abcdef' for c in hash1)
        
        # Different URLs should produce different hashes
        different_url = "https://github.com/example/other"
        hash3 = self.mirror._generate_repo_hash(different_url)
        assert hash1 != hash3
        
        # Equivalent URLs should produce same hash
        equivalent_url = "https://github.com/example/test.git/"
        hash4 = self.mirror._generate_repo_hash(equivalent_url)
        assert hash1 == hash4
    
    def test_get_mirror_path(self):
        """Test mirror path generation."""
        repo_url = "https://github.com/example/test"
        path = self.mirror.get_mirror_path(repo_url)
        
        expected_hash = self.mirror._generate_repo_hash(repo_url)
        expected_path = self.mirror_root / expected_hash
        
        assert path == expected_path
    
    def test_mirror_exists_false_for_nonexistent(self):
        """Test mirror_exists returns False for non-existent mirror."""
        repo_url = "https://github.com/example/test"
        assert not self.mirror.mirror_exists(repo_url)
    
    def test_mirror_exists_false_for_invalid_repo(self):
        """Test mirror_exists returns False for invalid git repository."""
        repo_url = "https://github.com/example/test"
        mirror_path = self.mirror.get_mirror_path(repo_url)
        
        # Create directory but not a git repo
        mirror_path.mkdir(parents=True)
        (mirror_path / "some_file.txt").write_text("not a git repo")
        
        assert not self.mirror.mirror_exists(repo_url)
    
    @patch('analog_hub.core.mirror.git.Repo')
    def test_mirror_exists_true_for_valid_repo(self, mock_repo_class):
        """Test mirror_exists returns True for valid git repository."""
        repo_url = "https://github.com/example/test"
        mirror_path = self.mirror.get_mirror_path(repo_url)
        mirror_path.mkdir(parents=True)
        
        # Mock successful git.Repo() call
        mock_repo_class.return_value = Mock()
        
        assert self.mirror.mirror_exists(repo_url)
        mock_repo_class.assert_called_once_with(mirror_path)
    
    def test_get_mirror_metadata_none_for_nonexistent(self):
        """Test get_mirror_metadata returns None for non-existent mirror."""
        repo_url = "https://github.com/example/test"
        metadata = self.mirror.get_mirror_metadata(repo_url)
        assert metadata is None
    
    @patch('analog_hub.core.mirror.git.Repo')
    def test_get_mirror_metadata_none_for_missing_file(self, mock_repo_class):
        """Test get_mirror_metadata returns None when metadata file missing."""
        repo_url = "https://github.com/example/test"
        mirror_path = self.mirror.get_mirror_path(repo_url)
        mirror_path.mkdir(parents=True)
        
        # Mock valid git repo but no metadata file
        mock_repo_class.return_value = Mock()
        
        metadata = self.mirror.get_mirror_metadata(repo_url)
        assert metadata is None
    
    @patch('analog_hub.core.mirror.git.Repo')
    def test_get_mirror_metadata_success(self, mock_repo_class):
        """Test successful metadata retrieval."""
        repo_url = "https://github.com/example/test"
        mirror_path = self.mirror.get_mirror_path(repo_url)
        mirror_path.mkdir(parents=True)
        
        # Mock valid git repo
        mock_repo_class.return_value = Mock()
        
        # Create metadata file
        metadata_path = mirror_path / ".mirror-meta.yaml"
        test_metadata = {
            "repo_url": repo_url,
            "repo_hash": "abcd1234",
            "current_ref": "main",
            "resolved_commit": "abc123",
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:00"
        }
        with open(metadata_path, 'w') as f:
            yaml.dump(test_metadata, f)
        
        metadata = self.mirror.get_mirror_metadata(repo_url)
        assert metadata is not None
        assert metadata.repo_url == repo_url
        assert metadata.repo_hash == "abcd1234"
        assert metadata.current_ref == "main"
    
    @patch('analog_hub.core.mirror.git.Repo')
    @patch('analog_hub.core.mirror.tempfile.TemporaryDirectory')
    @patch('analog_hub.core.mirror.shutil.move')
    def test_create_mirror_success(self, mock_move, mock_temp_dir, mock_repo_class):
        """Test successful mirror creation."""
        repo_url = "https://github.com/example/test"
        ref = "main"
        
        # Mock temporary directory  
        temp_path = Path(self.temp_dir) / "repo"
        mock_temp_dir.return_value.__enter__.return_value = str(temp_path.parent)
        
        # Mock git operations
        mock_repo = Mock()
        mock_repo.head.commit.hexsha = "abc123def456"
        mock_repo_class.clone_from.return_value = mock_repo
        
        # Mock shutil.move
        def mock_move_func(src, dst):
            Path(dst).mkdir(parents=True, exist_ok=True)
        mock_move.side_effect = mock_move_func
        
        metadata = self.mirror.create_mirror(repo_url, ref)
        
        # Verify git operations
        mock_repo_class.clone_from.assert_called_once_with(url=repo_url, to_path=temp_path)
        mock_repo.git.checkout.assert_called_once_with(ref)
        
        # Verify metadata
        assert metadata.repo_url == repo_url
        assert metadata.current_ref == ref
        assert metadata.resolved_commit == "abc123def456"
        assert metadata.repo_hash == self.mirror._generate_repo_hash(repo_url)
    
    @patch('analog_hub.core.mirror.git.Repo')
    @patch('analog_hub.core.mirror.tempfile.TemporaryDirectory')
    def test_create_mirror_invalid_ref(self, mock_temp_dir, mock_repo_class):
        """Test mirror creation with invalid reference."""
        repo_url = "https://github.com/example/test"
        ref = "nonexistent-branch"
        
        # Mock temporary directory
        temp_path = Path(self.temp_dir) / "temp_repo"
        mock_temp_dir.return_value.__enter__.return_value = str(temp_path.parent)
        
        # Mock git operations - checkout fails
        mock_repo = Mock()
        mock_repo.git.checkout.side_effect = git.GitCommandError(
            "checkout", 128, "pathspec 'nonexistent-branch' did not match any file(s) known to git"
        )
        mock_repo_class.clone_from.return_value = mock_repo
        
        with pytest.raises(ValueError, match="Reference 'nonexistent-branch' not found"):
            self.mirror.create_mirror(repo_url, ref)
    
    @patch('analog_hub.core.mirror.git.Repo')
    def test_update_mirror_nonexistent_creates_new(self, mock_repo_class):
        """Test update_mirror creates new mirror when it doesn't exist."""
        repo_url = "https://github.com/example/test"
        ref = "main"
        
        with patch.object(self.mirror, 'create_mirror') as mock_create:
            mock_metadata = Mock()
            mock_create.return_value = mock_metadata
            
            result = self.mirror.update_mirror(repo_url, ref)
            
            mock_create.assert_called_once_with(repo_url, ref)
            assert result == mock_metadata
    
    @patch('analog_hub.core.mirror.git.Repo')
    def test_update_mirror_existing_success(self, mock_repo_class):
        """Test successful update of existing mirror."""
        repo_url = "https://github.com/example/test"
        ref = "develop"
        mirror_path = self.mirror.get_mirror_path(repo_url)
        mirror_path.mkdir(parents=True)
        
        # Create existing metadata
        existing_metadata_path = mirror_path / ".mirror-meta.yaml"
        existing_data = {
            "repo_url": repo_url,
            "repo_hash": self.mirror._generate_repo_hash(repo_url),
            "current_ref": "main",
            "resolved_commit": "old123",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00"
        }
        with open(existing_metadata_path, 'w') as f:
            yaml.dump(existing_data, f)
        
        # Mock git repository
        mock_repo = Mock()
        mock_repo.head.commit.hexsha = "new456def"
        mock_repo.remotes.origin.fetch.return_value = None
        mock_repo_class.return_value = mock_repo
        
        # Mock mirror_exists to return True
        with patch.object(self.mirror, 'mirror_exists', return_value=True):
            metadata = self.mirror.update_mirror(repo_url, ref)
        
        # Verify git operations
        mock_repo.remotes.origin.fetch.assert_called_once()
        mock_repo.git.checkout.assert_called_once_with(ref)
        
        # Verify metadata update
        assert metadata.repo_url == repo_url
        assert metadata.current_ref == ref
        assert metadata.resolved_commit == "new456def"
        assert metadata.created_at == "2025-01-01T10:00:00"  # Preserved
        assert metadata.updated_at != "2025-01-01T10:00:00"  # Updated
    
    def test_remove_mirror_nonexistent(self):
        """Test removing non-existent mirror."""
        repo_url = "https://github.com/example/test"
        result = self.mirror.remove_mirror(repo_url)
        assert result is False
    
    def test_remove_mirror_existing(self):
        """Test removing existing mirror."""
        repo_url = "https://github.com/example/test"
        mirror_path = self.mirror.get_mirror_path(repo_url)
        mirror_path.mkdir(parents=True)
        (mirror_path / "test_file.txt").write_text("test content")
        
        result = self.mirror.remove_mirror(repo_url)
        assert result is True
        assert not mirror_path.exists()
    
    def test_list_mirrors_empty(self):
        """Test listing mirrors when none exist."""
        mirrors = self.mirror.list_mirrors()
        assert mirrors == {}
    
    def test_list_mirrors_with_valid_mirrors(self):
        """Test listing mirrors with valid metadata."""
        # Create test mirrors
        test_repos = [
            "https://github.com/example/repo1",
            "https://github.com/example/repo2"
        ]
        
        for repo_url in test_repos:
            mirror_path = self.mirror.get_mirror_path(repo_url)
            mirror_path.mkdir(parents=True)
            
            # Create metadata
            metadata_path = mirror_path / ".mirror-meta.yaml"
            metadata_data = {
                "repo_url": repo_url,
                "repo_hash": self.mirror._generate_repo_hash(repo_url),
                "current_ref": "main",
                "resolved_commit": "abc123",
                "created_at": "2025-01-01T12:00:00",
                "updated_at": "2025-01-01T12:00:00"
            }
            with open(metadata_path, 'w') as f:
                yaml.dump(metadata_data, f)
        
        mirrors = self.mirror.list_mirrors()
        assert len(mirrors) == 2
        assert all(url in mirrors for url in test_repos)
        
        for repo_url in test_repos:
            metadata = mirrors[repo_url]
            assert metadata.repo_url == repo_url
            assert metadata.current_ref == "main"
    
    @patch('analog_hub.core.mirror.git.Repo')
    def test_cleanup_invalid_mirrors(self, mock_repo_class):
        """Test cleanup of invalid mirrors."""
        # Create mixed mirrors: valid, invalid git repo, missing metadata
        test_cases = [
            ("valid", True, True),      # Valid git repo with metadata
            ("invalid_git", False, True),  # Invalid git repo with metadata  
            ("no_metadata", True, False),  # Valid git repo without metadata
        ]
        
        for name, valid_git, has_metadata in test_cases:
            mirror_path = self.mirror_root / f"test_{name}"
            mirror_path.mkdir(parents=True)
            
            if has_metadata:
                metadata_path = mirror_path / ".mirror-meta.yaml"
                metadata_data = {
                    "repo_url": f"https://github.com/example/{name}",
                    "repo_hash": f"hash_{name}",
                    "current_ref": "main",
                    "resolved_commit": "abc123",
                    "created_at": "2025-01-01T12:00:00",
                    "updated_at": "2025-01-01T12:00:00"
                }
                with open(metadata_path, 'w') as f:
                    yaml.dump(metadata_data, f)
        
        # Mock git.Repo to succeed only for valid cases
        def mock_repo_init(path):
            if "valid" in str(path) and "invalid" not in str(path):
                return Mock()
            else:
                raise git.InvalidGitRepositoryError()
        
        mock_repo_class.side_effect = mock_repo_init
        
        removed_count = self.mirror.cleanup_invalid_mirrors()
        
        # Should remove invalid_git and no_metadata, keep valid
        assert removed_count == 2
        assert (self.mirror_root / "test_valid").exists()
        assert not (self.mirror_root / "test_invalid_git").exists()
        assert not (self.mirror_root / "test_no_metadata").exists()


class TestMirrorMetadata:
    """Test cases for MirrorMetadata class."""
    
    def test_metadata_yaml_roundtrip(self):
        """Test saving and loading metadata to/from YAML."""
        metadata = MirrorMetadata(
            repo_url="https://github.com/example/test",
            repo_hash="abcd1234",
            current_ref="main",
            resolved_commit="abc123def456",
            created_at="2025-01-01T12:00:00",
            updated_at="2025-01-01T12:30:00"
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # Save to YAML
            metadata.to_yaml(temp_path)
            
            # Load from YAML
            loaded_metadata = MirrorMetadata.from_yaml(temp_path)
            
            # Verify all fields match
            assert loaded_metadata.repo_url == metadata.repo_url
            assert loaded_metadata.repo_hash == metadata.repo_hash
            assert loaded_metadata.current_ref == metadata.current_ref
            assert loaded_metadata.resolved_commit == metadata.resolved_commit
            assert loaded_metadata.created_at == metadata.created_at
            assert loaded_metadata.updated_at == metadata.updated_at
            
        finally:
            temp_path.unlink()