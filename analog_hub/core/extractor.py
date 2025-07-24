"""Path extraction operations for analog-hub."""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

import yaml
from pydantic import BaseModel, Field

from .config import ImportSpec


class LibraryMetadata(BaseModel):
    """Metadata stored in each installed library directory."""
    library_name: str = Field(..., description="Name of the imported library")
    repo_url: str = Field(..., description="Source repository URL")
    repo_hash: str = Field(..., description="SHA256 hash of repo URL")
    ref: str = Field(..., description="Git reference used")
    resolved_commit: str = Field(..., description="Resolved commit hash")
    source_path: str = Field(..., description="Source path within repository")
    local_path: str = Field(..., description="Local installation path")
    checksum: str = Field(..., description="Content checksum for validation")
    installed_at: str = Field(..., description="Installation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    def to_yaml(self, path: Path) -> None:
        """Save metadata to YAML file."""
        data = self.model_dump()
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    @classmethod
    def from_yaml(cls, path: Path) -> "LibraryMetadata":
        """Load metadata from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)


class PathExtractor:
    """Manages selective path extraction from mirrors to project directories."""
    
    def __init__(self, project_root: Path = Path(".")):
        """Initialize path extractor.
        
        Args:
            project_root: Root directory of the project (default: current directory)
        """
        self.project_root = Path(project_root).resolve()
    
    def _calculate_directory_checksum(self, directory: Path) -> str:
        """Calculate SHA256 checksum of directory contents.
        
        Args:
            directory: Directory to checksum
            
        Returns:
            Hex string of SHA256 checksum
        """
        if not directory.exists() or not directory.is_dir():
            return ""
        
        sha256_hash = hashlib.sha256()
        
        # Get all files recursively, sorted for consistent ordering
        files = sorted(directory.rglob("*"))
        
        for file_path in files:
            if file_path.is_file():
                # Skip metadata files when calculating checksum
                if file_path.name.startswith(".analog-hub-meta"):
                    continue
                
                # Include relative path in hash for structure validation
                relative_path = file_path.relative_to(directory)
                sha256_hash.update(str(relative_path).encode('utf-8'))
                
                # Include file content in hash
                try:
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(chunk)
                except (OSError, PermissionError):
                    # Include placeholder for unreadable files
                    sha256_hash.update(b"<unreadable>")
        
        return sha256_hash.hexdigest()
    
    def _resolve_local_path(self, library_name: str, import_spec: ImportSpec, library_root: str) -> Path:
        """Resolve the local installation path for a library.
        
        Args:
            library_name: Name/key of the library import
            import_spec: Import specification with local_path override
            library_root: Default library root directory
            
        Returns:
            Resolved absolute path for library installation
        """
        if import_spec.local_path:
            # Use explicit local_path override (absolute path)
            local_path = Path(import_spec.local_path)
            if not local_path.is_absolute():
                local_path = self.project_root / local_path
        else:
            # Use library_root + library_name
            local_path = self.project_root / library_root / library_name
        
        return local_path.resolve()
    
    def extract_library(
        self, 
        library_name: str,
        import_spec: ImportSpec,
        mirror_path: Path,
        library_root: str,
        repo_hash: str,
        resolved_commit: str
    ) -> LibraryMetadata:
        """Extract library from mirror to local project directory.
        
        Args:
            library_name: Name/key of the library import
            import_spec: Import specification (repo, ref, source_path, local_path)
            mirror_path: Path to mirror directory containing cloned repository
            library_root: Default library root directory
            repo_hash: SHA256 hash of repository URL
            resolved_commit: Resolved commit hash
            
        Returns:
            LibraryMetadata for the extracted library
            
        Raises:
            FileNotFoundError: If source_path doesn't exist in mirror
            OSError: If file operations fail
        """
        # Resolve paths
        source_full_path = mirror_path / import_spec.source_path
        local_path = self._resolve_local_path(library_name, import_spec, library_root)
        
        # Validate source path exists
        if not source_full_path.exists():
            raise FileNotFoundError(
                f"Source path '{import_spec.source_path}' not found in repository mirror"
            )
        
        # Remove existing installation if it exists
        if local_path.exists():
            if local_path.is_dir():
                shutil.rmtree(local_path)
            else:
                local_path.unlink()
        
        # Create parent directories
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy source to destination
            if source_full_path.is_dir():
                shutil.copytree(
                    source_full_path, 
                    local_path,
                    symlinks=True,  # Preserve symlinks
                    ignore_dangling_symlinks=True,
                    dirs_exist_ok=False  # Should not exist due to cleanup above
                )
            else:
                # Single file - copy to parent directory with same name
                shutil.copy2(source_full_path, local_path)
            
            # Calculate checksum of extracted content
            if local_path.is_dir():
                checksum = self._calculate_directory_checksum(local_path)
            else:
                with open(local_path, 'rb') as f:
                    checksum = hashlib.sha256(f.read()).hexdigest()
            
            # Create metadata
            now = datetime.now().isoformat()
            metadata = LibraryMetadata(
                library_name=library_name,
                repo_url=import_spec.repo,
                repo_hash=repo_hash,
                ref=import_spec.ref,
                resolved_commit=resolved_commit,
                source_path=import_spec.source_path,
                local_path=str(local_path.relative_to(self.project_root)),
                checksum=checksum,
                installed_at=now,
                updated_at=now
            )
            
            # Save metadata file in the library directory
            if local_path.is_dir():
                metadata_path = local_path / ".analog-hub-meta.yaml"
            else:
                # For single files, save metadata alongside
                metadata_path = local_path.parent / f".analog-hub-meta-{local_path.name}.yaml"
            
            metadata.to_yaml(metadata_path)
            
            return metadata
            
        except Exception:
            # Cleanup on failure
            if local_path.exists():
                if local_path.is_dir():
                    shutil.rmtree(local_path)
                else:
                    local_path.unlink()
            raise
    
    def validate_library(self, library_path: Path) -> Optional[LibraryMetadata]:
        """Validate installed library and return its metadata.
        
        Args:
            library_path: Path to installed library directory
            
        Returns:
            LibraryMetadata if valid, None if invalid or missing
        """
        if not library_path.exists():
            return None
        
        # Find metadata file
        if library_path.is_dir():
            metadata_path = library_path / ".analog-hub-meta.yaml"
        else:
            # Single file - look for metadata alongside
            metadata_path = library_path.parent / f".analog-hub-meta-{library_path.name}.yaml"
        
        if not metadata_path.exists():
            return None
        
        try:
            metadata = LibraryMetadata.from_yaml(metadata_path)
            
            # Validate checksum only if we can calculate it
            try:
                if library_path.is_dir():
                    current_checksum = self._calculate_directory_checksum(library_path)
                else:
                    with open(library_path, 'rb') as f:
                        current_checksum = hashlib.sha256(f.read()).hexdigest()
                
                if current_checksum != metadata.checksum:
                    # Checksum mismatch - library may have been modified
                    return None
            except Exception:
                # If checksum calculation fails, still return metadata but warn
                pass
            
            return metadata
            
        except Exception:
            return None
    
    def remove_library(self, library_path: Path) -> bool:
        """Remove installed library and its metadata.
        
        Args:
            library_path: Path to installed library
            
        Returns:
            True if library was removed, False if it didn't exist
        """
        if not library_path.exists():
            return False
        
        try:
            # Remove metadata file first
            if library_path.is_dir():
                metadata_path = library_path / ".analog-hub-meta.yaml"
                if metadata_path.exists():
                    metadata_path.unlink()
                
                # Remove library directory
                shutil.rmtree(library_path)
            else:
                # Single file - remove metadata alongside
                metadata_path = library_path.parent / f".analog-hub-meta-{library_path.name}.yaml"
                if metadata_path.exists():
                    metadata_path.unlink()
                
                # Remove library file
                library_path.unlink()
            
            return True
            
        except Exception:
            return False
    
    def list_installed_libraries(self, library_root: str) -> Dict[str, LibraryMetadata]:
        """List all installed libraries with their metadata.
        
        Args:
            library_root: Root directory to search for libraries
            
        Returns:
            Dictionary mapping library names to their metadata
        """
        libraries = {}
        library_root_path = self.project_root / library_root
        
        if not library_root_path.exists():
            return libraries
        
        # Search for metadata files
        for metadata_file in library_root_path.rglob(".analog-hub-meta*.yaml"):
            try:
                metadata = LibraryMetadata.from_yaml(metadata_file)
                
                # Verify the library still exists and is valid
                if metadata_file.name == ".analog-hub-meta.yaml":
                    # Directory-based library
                    library_path = metadata_file.parent
                else:
                    # Single file library
                    file_name = metadata_file.name.replace(".analog-hub-meta-", "").replace(".yaml", "")
                    library_path = metadata_file.parent / file_name
                
                # Check if library path exists and metadata is readable
                if library_path.exists():
                    libraries[metadata.library_name] = metadata
                    
            except Exception:
                # Skip invalid metadata files
                continue
        
        return libraries
    
    def update_library_metadata(
        self, 
        library_path: Path, 
        new_commit: str, 
        new_ref: str
    ) -> Optional[LibraryMetadata]:
        """Update metadata for an existing library installation.
        
        Args:
            library_path: Path to installed library
            new_commit: New resolved commit hash
            new_ref: New git reference
            
        Returns:
            Updated LibraryMetadata if successful, None if failed
        """
        metadata = self.validate_library(library_path)
        if not metadata:
            return None
        
        try:
            # Recalculate checksum
            if library_path.is_dir():
                new_checksum = self._calculate_directory_checksum(library_path)
            else:
                with open(library_path, 'rb') as f:
                    new_checksum = hashlib.sha256(f.read()).hexdigest()
            
            # Update metadata
            updated_metadata = LibraryMetadata(
                library_name=metadata.library_name,
                repo_url=metadata.repo_url,
                repo_hash=metadata.repo_hash,
                ref=new_ref,
                resolved_commit=new_commit,
                source_path=metadata.source_path,
                local_path=metadata.local_path,
                checksum=new_checksum,
                installed_at=metadata.installed_at,
                updated_at=datetime.now().isoformat()
            )
            
            # Save updated metadata
            if library_path.is_dir():
                metadata_path = library_path / ".analog-hub-meta.yaml"
            else:
                metadata_path = library_path.parent / f".analog-hub-meta-{library_path.name}.yaml"
            
            updated_metadata.to_yaml(metadata_path)
            return updated_metadata
            
        except Exception:
            return None