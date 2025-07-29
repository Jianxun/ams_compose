"""Installation orchestration for analog-hub."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import AnalogHubConfig, LockFile, LockEntry, ImportSpec
from .mirror import RepositoryMirror
from .extractor import PathExtractor
from ..utils.checksum import ChecksumCalculator
from ..utils.license import LicenseDetector


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
        self.license_detector = LicenseDetector()
        
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
                       library_root: str,
                       existing_entry: Optional[LockEntry] = None) -> LockEntry:
        """Install a single library.
        
        Args:
            library_name: Name of the library to install
            import_spec: Import specification from configuration
            library_root: Default library root directory
            existing_entry: Optional existing lock entry for timestamp preservation during updates
            
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
            repo_hash = ChecksumCalculator.generate_repo_hash(import_spec.repo)
            library_metadata = self.path_extractor.extract_library(
                library_name=library_name,
                import_spec=import_spec,
                mirror_path=mirror_path,
                library_root=library_root,
                repo_hash=repo_hash,
                resolved_commit=resolved_commit
            )
            
            # Step 3: Detect license information
            license_info = self.license_detector.detect_license(mirror_path)
            
            # Determine final license: user-specified takes precedence over auto-detected
            final_license = import_spec.license if import_spec.license else license_info.license_type
            
            # Step 4: Create lock entry
            timestamp = datetime.now().isoformat()
            
            # Handle timestamps: preserve installed_at for updates, set both for new installs
            if existing_entry:
                # This is an update: preserve original installed_at timestamp
                installed_at = existing_entry.installed_at
                updated_at = timestamp
            else:
                # This is a fresh install: set both timestamps to now
                installed_at = timestamp
                updated_at = timestamp
            
            lock_entry = LockEntry(
                repo=import_spec.repo,
                ref=import_spec.ref,
                commit=resolved_commit,
                source_path=import_spec.source_path,
                local_path=library_metadata.local_path,
                checksum=library_metadata.checksum,
                installed_at=installed_at,
                updated_at=updated_at,
                checkin=import_spec.checkin,
                license=final_license,
                detected_license=license_info.license_type
            )
            
            # Step 5: Update .gitignore based on checkin field
            self._update_gitignore_for_library(library_name, lock_entry)
            
            return lock_entry
            
        except Exception as e:
            raise InstallationError(f"Failed to install library '{library_name}': {e}")
    
    def _resolve_target_libraries(self, library_names: Optional[List[str]], config: AnalogHubConfig) -> Dict[str, ImportSpec]:
        """Resolve which libraries should be processed based on configuration and user input.
        
        Args:
            library_names: Optional list of specific libraries to install
            config: Loaded configuration with all available libraries
            
        Returns:
            Dictionary of libraries to process with their import specifications
            
        Raises:
            InstallationError: If specified libraries are not found in configuration
        """
        # Handle case where config has no imports
        if not config.imports:
            return {}
            
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
        
        return libraries_to_install

    def _determine_libraries_needing_work(self, libraries_to_install: Dict[str, ImportSpec], lock_file: LockFile, force: bool) -> Tuple[Dict[str, ImportSpec], List[str]]:
        """Determine which libraries need installation/update using smart skip logic.
        
        Args:
            libraries_to_install: Libraries that could potentially be installed
            lock_file: Current lock file state
            force: If True, force reinstall even if libraries are up-to-date
            
        Returns:
            Tuple of (libraries_needing_work, skipped_libraries)
        """
        libraries_needing_work = {}
        skipped_libraries = []
        
        for library_name, import_spec in libraries_to_install.items():
            if force:
                # Force mode: always install
                libraries_needing_work[library_name] = import_spec
            elif library_name not in lock_file.libraries:
                # Library not installed: needs installation
                libraries_needing_work[library_name] = import_spec
            else:
                # Library installed: check if update needed
                current_entry = lock_file.libraries[library_name]
                
                # Check if configuration changed (repo, ref, or source_path)
                if (current_entry.repo != import_spec.repo or 
                    current_entry.ref != import_spec.ref or
                    current_entry.source_path != import_spec.source_path):
                    libraries_needing_work[library_name] = import_spec
                else:
                    # Check if library files still exist
                    library_path = self.project_root / current_entry.local_path
                    
                    if not library_path.exists():
                        libraries_needing_work[library_name] = import_spec
                    else:
                        # Check if remote has updates by updating mirror and comparing commits
                        try:
                            mirror_state = self.mirror_manager.update_mirror(
                                import_spec.repo, 
                                import_spec.ref
                            )
                            
                            
                            # If the resolved commit is different, we need to update
                            if current_entry.commit != mirror_state.resolved_commit:
                                libraries_needing_work[library_name] = import_spec
                            else:
                                # Library is truly up-to-date
                                commit_hash = current_entry.commit[:8]
                                print(f"Library: {library_name} (commit {commit_hash}) [up to date]")
                                skipped_libraries.append(library_name)
                        except Exception as e:
                            # If we can't check for updates, assume library needs work
                            print(f"Warning: Could not check for updates for {library_name}: {e}")
                            libraries_needing_work[library_name] = import_spec
        
        return libraries_needing_work, skipped_libraries

    def _install_libraries_batch(self, libraries_needing_work: Dict[str, ImportSpec], config: AnalogHubConfig, lock_file: LockFile) -> Dict[str, LockEntry]:
        """Install/update a batch of libraries and handle status reporting.
        
        Args:
            libraries_needing_work: Libraries that need installation/update
            config: Configuration with library_root setting
            lock_file: Current lock file for comparison
            
        Returns:
            Dictionary of successfully installed libraries
            
        Raises:
            InstallationError: If any installation fails
        """
        installed_libraries = {}
        failed_libraries = []
        
        for library_name, import_spec in libraries_needing_work.items():
            try:
                # Pass existing entry if available for timestamp preservation during updates
                existing_entry = lock_file.libraries.get(library_name)
                lock_entry = self.install_library(
                    library_name, 
                    import_spec, 
                    config.library_root,
                    existing_entry
                )
                installed_libraries[library_name] = lock_entry
                
                # Determine if this was an install or update
                commit_hash = lock_entry.commit[:8]
                license_info = f" license: {lock_entry.license}" if lock_entry.license else " license: None"
                
                if library_name in lock_file.libraries:
                    old_commit = lock_file.libraries[library_name].commit
                    old_license = lock_file.libraries[library_name].license
                    
                    if old_commit != lock_entry.commit:
                        # Check if license changed during update
                        if old_license != lock_entry.license and old_license is not None:
                            license_change = f" (license changed: {old_license} → {lock_entry.license})"
                            print(f"Library: {library_name} (commit {commit_hash}){license_info}{license_change} [updated]")
                            # Show compatibility warning if needed
                            warning = self.license_detector.get_license_compatibility_warning(lock_entry.license)
                            if warning:
                                print(f"  WARNING: {warning}")
                        else:
                            print(f"Library: {library_name} (commit {commit_hash}){license_info} [updated]")
                    else:
                        print(f"Library: {library_name} (commit {commit_hash}){license_info} [installed]")
                else:
                    print(f"Library: {library_name} (commit {commit_hash}){license_info} [installed]")
                    # Show compatibility warning for new installations
                    warning = self.license_detector.get_license_compatibility_warning(lock_entry.license)
                    if warning:
                        print(f"  WARNING: {warning}")
                
            except Exception as e:
                failed_libraries.append((library_name, str(e)))
                print(f"Library: {library_name} (commit unknown) [error]")
        
        # Handle failures
        if failed_libraries:
            failure_summary = "\n".join([f"  - {name}: {error}" for name, error in failed_libraries])
            raise InstallationError(f"Failed to install {len(failed_libraries)} libraries:\n{failure_summary}")
        
        return installed_libraries

    def _update_lock_file(self, installed_libraries: Dict[str, LockEntry], config: AnalogHubConfig) -> None:
        """Update and save the lock file with newly installed libraries.
        
        Args:
            installed_libraries: Libraries that were successfully installed
            config: Configuration with library_root setting
        """
        lock_file = self.load_lock_file()
        lock_file.library_root = config.library_root
        lock_file.libraries.update(installed_libraries)
        self.save_lock_file(lock_file)

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
        # Load configuration and resolve target libraries
        config = self.load_config()
        libraries_to_install = self._resolve_target_libraries(library_names, config)
        
        if not libraries_to_install:
            return {}
        
        # Load current lock file and determine what needs work
        lock_file = self.load_lock_file()
        libraries_needing_work, skipped_libraries = self._determine_libraries_needing_work(
            libraries_to_install, lock_file, force
        )
        
        if not libraries_needing_work:
            return {}
        
        # Install/update libraries that need work
        installed_libraries = self._install_libraries_batch(libraries_needing_work, config, lock_file)
        
        # Update lock file with new installations
        self._update_lock_file(installed_libraries, config)
        
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
        
        Only validates libraries currently defined in analog-hub.yaml config.
        Libraries in lockfile but not in config are considered orphaned and warned about.
        
        Returns:
            Tuple of (valid_libraries, invalid_libraries_and_warnings)
        """
        lock_file = self.load_lock_file()
        config = self.load_config()
        
        valid_libraries = []
        invalid_libraries = []
        
        # Get current library names from config
        current_library_names = set(config.imports.keys())
        lockfile_library_names = set(lock_file.libraries.keys())
        
        # Find orphaned libraries (in lockfile but not in current config)
        orphaned_libraries = lockfile_library_names - current_library_names
        
        # Add warnings for orphaned libraries
        if orphaned_libraries:
            invalid_libraries.append(f"WARNING: Found {len(orphaned_libraries)} orphaned libraries in lockfile but not in config:")
            for orphaned_lib in sorted(orphaned_libraries):
                invalid_libraries.append(f"  {orphaned_lib}: no longer defined in analog-hub.yaml")
            invalid_libraries.append("  To fix: Run 'analog-hub clean' to remove orphaned libraries from lockfile")
        
        # Only validate libraries that exist in current config
        for library_name in current_library_names:
            if library_name not in lock_file.libraries:
                invalid_libraries.append(f"{library_name}: not installed (missing from lockfile)")
                continue
                
            lock_entry = lock_file.libraries[library_name]
            try:
                # Check if library still exists
                library_path = self.project_root / lock_entry.local_path
                if not library_path.exists():
                    invalid_libraries.append(f"{library_name}: library not found at {lock_entry.local_path}")
                    continue
                
                # Verify checksum using correct method for files vs directories
                if library_path.is_dir():
                    current_checksum = ChecksumCalculator.calculate_directory_checksum(library_path)
                else:
                    current_checksum = ChecksumCalculator.calculate_file_checksum(library_path)
                    
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
        for repo_hash in existing_mirrors:
            # Convert repo_hash back to URL for checking
            # Note: We'll need to track this differently in the new architecture
            # For now, remove all unused mirrors
            try:
                mirror_path = self.mirror_root / repo_hash
                if mirror_path.exists():
                    import shutil
                    shutil.rmtree(mirror_path)
                    removed_mirrors.append(str(mirror_path))
            except Exception as e:
                print(f"Warning: Failed to remove mirror {repo_hash}: {e}")
        
        return removed_mirrors
    
    def clean_orphaned_libraries(self) -> List[str]:
        """Remove orphaned libraries from lockfile that are no longer in config.
        
        Returns:
            List of removed library names
        """
        lock_file = self.load_lock_file()
        config = self.load_config()
        
        # Get current library names from config
        current_library_names = set(config.imports.keys())
        lockfile_library_names = set(lock_file.libraries.keys())
        
        # Find orphaned libraries (in lockfile but not in current config)
        orphaned_libraries = lockfile_library_names - current_library_names
        
        if not orphaned_libraries:
            return []
        
        # Remove orphaned libraries from lockfile
        for orphaned_lib in orphaned_libraries:
            del lock_file.libraries[orphaned_lib]
        
        # Save updated lockfile
        self.save_lock_file(lock_file)
        
        return list(orphaned_libraries)
    
    def _update_gitignore_for_library(self, library_name: str, lock_entry: LockEntry) -> None:
        """Update .gitignore file based on library's checkin setting.
        
        Args:
            library_name: Name of the library
            lock_entry: Lock entry containing checkin setting and local_path
        """
        gitignore_path = self.project_root / ".gitignore"
        
        # Prepare library entry for .gitignore (always with trailing slash for directories)
        library_ignore_line = f"{lock_entry.local_path}/"
        
        # Read existing .gitignore content
        if gitignore_path.exists():
            gitignore_lines = gitignore_path.read_text().splitlines()
        else:
            gitignore_lines = []
        
        # Check if library is already in .gitignore
        library_already_ignored = library_ignore_line in gitignore_lines
        
        if not lock_entry.checkin:
            # Library should be ignored - add to .gitignore if not already there
            if not library_already_ignored:
                gitignore_lines.append(library_ignore_line)
                gitignore_path.write_text('\n'.join(gitignore_lines) + '\n')
        else:
            # Library should be checked in - remove from .gitignore if present
            if library_already_ignored:
                gitignore_lines.remove(library_ignore_line)
                gitignore_path.write_text('\n'.join(gitignore_lines) + '\n')