"""Repository mirroring operations for ams-compose."""

import os
import shutil
import tempfile
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import urlparse

import git

from ..utils.checksum import ChecksumCalculator


@dataclass
class MirrorState:
    """Lightweight state information returned by mirror operations."""
    resolved_commit: str


class GitOperationTimeout(Exception):
    """Raised when git operation times out."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for operation timeout."""
    raise GitOperationTimeout("Git operation timed out")



class RepositoryMirror:
    """Manages repository mirroring operations."""
    
    def __init__(self, mirror_root: Path = Path(".mirror"), git_timeout: int = 60, allow_file_urls: bool = None):
        """Initialize mirror manager.
        
        Args:
            mirror_root: Root directory for all mirrors (default: .mirror)
            git_timeout: Timeout for git operations in seconds (default: 60)
            allow_file_urls: Allow file:// URLs (for testing only, auto-detects if None)
        """
        self.mirror_root = Path(mirror_root)
        self.mirror_root.mkdir(exist_ok=True)
        self._ensure_mirror_gitignore()
        self.git_timeout = git_timeout
        
        # Auto-detect test mode if not explicitly set
        if allow_file_urls is None:
            # Check if we're running in test environment
            self.allow_file_urls = (
                os.environ.get('PYTEST_CURRENT_TEST') is not None or
                os.environ.get('AMS_COMPOSE_TEST_MODE', '').lower() == 'true'
            )
        else:
            self.allow_file_urls = allow_file_urls
    
    def _ensure_mirror_gitignore(self) -> None:
        """Create .gitignore file in mirror directory to exclude all contents from version control."""
        gitignore_path = self.mirror_root / ".gitignore"
        
        # Only create if it doesn't exist
        if not gitignore_path.exists():
            gitignore_content = """# Exclude all mirror contents from version control
# Mirrors are local caches and should not be committed
*
!.gitignore
"""
            gitignore_path.write_text(gitignore_content)
    
    def _validate_repo_url(self, repo_url: str) -> None:
        """Validate repository URL for security.
        
        Args:
            repo_url: Repository URL to validate
            
        Raises:
            ValueError: If URL is potentially malicious or unsafe
        """
        if not repo_url or not repo_url.strip():
            raise ValueError("Repository URL cannot be empty")
        
        # Parse the URL
        try:
            parsed = urlparse(repo_url)
        except Exception as e:
            raise ValueError(f"Invalid repository URL format: {repo_url}") from e
        
        # Check for malformed URLs
        if repo_url.startswith('://'):
            raise ValueError(f"Malformed URL missing scheme: {repo_url}")
        
        if parsed.scheme and not parsed.netloc and parsed.scheme in {'http', 'https'}:
            raise ValueError(f"Malformed URL missing host: {repo_url}")
        
        # Check for allowed schemes
        allowed_schemes = {'https', 'http', 'git', 'ssh'}
        if self.allow_file_urls:
            allowed_schemes.add('file')
            
        if parsed.scheme and parsed.scheme.lower() not in allowed_schemes:
            raise ValueError(
                f"Unsupported URL scheme '{parsed.scheme}'. "
                f"Allowed schemes: {', '.join(sorted(allowed_schemes))}"
            )
        
        # Explicitly reject file:// URLs for security (unless explicitly allowed for testing)
        if parsed.scheme and parsed.scheme.lower() == 'file' and not self.allow_file_urls:
            raise ValueError(
                "Local file:// URLs are not allowed for security reasons. "
                "Use remote repository URLs only."
            )
        
        # Check for potentially malicious patterns
        suspicious_patterns = ['..', '~', '$', '`', '|', ';', '&']
        for pattern in suspicious_patterns:
            if pattern in repo_url:
                raise ValueError(
                    f"Repository URL contains suspicious pattern '{pattern}': {repo_url}"
                )
    
    def _with_timeout(self, operation, timeout=None):
        """Execute git operation with timeout.
        
        Args:
            operation: Function to execute
            timeout: Timeout in seconds (uses instance default if None)
            
        Returns:
            Result of operation
            
        Raises:
            GitOperationTimeout: If operation times out
        """
        if timeout is None:
            timeout = self.git_timeout
            
        # Set up signal handler
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            result = operation()
            return result
        finally:
            # Clean up signal handler
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
    def _update_submodules(self, repo: git.Repo) -> None:
        """Update all submodules to match remote state.
        
        Args:
            repo: Git repository object with submodules to update
        """
        self._with_timeout(
            lambda: repo.git.submodule('update', '--init', '--recursive'),
            timeout=180  # 3 minutes for submodule operations
        )
    
    def get_mirror_path(self, repo_url: str) -> Path:
        """Get mirror directory path for repository.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Path to mirror directory
        """
        repo_hash = ChecksumCalculator.generate_repo_hash(repo_url)
        return self.mirror_root / repo_hash
    
    def mirror_exists(self, repo_url: str) -> bool:
        """Check if mirror exists for repository.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            True if mirror directory exists with valid git repo
        """
        mirror_path = self.get_mirror_path(repo_url)
        if not mirror_path.exists():
            return False
        
        try:
            # Check if it's a valid git repository
            git.Repo(mirror_path)
            return True
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False
    
    def get_mirror_commit(self, repo_url: str) -> Optional[str]:
        """Get current commit for existing mirror.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Current commit hash if mirror exists, None otherwise
        """
        if not self.mirror_exists(repo_url):
            return None
        
        mirror_path = self.get_mirror_path(repo_url)
        try:
            repo = git.Repo(mirror_path)
            return repo.head.commit.hexsha
        except Exception:
            return None
    
    def create_mirror(self, repo_url: str, ref: str = "main") -> MirrorState:
        """Create new mirror by cloning repository.
        
        Args:
            repo_url: Repository URL to clone
            ref: Git reference to checkout (branch, tag, or commit)
            
        Returns:
            MirrorState for the created mirror
            
        Raises:
            git.GitCommandError: If git operations fail
            OSError: If file system operations fail
            ValueError: If repo_url is malicious or unsafe
        """
        # Validate repository URL for security
        self._validate_repo_url(repo_url)
        
        mirror_path = self.get_mirror_path(repo_url)
        
        # Remove existing mirror if it exists but is invalid
        if mirror_path.exists():
            shutil.rmtree(mirror_path)
        
        # Create mirror directory
        mirror_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Clone repository to temporary location first
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "repo"
                
                # Clone repository with timeout and submodule support
                repo = self._with_timeout(
                    lambda: git.Repo.clone_from(url=repo_url, to_path=temp_path, recurse_submodules=True),
                    timeout=300  # Increase timeout to 5 minutes for problematic repos
                )
                
                # Checkout requested ref with timeout
                try:
                    self._with_timeout(lambda: repo.git.checkout(ref))
                    resolved_commit = repo.head.commit.hexsha
                except git.GitCommandError as e:
                    if "pathspec" in str(e).lower():
                        raise ValueError(f"Reference '{ref}' not found in repository")
                    raise
                
                # Move cloned repo contents to final location
                for item in temp_path.iterdir():
                    shutil.move(str(item), str(mirror_path / item.name))
            
            # Return mirror state
            return MirrorState(resolved_commit=resolved_commit)
            
        except Exception as e:
            # Cleanup on failure
            if mirror_path.exists():
                shutil.rmtree(mirror_path)
            raise
    
    def _check_commit_exists_locally(self, repo: git.Repo, ref: str) -> Optional[str]:
        """Check if a commit/ref exists locally and return its SHA.
        
        Args:
            repo: Git repository object
            ref: Git reference (branch, tag, or commit SHA)
            
        Returns:
            Commit SHA if ref exists locally, None otherwise
        """
        try:
            # Try to resolve the ref to a commit SHA
            commit = repo.commit(ref)
            return commit.hexsha
        except (git.BadName, git.BadObject, ValueError):
            return None
    
    def update_mirror(self, repo_url: str, ref: str) -> MirrorState:
        """Update existing mirror or create new one with smart git operations.
        
        Args:
            repo_url: Repository URL
            ref: Git reference to checkout
            
        Returns:
            Updated MirrorState
            
        Raises:
            ValueError: If repo_url is malicious or unsafe
        """
        # Validate repository URL for security
        self._validate_repo_url(repo_url)
        
        mirror_path = self.get_mirror_path(repo_url)
        
        if not self.mirror_exists(repo_url):
            # Create new mirror if it doesn't exist
            return self.create_mirror(repo_url, ref)
        
        try:
            repo = git.Repo(mirror_path)
            
            # For branch references, always fetch to get latest commits
            # For commit SHAs and tags, check locally first
            is_commit_sha = len(ref) == 40 and all(c in '0123456789abcdef' for c in ref.lower())
            is_tag = ref.startswith('v') or ref in [tag.name for tag in repo.tags]
            
            if is_commit_sha or is_tag:
                # Check if we already have the target ref locally
                resolved_commit = self._check_commit_exists_locally(repo, ref)
                
                if resolved_commit is None:
                    # We don't have the ref locally, need to fetch
                    self._with_timeout(lambda: repo.remotes.origin.fetch())
                    
                    # Try to resolve the ref again after fetching
                    resolved_commit = self._check_commit_exists_locally(repo, ref)
                    
                    if resolved_commit is None:
                        raise ValueError(f"Reference '{ref}' not found in repository after fetch")
            else:
                # For branch references, always fetch to get latest commits
                # Fetch with explicit refspec to ensure branch updates
                refspec = f"+refs/heads/*:refs/remotes/origin/*"
                self._with_timeout(lambda: repo.remotes.origin.fetch(refspec))
                
                # For branches, check the remote tracking branch
                try:
                    # Try to get the commit from the remote tracking branch
                    remote_ref = f"origin/{ref}"
                    remote_commit = repo.commit(remote_ref)
                    resolved_commit = remote_commit.hexsha
                    
                    # Update local branch to match remote
                    if repo.heads[ref].commit.hexsha != resolved_commit:
                        repo.heads[ref].set_commit(remote_commit)
                        
                except (git.BadName, git.BadObject, AttributeError):
                    # Fall back to checking local ref
                    resolved_commit = self._check_commit_exists_locally(repo, ref)
                
                if resolved_commit is None:
                    raise ValueError(f"Reference '{ref}' not found in repository after fetch")
            
            # Always checkout the target commit to ensure working directory is correct
            try:
                # Always checkout to ensure working directory matches target commit
                self._with_timeout(lambda: repo.git.checkout('-f', resolved_commit))
                
                # Verify checkout was successful
                actual_commit = repo.head.commit.hexsha
                if actual_commit != resolved_commit:
                    raise ValueError(f"Checkout failed: expected {resolved_commit}, got {actual_commit}")
                
                # Update submodules if they exist
                if repo.submodules:
                    self._update_submodules(repo)
                    
            except git.GitCommandError as e:
                if "pathspec" in str(e).lower():
                    raise ValueError(f"Reference '{ref}' not found in repository")
                raise
            
            # Return mirror state
            return MirrorState(resolved_commit=resolved_commit)
            
        except GitOperationTimeout:
            # Re-raise timeout errors to allow caller to handle appropriately
            raise
        except Exception as e:
            # If update fails due to non-timeout issues, try fresh clone
            return self.create_mirror(repo_url, ref)
    
    def remove_mirror(self, repo_url: str) -> bool:
        """Remove mirror directory for repository.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            True if mirror was removed, False if it didn't exist
        """
        mirror_path = self.get_mirror_path(repo_url)
        if mirror_path.exists():
            shutil.rmtree(mirror_path)
            return True
        return False
    
    def list_mirrors(self) -> List[str]:
        """List all existing mirror directories.
        
        Returns:
            List of mirror directory hashes
        """
        mirrors = []
        
        if not self.mirror_root.exists():
            return mirrors
        
        for mirror_dir in self.mirror_root.iterdir():
            if mirror_dir.is_dir():
                try:
                    # Check if it's a valid git repository
                    git.Repo(mirror_dir)
                    mirrors.append(mirror_dir.name)
                except (git.InvalidGitRepositoryError, git.NoSuchPathError):
                    continue
        
        return mirrors
    
    def cleanup_invalid_mirrors(self) -> int:
        """Remove mirrors that are invalid or corrupted.
        
        Returns:
            Number of mirrors removed
        """
        removed_count = 0
        
        if not self.mirror_root.exists():
            return removed_count
        
        for mirror_dir in self.mirror_root.iterdir():
            if not mirror_dir.is_dir():
                continue
            
            # Check if it's a valid git repository
            try:
                git.Repo(mirror_dir)
                # Valid repository - keep it
            except Exception:
                # Invalid repository - remove
                shutil.rmtree(mirror_dir)
                removed_count += 1
        
        return removed_count