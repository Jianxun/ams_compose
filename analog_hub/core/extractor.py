"""Path extraction operations for analog-hub."""

import shutil
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

from .config import ImportSpec
from ..utils.checksum import ChecksumCalculator


@dataclass
class ExtractionState:
    """Lightweight state information returned by extraction operations."""
    local_path: str
    checksum: str




class PathExtractor:
    """Manages selective path extraction from mirrors to project directories."""
    
    def __init__(self, project_root: Path = Path(".")):
        """Initialize path extractor.
        
        Args:
            project_root: Root directory of the project (default: current directory)
        """
        self.project_root = Path(project_root).resolve()
    
    
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
    ) -> ExtractionState:
        """Extract library from mirror to local project directory.
        
        Args:
            library_name: Name/key of the library import
            import_spec: Import specification (repo, ref, source_path, local_path)
            mirror_path: Path to mirror directory containing cloned repository
            library_root: Default library root directory
            repo_hash: SHA256 hash of repository URL
            resolved_commit: Resolved commit hash
            
        Returns:
            ExtractionState with local path and checksum
            
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
                checksum = ChecksumCalculator.calculate_directory_checksum(local_path)
            else:
                checksum = ChecksumCalculator.calculate_file_checksum(local_path)
            
            # Return extraction state
            return ExtractionState(
                local_path=str(local_path.relative_to(self.project_root)),
                checksum=checksum
            )
            
        except Exception:
            # Cleanup on failure
            if local_path.exists():
                if local_path.is_dir():
                    shutil.rmtree(local_path)
                else:
                    local_path.unlink()
            raise
    
    def validate_library(self, library_path: Path) -> Optional[str]:
        """Validate installed library and return its checksum.
        
        Args:
            library_path: Path to installed library directory
            
        Returns:
            Checksum if valid, None if library doesn't exist
        """
        if not library_path.exists():
            return None
        
        try:
            if library_path.is_dir():
                return ChecksumCalculator.calculate_directory_checksum(library_path)
            else:
                return ChecksumCalculator.calculate_file_checksum(library_path)
        except Exception:
            return None
    
    def remove_library(self, library_path: Path) -> bool:
        """Remove installed library.
        
        Args:
            library_path: Path to installed library
            
        Returns:
            True if library was removed, False if it didn't exist
        """
        if not library_path.exists():
            return False
        
        try:
            if library_path.is_dir():
                shutil.rmtree(library_path)
            else:
                library_path.unlink()
            
            return True
            
        except Exception:
            return False
    
    def list_installed_libraries(self, library_root: str) -> Dict[str, Path]:
        """List all installed libraries.
        
        Args:
            library_root: Root directory to search for libraries
            
        Returns:
            Dictionary mapping library names to their paths
        """
        libraries = {}
        library_root_path = self.project_root / library_root
        
        if not library_root_path.exists():
            return libraries
        
        # Search for directories and files in library root
        for item in library_root_path.iterdir():
            if item.is_dir() or item.is_file():
                libraries[item.name] = item
        
        return libraries
    
    def calculate_library_checksum(self, library_path: Path) -> Optional[str]:
        """Calculate checksum for an existing library installation.
        
        Args:
            library_path: Path to installed library
            
        Returns:
            Checksum if successful, None if failed
        """
        if not library_path.exists():
            return None
        
        try:
            if library_path.is_dir():
                return ChecksumCalculator.calculate_directory_checksum(library_path)
            else:
                return ChecksumCalculator.calculate_file_checksum(library_path)
        except Exception:
            return None