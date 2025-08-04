"""Installation orchestration for ams-compose."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import ComposeConfig, LockFile, LockEntry, ImportSpec
from .mirror import RepositoryMirror
from .extractor import PathExtractor
from ..utils.checksum import ChecksumCalculator
from ..utils.license import LicenseDetector

logger = logging.getLogger(__name__)


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
        self.config_path = self.project_root / "ams-compose.yaml"
        self.lock_path = self.project_root / ".ams-compose.lock"
    
    def _validate_library_path(self, local_path: str, library_name: str) -> Path:
        """Validate that library path is safe and within project directory.
        
        Args:
            local_path: Local path string from lock entry
            library_name: Name of the library (for error messages)
            
        Returns:
            Validated absolute path
            
        Raises:
            ValueError: If path attempts to escape project directory
        """
        library_path = Path(local_path)
        if not library_path.is_absolute():
            library_path = self.project_root / local_path
        
        resolved_path = library_path.resolve()
        
        # Security check: Prevent path traversal attacks
        try:
            resolved_path.relative_to(self.project_root.resolve())
        except ValueError:
            raise ValueError(
                f"Security error: library '{library_name}' path '{local_path}' "
                f"attempts to escape project directory. Resolved path: {resolved_path}"
            )
        
        return resolved_path
    
    def load_config(self) -> ComposeConfig:
        """Load ams-compose.yaml configuration."""
        if not self.config_path.exists():
            raise InstallationError(f"Configuration file not found: {self.config_path}")
        
        try:
            return ComposeConfig.from_yaml(self.config_path)
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
            
            # Note: .gitignore injection now handled in PathExtractor.extract_library()
            # before checksum calculation to fix race condition
            
            return lock_entry
            
        except Exception as e:
            raise InstallationError(f"Failed to install library '{library_name}': {e}")
    
    def _resolve_target_libraries(self, library_names: Optional[List[str]], config: ComposeConfig) -> Dict[str, ImportSpec]:
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

    def _determine_libraries_needing_work(self, libraries_to_install: Dict[str, ImportSpec], lock_file: LockFile, force: bool, check_remote_updates: bool = False) -> Tuple[Dict[str, ImportSpec], List[str]]:
        """Determine which libraries need installation/update using smart skip logic.
        
        Args:
            libraries_to_install: Libraries that could potentially be installed
            lock_file: Current lock file state
            force: If True, force reinstall even if libraries are up-to-date
            check_remote_updates: If True, check remote repositories for updates
            
        Returns:
            Tuple of (libraries_needing_work, skipped_libraries)
        """
        libraries_needing_work = {}
        skipped_libraries = []
        
        for library_name, import_spec in libraries_to_install.items():
            logger.debug(f"Checking library: {library_name}")
            
            if force:
                # Force mode: always install
                logger.debug(f"{library_name}: force=True, adding to work queue")
                libraries_needing_work[library_name] = import_spec
            elif library_name not in lock_file.libraries:
                # Library not installed: needs installation
                logger.debug(f"{library_name}: not in lock file, needs installation")
                libraries_needing_work[library_name] = import_spec
            else:
                # Library installed: check if update needed
                current_entry = lock_file.libraries[library_name]
                logger.debug(f"{library_name}: exists in lock file, checking for updates")
                
                # Check if configuration changed (repo, ref, or source_path)
                if (current_entry.repo != import_spec.repo or 
                    current_entry.ref != import_spec.ref or
                    current_entry.source_path != import_spec.source_path):
                    logger.debug(f"{library_name}: configuration changed, needs update")
                    libraries_needing_work[library_name] = import_spec
                else:
                    # Check if library files still exist
                    library_path = self._validate_library_path(current_entry.local_path, library_name)
                    
                    if not library_path.exists():
                        logger.debug(f"{library_name}: files missing, needs reinstall")
                        libraries_needing_work[library_name] = import_spec
                    else:
                        if check_remote_updates:
                            # Check if remote has updates by updating mirror and comparing commits
                            logger.debug(f"{library_name}: checking remote for updates via mirror")
                            try:
                                logger.debug(f"{library_name}: calling update_mirror({import_spec.repo}, {import_spec.ref})")
                                mirror_state = self.mirror_manager.update_mirror(
                                    import_spec.repo, 
                                    import_spec.ref
                                )
                                logger.debug(f"{library_name}: mirror updated, resolved commit: {mirror_state.resolved_commit}")
                                
                                # If the resolved commit is different, we need to update
                                if current_entry.commit != mirror_state.resolved_commit:
                                    logger.debug(f"{library_name}: commit changed {current_entry.commit} → {mirror_state.resolved_commit}, needs update")
                                    libraries_needing_work[library_name] = import_spec
                                else:
                                    # Library is truly up-to-date
                                    logger.debug(f"{library_name}: up-to-date, skipping")
                                    skipped_libraries.append(library_name)
                            except Exception as e:
                                # If we can't check for updates, assume library needs work
                                logger.warning(f"{library_name}: failed to check for updates: {e}")
                                libraries_needing_work[library_name] = import_spec
                        else:
                            # Skip remote update check - library is considered up-to-date
                            logger.debug(f"{library_name}: skipping remote update check, considered up-to-date")
                            skipped_libraries.append(library_name)
        
        return libraries_needing_work, skipped_libraries

    def _install_libraries_batch(self, libraries_needing_work: Dict[str, ImportSpec], config: ComposeConfig, lock_file: LockFile) -> Dict[str, LockEntry]:
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
                
                # Determine if this was an install or update and set status fields
                if library_name in lock_file.libraries:
                    old_commit = lock_file.libraries[library_name].commit
                    old_license = lock_file.libraries[library_name].license
                    
                    if old_commit != lock_entry.commit:
                        # This was an update
                        lock_entry.install_status = "updated"
                        
                        # Check if license changed during update
                        if old_license != lock_entry.license and old_license is not None:
                            lock_entry.license_change = f"license changed: {old_license} → {lock_entry.license}"
                            
                        # Check for compatibility warning
                        warning = self.license_detector.get_license_compatibility_warning(lock_entry.license)
                        if warning:
                            lock_entry.license_warning = warning
                    else:
                        # Files were reinstalled but no update needed
                        lock_entry.install_status = "installed"
                else:
                    # This was a new installation
                    lock_entry.install_status = "installed"
                    
                    # Check for compatibility warning for new installations
                    warning = self.license_detector.get_license_compatibility_warning(lock_entry.license)
                    if warning:
                        lock_entry.license_warning = warning
                
            except Exception as e:
                failed_libraries.append((library_name, str(e)))
                # No print statement - error handling moved to structured data
        
        # Handle failures
        if failed_libraries:
            failure_summary = "\n".join([f"  - {name}: {error}" for name, error in failed_libraries])
            raise InstallationError(f"Failed to install {len(failed_libraries)} libraries:\n{failure_summary}")
        
        return installed_libraries

    def _update_lock_file(self, installed_libraries: Dict[str, LockEntry], config: ComposeConfig) -> None:
        """Update and save the lock file with newly installed libraries.
        
        Args:
            installed_libraries: Libraries that were successfully installed
            config: Configuration with library_root setting
        """
        lock_file = self.load_lock_file()
        lock_file.library_root = config.library_root
        lock_file.libraries.update(installed_libraries)
        self.save_lock_file(lock_file)

    def install_all(self, library_names: Optional[List[str]] = None, force: bool = False, check_remote_updates: bool = False) -> Dict[str, LockEntry]:
        """Install all libraries or specific subset with smart skip logic.
        
        Args:
            library_names: Optional list of specific libraries to install.
                          If None, installs all libraries from configuration.
            force: If True, force reinstall even if libraries are up-to-date.
                  If False, skip libraries that are already installed at correct version.
            check_remote_updates: If True, check remote repositories for updates.
                                If False, only install missing libraries (no remote checks).
            
        Returns:
            Dictionary of library_name -> LockEntry for all processed libraries.
            Libraries have install_status set to:
            - "installed": New installation 
            - "updated": Library was updated
            - "up_to_date": Library was already current and skipped
            
        Raises:
            InstallationError: If any installation fails
        """
        logger.debug(f"install_all called with library_names={library_names}, force={force}")
        
        # Load configuration and resolve target libraries
        logger.debug("Loading configuration")
        config = self.load_config()
        logger.debug(f"Configuration loaded with {len(config.imports)} libraries")
        
        libraries_to_install = self._resolve_target_libraries(library_names, config)
        logger.debug(f"Resolved {len(libraries_to_install)} libraries to install")
        
        if not libraries_to_install:
            logger.debug("No libraries to install, returning empty dict")
            return {}
        
        # Load current lock file and determine what needs work
        logger.debug("Loading lock file")
        lock_file = self.load_lock_file()
        logger.debug(f"Lock file loaded with {len(lock_file.libraries)} existing libraries")
        
        logger.debug("Determining libraries needing work")
        libraries_needing_work, skipped_libraries = self._determine_libraries_needing_work(
            libraries_to_install, lock_file, force, check_remote_updates
        )
        logger.debug(f"Libraries needing work: {len(libraries_needing_work)}, skipped: {len(skipped_libraries)}")
        
        # Get up-to-date libraries info
        logger.debug("Processing up-to-date libraries")
        up_to_date_libraries = {}
        for library_name in skipped_libraries:
            if library_name in lock_file.libraries:
                lock_entry = lock_file.libraries[library_name].model_copy()
                lock_entry.install_status = "up_to_date"
                up_to_date_libraries[library_name] = lock_entry
        
        if not libraries_needing_work:
            logger.debug("No libraries need work, returning up-to-date libraries")
            return up_to_date_libraries
        
        # Install/update libraries that need work
        logger.debug(f"Installing batch of {len(libraries_needing_work)} libraries")
        installed_libraries = self._install_libraries_batch(libraries_needing_work, config, lock_file)
        logger.debug(f"Batch installation completed, got {len(installed_libraries)} results")
        
        # Update lock file with new installations
        logger.debug("Updating lock file")
        self._update_lock_file(installed_libraries, config)
        logger.debug("Lock file updated")
        
        # Combine all processed libraries into single result
        all_libraries = {}
        all_libraries.update(installed_libraries)
        all_libraries.update(up_to_date_libraries)
        
        logger.debug(f"install_all returning {len(all_libraries)} total libraries")
        return all_libraries
    
    def list_installed_libraries(self) -> Dict[str, LockEntry]:
        """List all currently installed libraries.
        
        Returns:
            Dictionary mapping library names to their lock entries
        """
        lock_file = self.load_lock_file()
        return lock_file.libraries.copy()
    
    def validate_library(self, library_name: str, lock_entry: LockEntry) -> LockEntry:
        """Validate a single library installation.
        
        Args:
            library_name: Name of the library to validate
            lock_entry: Lock entry for the library
            
        Returns:
            LockEntry with updated validation_status field
        """
        try:
            # Check if library exists
            library_path = self._validate_library_path(lock_entry.local_path, "unknown")
            if not library_path.exists():
                # Return a copy with updated validation_status
                updated_entry = lock_entry.model_copy()
                updated_entry.validation_status = "missing"
                return updated_entry
            
            # Verify checksum using correct method for files vs directories
            if library_path.is_dir():
                current_checksum = ChecksumCalculator.calculate_directory_checksum(library_path)
            else:
                current_checksum = ChecksumCalculator.calculate_file_checksum(library_path)
                
            # Check if checksum matches
            if current_checksum != lock_entry.checksum:
                updated_entry = lock_entry.model_copy()
                updated_entry.validation_status = "modified"
                return updated_entry
            
            # Library is valid
            updated_entry = lock_entry.model_copy()
            updated_entry.validation_status = "valid"
            return updated_entry
            
        except Exception:
            # Return error status for any validation exception
            updated_entry = lock_entry.model_copy()
            updated_entry.validation_status = "error"
            return updated_entry
    
    def validate_installation(self) -> Dict[str, LockEntry]:
        """Validate current installation state.
        
        Only validates libraries currently defined in ams-compose.yaml config.
        Libraries in lockfile but not in config are considered orphaned and warned about.
        
        Returns:
            Dictionary mapping library names to their lock entries with validation_status updated
        """
        lock_file = self.load_lock_file()
        config = self.load_config()
        
        validation_results = {}
        
        # Get current library names from config
        current_library_names = set(config.imports.keys())
        lockfile_library_names = set(lock_file.libraries.keys())
        
        # Find orphaned libraries (in lockfile but not in current config)
        orphaned_libraries = lockfile_library_names - current_library_names
        
        # Include orphaned libraries in results with special status
        for orphaned_lib in orphaned_libraries:
            orphaned_entry = lock_file.libraries[orphaned_lib].model_copy()
            orphaned_entry.validation_status = "orphaned"
            validation_results[orphaned_lib] = orphaned_entry
        
        # Validate libraries that exist in current config
        for library_name in current_library_names:
            if library_name not in lock_file.libraries:
                # Create a placeholder entry for missing libraries
                # This allows CLI to show missing libraries consistently
                missing_entry = LockEntry(
                    repo="unknown",
                    ref="unknown", 
                    commit="unknown",
                    source_path="unknown",
                    local_path="unknown",
                    checksum="unknown",
                    installed_at="unknown",
                    updated_at="unknown",
                    validation_status="not_installed"
                )
                validation_results[library_name] = missing_entry
                continue
                
            lock_entry = lock_file.libraries[library_name]
            # Use the new validate_library method
            validated_entry = self.validate_library(library_name, lock_entry)
            validation_results[library_name] = validated_entry
        
        return validation_results
    
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
        """Update library-specific .gitignore file based on library's checkin setting.
        
        Creates individual .gitignore files inside each library directory that has checkin=false,
        containing '*' to ignore all files in that directory. This keeps the main project
        .gitignore clean and avoids conflicts with user modifications.
        
        Args:
            library_name: Name of the library
            lock_entry: Lock entry containing checkin setting and local_path
        """
        library_path = self._validate_library_path(lock_entry.local_path, library_name)
        library_gitignore_path = library_path / ".gitignore"
        
        if not lock_entry.checkin:
            # Library should be ignored - create .gitignore inside library directory
            if library_path.exists():
                # Create .gitignore that ignores all files but keeps itself tracked
                # This makes the directory visible in git while ignoring library content
                gitignore_content = f"""# Library: {library_name} (checkin: false)
# This library is not checked into version control
# Run 'ams-compose install' to download this library
*
!.gitignore
"""
                library_gitignore_path.write_text(gitignore_content)
        else:
            # Library should be checked in - remove library-specific .gitignore if it exists
            if library_gitignore_path.exists():
                library_gitignore_path.unlink()