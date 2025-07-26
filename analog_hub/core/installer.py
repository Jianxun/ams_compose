"""Installation orchestration for analog-hub."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import AnalogHubConfig, LockFile, LockEntry, ImportSpec
from .mirror import RepositoryMirror
from .extractor import PathExtractor


class InstallationError(Exception):
    """Raised when installation operations fail."""
    pass


class LibraryInstaller:
    """Orchestrates mirror and extraction operations for library installation."""
    
    def __init__(self, 
                 project_root: Path = Path("."),
                 mirror_root: Path = Path(".mirror")):
        """Initialize library installer.
        
        Args:
            project_root: Root directory of the project
            mirror_root: Root directory for repository mirrors
        """
        self.project_root = Path(project_root)
        self.mirror_root = Path(mirror_root)
        
        # Initialize components
        self.mirror_manager = RepositoryMirror(self.mirror_root)
        self.path_extractor = PathExtractor(self.project_root)
        
        # Configuration paths
        self.config_path = self.project_root / "analog-hub.yaml"
        self.lock_path = self.project_root / ".analog-hub.lock"
    
    def load_config(self) -> AnalogHubConfig:
        """Load analog-hub.yaml configuration."""
        if not self.config_path.exists():
            raise InstallationError(f"Configuration file not found: {self.config_path}")
        
        try:
            return AnalogHubConfig.from_yaml(self.config_path)
        except Exception as e:
            raise InstallationError(f"Failed to load configuration: {e}")
    
    def load_lock_file(self) -> LockFile:
        """Load or create lock file."""
        try:
            if self.lock_path.exists():
                return LockFile.from_yaml(self.lock_path)
            else:
                # Create new lock file with default library_root
                config = self.load_config()
                return LockFile(library_root=config.library_root)
        except Exception as e:
            raise InstallationError(f"Failed to load lock file: {e}")
    
    def save_lock_file(self, lock_file: LockFile) -> None:
        """Save lock file to disk."""
        try:
            lock_file.to_yaml(self.lock_path)
        except Exception as e:
            raise InstallationError(f"Failed to save lock file: {e}")
    
    def install_library(self, 
                       library_name: str, 
                       import_spec: ImportSpec,
                       library_root: str) -> LockEntry:
        """Install a single library.
        
        Args:
            library_name: Name of the library to install
            import_spec: Import specification from configuration
            library_root: Default library root directory
            
        Returns:
            LockEntry for the installed library
            
        Raises:
            InstallationError: If installation fails
        """
        try:
            # Step 1: Mirror the repository
            mirror_metadata = self.mirror_manager.update_mirror(
                import_spec.repo, 
                import_spec.ref
            )
            mirror_path = self.mirror_manager.get_mirror_path(import_spec.repo)
            
            # Get resolved commit from mirror metadata
            resolved_commit = mirror_metadata.resolved_commit
            
            # Step 2: Extract the library
            repo_hash = self.mirror_manager._generate_repo_hash(import_spec.repo)
            library_metadata = self.path_extractor.extract_library(
                library_name=library_name,
                import_spec=import_spec,
                mirror_path=mirror_path,
                library_root=library_root,
                repo_hash=repo_hash,
                resolved_commit=resolved_commit
            )
            
            # Step 3: Create lock entry
            timestamp = datetime.now().isoformat()
            lock_entry = LockEntry(
                repo=import_spec.repo,
                ref=import_spec.ref,
                commit=resolved_commit,
                source_path=import_spec.source_path,
                local_path=library_metadata.local_path,
                checksum=library_metadata.checksum,
                installed_at=timestamp
            )
            
            return lock_entry
            
        except Exception as e:
            raise InstallationError(f"Failed to install library '{library_name}': {e}")
    
    def install_all(self, library_names: Optional[List[str]] = None, force: bool = False) -> Dict[str, LockEntry]:
        """Install all libraries or specific subset with smart skip logic.
        
        Args:
            library_names: Optional list of specific libraries to install.
                          If None, installs all libraries from configuration.
            force: If True, force reinstall even if libraries are up-to-date.
                  If False, skip libraries that are already installed at correct version.
            
        Returns:
            Dictionary mapping library names to their lock entries (only changed libraries)
            
        Raises:
            InstallationError: If any installation fails
        """
        # Load configuration
        config = self.load_config()
        
        # Determine libraries to install
        if library_names is None:
            libraries_to_install = config.imports
        else:
            libraries_to_install = {
                name: spec for name, spec in config.imports.items() 
                if name in library_names
            }
            
            # Check for missing libraries
            missing = set(library_names) - set(config.imports.keys())
            if missing:
                raise InstallationError(f"Libraries not found in configuration: {missing}")
        
        if not libraries_to_install:
            return {}
        
        # Load current lock file to check what's already installed
        lock_file = self.load_lock_file()
        
        # Filter libraries that need installation/update (smart skip logic)
        libraries_needing_work = {}
        skipped_libraries = []
        
        for library_name, import_spec in libraries_to_install.items():
            if force:
                # Force mode: always install
                libraries_needing_work[library_name] = import_spec
            elif library_name not in lock_file.libraries:
                # Library not installed: needs installation
                libraries_needing_work[library_name] = import_spec
                print(f"📦 Installing {library_name} (new library)")
            else:
                # Library installed: check if update needed
                current_entry = lock_file.libraries[library_name]
                
                # Check if configuration changed (repo, ref, or source_path)
                if (current_entry.repo != import_spec.repo or 
                    current_entry.ref != import_spec.ref or
                    current_entry.source_path != import_spec.source_path):
                    libraries_needing_work[library_name] = import_spec
                    print(f"🔄 Updating {library_name} (configuration changed)")
                else:
                    # Check if library files still exist and are valid
                    library_path = self.project_root / current_entry.local_path
                    metadata_path = library_path / ".analog-hub-meta.yaml" if library_path.is_dir() else library_path.parent / f".analog-hub-meta-{library_path.name}.yaml"
                    
                    if not library_path.exists() or not metadata_path.exists():
                        libraries_needing_work[library_name] = import_spec
                        print(f"🔄 Reinstalling {library_name} (library files missing)")
                    else:
                        # Library is up-to-date, skip it
                        skipped_libraries.append(library_name)
                        print(f"⏭️  Skipping {library_name} (up-to-date)")
        
        # Show summary of what will be processed
        if skipped_libraries:
            print(f"Skipped {len(skipped_libraries)} up-to-date libraries")
        
        if not libraries_needing_work:
            print("All libraries are up-to-date")
            return {}
        
        # Install/update libraries that need work
        installed_libraries = {}
        failed_libraries = []
        
        for library_name, import_spec in libraries_needing_work.items():
            try:
                lock_entry = self.install_library(
                    library_name, 
                    import_spec, 
                    config.library_root
                )
                installed_libraries[library_name] = lock_entry
                
                # Show what changed if this was an update
                if library_name in lock_file.libraries:
                    old_commit = lock_file.libraries[library_name].commit
                    if old_commit != lock_entry.commit:
                        print(f"✓ Updated {library_name}: {old_commit[:8]} → {lock_entry.commit[:8]}")
                    else:
                        print(f"✓ Reinstalled {library_name}: {lock_entry.commit[:8]}")
                else:
                    print(f"✓ Installed {library_name}: {lock_entry.commit[:8]}")
                
            except Exception as e:
                failed_libraries.append((library_name, str(e)))
                print(f"✗ Failed to process library: {library_name} - {e}")
        
        # Handle failures
        if failed_libraries:
            failure_summary = "\n".join([f"  - {name}: {error}" for name, error in failed_libraries])
            raise InstallationError(f"Failed to install {len(failed_libraries)} libraries:\n{failure_summary}")
        
        # Update lock file
        lock_file = self.load_lock_file()
        lock_file.library_root = config.library_root
        lock_file.libraries.update(installed_libraries)
        self.save_lock_file(lock_file)
        
        return installed_libraries
    
    def list_installed_libraries(self) -> Dict[str, LockEntry]:
        """List all currently installed libraries.
        
        Returns:
            Dictionary mapping library names to their lock entries
        """
        lock_file = self.load_lock_file()
        return lock_file.libraries.copy()
    
    def validate_installation(self) -> Tuple[List[str], List[str]]:
        """Validate current installation state.
        
        Returns:
            Tuple of (valid_libraries, invalid_libraries)
        """
        lock_file = self.load_lock_file()
        valid_libraries = []
        invalid_libraries = []
        
        for library_name, lock_entry in lock_file.libraries.items():
            try:
                # Check if library still exists and validate checksum
                library_path = self.project_root / lock_entry.local_path
                if not library_path.exists():
                    invalid_libraries.append(f"{library_name}: library directory not found")
                    continue
                
                # Validate metadata and checksum
                metadata_path = library_path / ".analog-hub-meta.yaml"
                if not metadata_path.exists():
                    invalid_libraries.append(f"{library_name}: metadata file missing")
                    continue
                
                from .extractor import LibraryMetadata
                metadata = LibraryMetadata.from_yaml(metadata_path)
                
                # Verify checksum
                current_checksum = self.path_extractor._calculate_directory_checksum(library_path)
                if current_checksum != lock_entry.checksum:
                    invalid_libraries.append(f"{library_name}: checksum mismatch (modified?)")
                    continue
                
                valid_libraries.append(library_name)
                
            except Exception as e:
                invalid_libraries.append(f"{library_name}: validation error - {e}")
        
        return valid_libraries, invalid_libraries
    
    def clean_unused_mirrors(self) -> List[str]:
        """Remove unused mirrors not referenced by any installed library.
        
        Returns:
            List of removed mirror directories
        """
        lock_file = self.load_lock_file()
        
        # Get repo URLs that are currently in use
        used_repos = {entry.repo for entry in lock_file.libraries.values()}
        
        # Get all existing mirrors
        existing_mirrors = self.mirror_manager.list_mirrors()
        
        # Find unused mirrors
        removed_mirrors = []
        for repo_url, metadata in existing_mirrors.items():
            if repo_url not in used_repos:
                try:
                    self.mirror_manager.remove_mirror(repo_url)
                    removed_mirrors.append(self.mirror_manager.get_mirror_path(repo_url))
                    print(f"Removed unused mirror: {repo_url}")
                except Exception as e:
                    print(f"Warning: Failed to remove mirror {repo_url}: {e}")
        
        return removed_mirrors