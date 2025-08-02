"""Unit tests for RepositoryMirror submodule support."""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest
import git

from ams_compose.core.mirror import RepositoryMirror, MirrorState


class TestSubmoduleSupport:
    """Test RepositoryMirror submodule operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mirror_root = Path(self.temp_dir) / "mirrors"
        self.mirror = RepositoryMirror(self.mirror_root)
        
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('ams_compose.core.mirror.git.Repo')
    @patch('ams_compose.core.mirror.shutil.move')
    @patch('ams_compose.core.mirror.tempfile.TemporaryDirectory')
    def test_create_mirror_clones_with_submodules(self, mock_temp_dir, mock_move, mock_repo_class):
        """Test that create_mirror() clones repositories with submodules."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "abc123"
        mock_repo_class.clone_from.return_value = mock_repo
        
        # Mock temporary directory and its contents
        temp_path = Path("/mock/temp/repo")
        mock_temp_context = MagicMock()
        mock_temp_context.__enter__.return_value = "/mock/temp"
        mock_temp_context.__exit__.return_value = None
        mock_temp_dir.return_value = mock_temp_context
        
        # Mock directory iteration - simulate cloned repo contents
        with patch.object(Path, 'iterdir') as mock_iterdir:
            mock_iterdir.return_value = [Path("/mock/temp/repo/.git"), Path("/mock/temp/repo/README.md")]
            
            repo_url = "https://github.com/test/repo-with-submodules.git"
            ref = "main"
            
            # Act
            result = self.mirror.create_mirror(repo_url, ref)
            
            # Assert
            mock_repo_class.clone_from.assert_called_once()
            call_args = mock_repo_class.clone_from.call_args
            
            # Verify that recurse_submodules=True was passed
            assert call_args[1]['recurse_submodules'] is True
            assert call_args[1]['url'] == repo_url
            assert isinstance(result, MirrorState)
            assert result.resolved_commit == "abc123"
    
    @patch('ams_compose.core.mirror.git.Repo')
    def test_update_mirror_updates_submodules(self, mock_repo_class):
        """Test that update_mirror() updates existing submodules."""
        # Arrange
        repo_url = "https://github.com/test/repo-with-submodules.git"
        ref = "main"
        
        # Create mock mirror directory
        mirror_path = self.mirror.get_mirror_path(repo_url)
        mirror_path.mkdir(parents=True)
        (mirror_path / ".git").mkdir()
        
        # Mock existing repo with submodules
        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "def456"
        mock_repo.submodules = [MagicMock()]  # Has submodules
        mock_repo.remotes.origin.fetch.return_value = None
        mock_repo.commit.return_value.hexsha = "def456"
        mock_repo.heads = {"main": MagicMock()}
        mock_repo.heads["main"].commit.hexsha = "def456"
        
        # Mock git.submodule command
        mock_repo.git.submodule.return_value = None
        mock_repo.git.checkout.return_value = None
        
        mock_repo_class.return_value = mock_repo
        
        # Act
        result = self.mirror.update_mirror(repo_url, ref)
        
        # Assert
        mock_repo.git.submodule.assert_called_once_with('update', '--init', '--recursive')
        assert isinstance(result, MirrorState)
        assert result.resolved_commit == "def456"
    
    @patch('ams_compose.core.mirror.git.Repo')
    def test_update_mirror_skips_submodules_when_none_exist(self, mock_repo_class):
        """Test that update_mirror() skips submodule operations when no submodules exist."""
        # Arrange
        repo_url = "https://github.com/test/repo-without-submodules.git"
        ref = "main"
        
        # Create mock mirror directory
        mirror_path = self.mirror.get_mirror_path(repo_url)
        mirror_path.mkdir(parents=True)
        (mirror_path / ".git").mkdir()
        
        # Mock existing repo without submodules
        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "ghi789"
        mock_repo.submodules = []  # No submodules
        mock_repo.remotes.origin.fetch.return_value = None
        mock_repo.commit.return_value.hexsha = "ghi789"
        mock_repo.heads = {"main": MagicMock()}
        mock_repo.heads["main"].commit.hexsha = "ghi789"
        mock_repo.git.checkout.return_value = None
        
        mock_repo_class.return_value = mock_repo
        
        # Act
        result = self.mirror.update_mirror(repo_url, ref)
        
        # Assert
        # submodule command should NOT be called
        mock_repo.git.submodule.assert_not_called()
        assert isinstance(result, MirrorState)
        assert result.resolved_commit == "ghi789"
    
    @patch('ams_compose.core.mirror.git.Repo')
    def test_submodule_timeout_handling(self, mock_repo_class):
        """Test that submodule operations respect timeout settings."""
        # Arrange
        repo_url = "https://github.com/test/repo-with-submodules.git"
        ref = "main"
        
        # Create mock mirror directory
        mirror_path = self.mirror.get_mirror_path(repo_url)
        mirror_path.mkdir(parents=True)
        (mirror_path / ".git").mkdir()
        
        # Mock repo that will timeout during submodule operations
        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "timeout123"
        mock_repo.submodules = [MagicMock()]  # Has submodules
        mock_repo.remotes.origin.fetch.return_value = None
        mock_repo.commit.return_value.hexsha = "timeout123"
        mock_repo.heads = {"main": MagicMock()}
        mock_repo.heads["main"].commit.hexsha = "timeout123"
        mock_repo.git.checkout.return_value = None
        
        # Mock timeout during submodule operation
        from ams_compose.core.mirror import GitOperationTimeout
        mock_repo.git.submodule.side_effect = GitOperationTimeout("Submodule operation timed out")
        
        mock_repo_class.return_value = mock_repo
        
        # Mock _update_submodules to directly test timeout handling
        with patch.object(self.mirror, '_update_submodules', side_effect=GitOperationTimeout("Submodule operation timed out")):
            # Act & Assert
            with pytest.raises(GitOperationTimeout, match="Submodule operation timed out"):
                self.mirror.update_mirror(repo_url, ref)
    
    def test_update_submodules_method_exists(self):
        """Test that _update_submodules method will be implemented."""
        # This test ensures we implement the _update_submodules method
        # It will fail until we implement it
        assert hasattr(self.mirror, '_update_submodules'), "RepositoryMirror should have _update_submodules method"
        
        # Test that it's callable
        mock_repo = MagicMock()
        mock_repo.submodules = [MagicMock()]
        
        # This will fail until implemented
        try:
            self.mirror._update_submodules(mock_repo)
        except AttributeError:
            pytest.fail("_update_submodules method not implemented")