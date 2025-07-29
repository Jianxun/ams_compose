"""Path extraction operations for analog-hub."""

import shutil
from pathlib import Path
from typing import Optional, Dict, Callable, Set, List
from dataclasses import dataclass

import pathspec

from .config import ImportSpec
from ..utils.checksum import ChecksumCalculator


@dataclass
class ExtractionState:
    """Lightweight state information returned by extraction operations."""
    local_path: str
    checksum: str




class PathExtractor:
    """Manages selective path extraction from mirrors to project directories."""
    
    # Built-in ignore patterns - easily maintainable and extensible
    VCS_IGNORE_PATTERNS = {
        '.git',              # Git repository metadata
        '.gitignore',        # Git ignore rules
        '.gitmodules',       # Git submodules configuration
        '.gitattributes',    # Git attributes configuration
        '.svn',              # SVN metadata
        '.hg',               # Mercurial metadata
        '.bzr',              # Bazaar metadata
        'CVS',               # CVS metadata
    }
    
    DEV_TOOL_IGNORE_PATTERNS = {
        '.ipynb_checkpoints', # Jupyter notebook checkpoints
        '__pycache__',       # Python cache directories
        '*.pyc',             # Python compiled files
        '*.pyo',             # Python optimized files
        'node_modules',      # Node.js dependencies
        '.vscode',           # VS Code settings
        '.idea',             # IntelliJ IDEA settings
    }
    
    OS_IGNORE_PATTERNS = {
        '.DS_Store',         # macOS system files
        'Thumbs.db',         # Windows thumbnail cache
        'desktop.ini',       # Windows desktop settings
    }
    
    # Global ignore file name
    GLOBAL_IGNORE_FILE = '.analog-hub-ignore'
    
    def __init__(self, project_root: Path = Path(".")):
        """Initialize path extractor.
        
        Args:
            project_root: Root directory of the project (default: current directory)
        """
        self.project_root = Path(project_root).resolve()
    
    @classmethod
    def get_builtin_ignore_patterns(cls) -> Set[str]:
        """Get all built-in ignore patterns combined.
        
        Returns:
            Set of all built-in ignore patterns
        """
        return cls.VCS_IGNORE_PATTERNS | cls.DEV_TOOL_IGNORE_PATTERNS | cls.OS_IGNORE_PATTERNS
    
    def _load_global_ignore_patterns(self) -> List[str]:
        """Load global ignore patterns from .analog-hub-ignore file.
        
        Returns:
            List of ignore patterns from global ignore file
        """
        global_ignore_file = self.project_root / self.GLOBAL_IGNORE_FILE
        if not global_ignore_file.exists():
            return []
        
        try:
            with open(global_ignore_file, 'r') as f:
                patterns = []
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        patterns.append(line)
                return patterns
        except Exception:
            # If there's any error reading the file, return empty list
            return []
    
    def _create_ignore_function(
        self, 
        custom_ignore_hook: Optional[Callable[[str, Set[str]], Set[str]]] = None,
        library_ignore_patterns: Optional[List[str]] = None
    ) -> Callable[[str, list], list]:
        """Create ignore function for shutil.copytree with three-tier filtering.
        
        Three-tier filtering system:
        1. Built-in defaults (VCS, development tools, OS files)
        2. Global .analog-hub-ignore patterns (gitignore-style)
        3. Per-library ignore_patterns (gitignore-style)
        
        Args:
            library_ignore_patterns: Library-specific ignore patterns
            custom_ignore_hook: Optional function for additional custom ignores
        
        Returns:
            Function compatible with shutil.copytree ignore parameter
        """
        # Load global ignore patterns
        global_patterns = self._load_global_ignore_patterns()
        
        # Combine all gitignore-style patterns
        all_patterns = global_patterns.copy()
        if library_ignore_patterns:
            all_patterns.extend(library_ignore_patterns)
        
        # Create pathspec matcher if we have patterns
        pathspec_matcher = None
        if all_patterns:
            try:
                pathspec_matcher = pathspec.PathSpec.from_lines('gitwildmatch', all_patterns)
            except Exception:
                # If pathspec fails, continue without pattern matching
                pathspec_matcher = None
        
        def ignore_function(directory: str, filenames: list) -> list:
            ignored = set()
            filenames_set = set(filenames)
            
            # Tier 1: Apply built-in ignore patterns (exact filename matches)
            builtin_ignores = self.get_builtin_ignore_patterns()
            ignored.update(filenames_set.intersection(builtin_ignores))
            
            # Tier 2 & 3: Apply gitignore-style patterns from global and library configs
            if pathspec_matcher:
                for filename in filenames:
                    # Check if this is a directory by looking at the path
                    file_path = Path(directory) / filename
                    is_directory = file_path.is_dir() if file_path.exists() else False
                    
                    # Test multiple pattern variants for better matching
                    test_paths = [
                        filename,           # Direct filename
                        f"./{filename}",    # Relative path
                    ]
                    
                    # For directories, also test with trailing slash
                    if is_directory:
                        test_paths.extend([
                            f"{filename}/",
                            f"./{filename}/"
                        ])
                    
                    # Check if any variant matches
                    if any(pathspec_matcher.match_file(test_path) for test_path in test_paths):
                        ignored.add(filename)
            
            # Backward compatibility: Apply custom ignore hook
            if custom_ignore_hook:
                additional_ignores = custom_ignore_hook(directory, filenames_set)
                ignored.update(additional_ignores)
            
            return list(ignored)
        
        return ignore_function
    
    
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
                # Create ignore function with three-tier filtering
                ignore_func = self._create_ignore_function(
                    library_ignore_patterns=import_spec.ignore_patterns
                )
                
                shutil.copytree(
                    source_full_path, 
                    local_path,
                    symlinks=True,  # Preserve symlinks
                    ignore_dangling_symlinks=True,
                    ignore=ignore_func,  # Apply three-tier filtering
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