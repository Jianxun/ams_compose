"""Repository mirroring operations for analog-hub."""

import hashlib
import shutil
import tempfile
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import git
import yaml
from pydantic import BaseModel, Field


class GitOperationTimeout(Exception):
    """Raised when git operation times out."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for operation timeout."""
    raise GitOperationTimeout("Git operation timed out")


class MirrorMetadata(BaseModel):
    """Metadata stored in each mirror directory."""
    repo_url: str = Field(..., description="Original repository URL")
    repo_hash: str = Field(..., description="SHA256 hash of repo URL")
    current_ref: str = Field(..., description="Currently checked out ref")
    resolved_commit: str = Field(..., description="Resolved commit hash")
    created_at: str = Field(..., description="Mirror creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    def to_yaml(self, path: Path) -> None:
        """Save metadata to YAML file."""
        data = self.model_dump()
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    @classmethod
    def from_yaml(cls, path: Path) -> "MirrorMetadata":
        """Load metadata from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)


class RepositoryMirror:
    """Manages repository mirroring operations."""
    
    def __init__(self, mirror_root: Path = Path(".mirror"), git_timeout: int = 60):
        """Initialize mirror manager.
        
        Args:
            mirror_root: Root directory for all mirrors (default: .mirror)
            git_timeout: Timeout for git operations in seconds (default: 60)
        """
        self.mirror_root = Path(mirror_root)
        self.mirror_root.mkdir(exist_ok=True)
        self.git_timeout = git_timeout
    
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
    
    def _normalize_repo_url(self, repo_url: str) -> str:
        """Normalize repository URL for consistent hashing.
        
        Args:
            repo_url: Repository URL in various formats
            
        Returns:
            Normalized URL string
        """
        # Remove trailing slashes and .git suffixes
        normalized = repo_url.rstrip('/')
        if normalized.endswith('.git'):
            normalized = normalized[:-4]
        
        # Convert SSH URLs to HTTPS for consistency
        if normalized.startswith('git@github.com:'):
            normalized = normalized.replace('git@github.com:', 'https://github.com/')
        elif normalized.startswith('git@gitlab.com:'):
            normalized = normalized.replace('git@gitlab.com:', 'https://gitlab.com/')
        
        return normalized.lower()
    
    def _generate_repo_hash(self, repo_url: str) -> str:
        """Generate SHA256 hash for repository URL.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            16-character hex hash (first 64 bits of SHA256)
        """
        normalized_url = self._normalize_repo_url(repo_url)
        hash_bytes = hashlib.sha256(normalized_url.encode('utf-8')).digest()
        return hash_bytes[:8].hex()  # First 8 bytes = 16 hex chars
    
    def get_mirror_path(self, repo_url: str) -> Path:
        """Get mirror directory path for repository.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Path to mirror directory
        """
        repo_hash = self._generate_repo_hash(repo_url)
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
    
    def get_mirror_metadata(self, repo_url: str) -> Optional[MirrorMetadata]:
        """Get metadata for existing mirror.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            MirrorMetadata if mirror exists, None otherwise
        """
        if not self.mirror_exists(repo_url):
            return None
        
        mirror_path = self.get_mirror_path(repo_url)
        metadata_path = mirror_path / ".mirror-meta.yaml"
        
        if not metadata_path.exists():
            return None
        
        try:
            return MirrorMetadata.from_yaml(metadata_path)
        except Exception:
            return None
    
    def create_mirror(self, repo_url: str, ref: str = "main") -> MirrorMetadata:
        """Create new mirror by cloning repository.
        
        Args:
            repo_url: Repository URL to clone
            ref: Git reference to checkout (branch, tag, or commit)
            
        Returns:
            MirrorMetadata for the created mirror
            
        Raises:
            git.GitCommandError: If git operations fail
            OSError: If file system operations fail
        """
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
                
                # Clone repository with timeout
                repo = self._with_timeout(
                    lambda: git.Repo.clone_from(url=repo_url, to_path=temp_path),
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
            
            # Create metadata
            now = datetime.now().isoformat()
            repo_hash = self._generate_repo_hash(repo_url)
            
            metadata = MirrorMetadata(
                repo_url=repo_url,
                repo_hash=repo_hash,
                current_ref=ref,
                resolved_commit=resolved_commit,
                created_at=now,
                updated_at=now
            )
            
            # Save metadata
            metadata_path = mirror_path / ".mirror-meta.yaml"
            metadata.to_yaml(metadata_path)
            
            return metadata
            
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
    
    def update_mirror(self, repo_url: str, ref: str) -> MirrorMetadata:
        """Update existing mirror or create new one with smart git operations.
        
        Args:
            repo_url: Repository URL
            ref: Git reference to checkout
            
        Returns:
            Updated MirrorMetadata
        """
        mirror_path = self.get_mirror_path(repo_url)
        existing_metadata = self.get_mirror_metadata(repo_url)
        
        if not self.mirror_exists(repo_url):
            # Create new mirror if it doesn't exist
            return self.create_mirror(repo_url, ref)
        
        try:
            repo = git.Repo(mirror_path)
            
            # First, check if we already have the target ref locally
            resolved_commit = self._check_commit_exists_locally(repo, ref)
            
            if resolved_commit is None:
                # We don't have the ref locally, need to fetch
                self._with_timeout(lambda: repo.remotes.origin.fetch())
                
                # Try to resolve the ref again after fetching
                resolved_commit = self._check_commit_exists_locally(repo, ref)
                
                if resolved_commit is None:
                    raise ValueError(f"Reference '{ref}' not found in repository after fetch")
            
            # Checkout the target ref (this is fast since we verified it exists)
            try:
                current_commit = repo.head.commit.hexsha
                if current_commit != resolved_commit:
                    self._with_timeout(lambda: repo.git.checkout('-f', ref))
            except git.GitCommandError as e:
                if "pathspec" in str(e).lower():
                    raise ValueError(f"Reference '{ref}' not found in repository")
                raise
            
            # Update metadata
            repo_hash = self._generate_repo_hash(repo_url)
            created_at = existing_metadata.created_at if existing_metadata else datetime.now().isoformat()
            
            metadata = MirrorMetadata(
                repo_url=repo_url,
                repo_hash=repo_hash,
                current_ref=ref,
                resolved_commit=resolved_commit,
                created_at=created_at,
                updated_at=datetime.now().isoformat()
            )
            
            # Save updated metadata
            metadata_path = mirror_path / ".mirror-meta.yaml"
            metadata.to_yaml(metadata_path)
            
            return metadata
            
        except Exception as e:
            # If update fails, try fresh clone
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
    
    def list_mirrors(self) -> Dict[str, MirrorMetadata]:
        """List all existing mirrors with their metadata.
        
        Returns:
            Dictionary mapping repo URLs to their metadata
        """
        mirrors = {}
        
        if not self.mirror_root.exists():
            return mirrors
        
        for mirror_dir in self.mirror_root.iterdir():
            if not mirror_dir.is_dir():
                continue
            
            metadata_path = mirror_dir / ".mirror-meta.yaml"
            if metadata_path.exists():
                try:
                    metadata = MirrorMetadata.from_yaml(metadata_path)
                    mirrors[metadata.repo_url] = metadata
                except Exception:
                    # Skip invalid metadata files
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
                # Also check if metadata exists
                metadata_path = mirror_dir / ".mirror-meta.yaml"
                if metadata_path.exists():
                    MirrorMetadata.from_yaml(metadata_path)
                else:
                    # Missing metadata - remove
                    shutil.rmtree(mirror_dir)
                    removed_count += 1
            except Exception:
                # Invalid repository or metadata - remove
                shutil.rmtree(mirror_dir)
                removed_count += 1
        
        return removed_count