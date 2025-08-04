"""Main CLI entry point for ams-compose."""

import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict

import click
from ams_compose import __version__
from ams_compose.core.installer import LibraryInstaller, InstallationError
from ams_compose.core.config import ComposeConfig, LockEntry

# Set up logging
logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Configure logging for the CLI."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
        
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger('ams_compose').setLevel(level)


def _get_installer() -> LibraryInstaller:
    """Get LibraryInstaller instance for current directory."""
    return LibraryInstaller(project_root=Path.cwd())


def _handle_installation_error(e: InstallationError) -> None:
    """Handle installation errors with user-friendly messages."""
    click.echo(f"Error: {e}", err=True)
    sys.exit(1)


def _get_entry_status(entry: LockEntry, command_context: str) -> str:
    """Get appropriate status string for entry based on command context."""
    if command_context == "validate":
        return entry.validation_status or "unknown"
    elif command_context == "install":
        return entry.install_status or entry.validation_status or "unknown"
    else:  # list or default
        return entry.install_status or entry.validation_status or "unknown"


def _show_license_warnings(lock_entry: LockEntry) -> None:
    """Display license warnings for a library entry."""
    if lock_entry.license_change:
        click.echo(f"  ↳ {lock_entry.license_change}")
    
    if lock_entry.license_warning:
        click.echo(f"  ⚠️  WARNING: {lock_entry.license_warning}")
    elif lock_entry.license:
        from ams_compose.utils.license import LicenseDetector
        license_detector = LicenseDetector()
        warning = license_detector.get_license_compatibility_warning(lock_entry.license)
        if warning:
            click.echo(f"  ⚠️  WARNING: {warning}")


def _format_libraries_tabular(libraries: Dict[str, LockEntry], show_status: bool = False, 
                             command_context: str = "list") -> None:
    """Format libraries in clean tabular format with proper column alignment."""
    if not libraries:
        return
        
    # Calculate column widths for alignment
    max_name_width = max(len(name) for name in libraries.keys())
    max_ref_width = max(len(entry.ref) for entry in libraries.values())
    max_license_width = max(len(entry.license or "None") for entry in libraries.values())
    
    for library_name, lock_entry in libraries.items():
        commit_hash = lock_entry.commit[:8]
        license_display = lock_entry.license or "None"
        
        if show_status:
            status = _get_entry_status(lock_entry, command_context)
            click.echo(f"{library_name:<{max_name_width}} | commit:{commit_hash} | ref:{lock_entry.ref:<{max_ref_width}} | license:{license_display:<{max_license_width}} | status:{status}")
            _show_license_warnings(lock_entry)
        else:
            click.echo(f"{library_name:<{max_name_width}} | commit:{commit_hash} | ref:{lock_entry.ref:<{max_ref_width}} | license:{license_display}")


def _format_libraries_detailed(libraries: Dict[str, LockEntry], show_status: bool = False) -> None:
    """Format libraries in detailed multi-line format."""
    if not libraries:
        return
        
    for library_name, lock_entry in libraries.items():
        click.echo(f"{library_name}")
        click.echo(f"  Repository: {lock_entry.repo}")
        click.echo(f"  Reference:  {lock_entry.ref}")
        click.echo(f"  Commit:     {lock_entry.commit}")
        click.echo(f"  Path:       {lock_entry.local_path}")
        click.echo(f"  License:    {lock_entry.license or 'Not detected'}")
        
        if lock_entry.detected_license and lock_entry.license != lock_entry.detected_license:
            click.echo(f"  Auto-detected: {lock_entry.detected_license}")
            
        click.echo(f"  Installed:  {lock_entry.installed_at}")
        
        if show_status:
            status = lock_entry.install_status or lock_entry.validation_status
            if status:
                click.echo(f"  Status:     {status}")
                
            if lock_entry.license_change:
                click.echo(f"  Changes:    {lock_entry.license_change}")
        
        _show_license_warnings(lock_entry)        
        click.echo()


def _format_libraries_summary(libraries: Dict[str, LockEntry], title: str, empty_message: str = None, 
                             show_status: bool = False, command_context: str = "list") -> None:
    """Unified formatter for library summaries across all commands.
    
    Args:
        libraries: Dictionary of library name to LockEntry
        title: Title to display
        empty_message: Custom message when no libraries found
        show_status: Whether to show status information
        command_context: Command context for status priority ("list", "validate", "install")
    """
    if not libraries:
        message = empty_message or f"No {title.lower()}"
        click.echo(message)
        return
        
    click.echo(f"{title} ({len(libraries)}):")
    _format_libraries_tabular(libraries, show_status, command_context)




@click.group()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging (INFO level)')
@click.option('--debug', is_flag=True, help='Enable debug logging (DEBUG level)')
@click.pass_context
def main(ctx, verbose, debug):
    """ams-compose: Dependency management for analog/mixed-signal IC design repositories."""
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    
    # Set up logging
    _setup_logging(verbose, debug)


@main.command()
@click.argument('libraries', nargs=-1)
@click.option('--force', is_flag=True, default=False,
              help='Force reinstall all libraries (ignore up-to-date check)')
def install(libraries: tuple, force: bool):
    """Install missing libraries from ams-compose.yaml.
    
    Only installs libraries that are missing or have configuration changes.
    Does not check remote repositories for updates (use 'update' command for that).
    
    LIBRARIES: Optional list of specific libraries to install.
               If not provided, installs all libraries from configuration.
    """
    try:
        logger.info("Starting install command")
        installer = _get_installer()
        logger.debug("Created installer instance")
        
        # Convert tuple to list for installer
        library_list = list(libraries) if libraries else None
        logger.debug(f"Library list: {library_list}")
        
        if library_list:
            click.echo(f"Installing libraries: {', '.join(library_list)}")
        else:
            click.echo("Installing all libraries from ams-compose.yaml")
        
        logger.debug("About to call installer.install_all()")
        all_libraries = installer.install_all(library_list, force=force, check_remote_updates=False)
        logger.debug("install_all() completed")
        
        logger.debug(f"Got {len(all_libraries)} libraries from install_all")
        
        # Filter libraries by install_status
        up_to_date = {name: entry for name, entry in all_libraries.items() 
                     if entry.install_status == "up_to_date"}
        processed = {name: entry for name, entry in all_libraries.items() 
                    if entry.install_status in ["installed", "updated"]}
        
        logger.debug(f"{len(up_to_date)} up-to-date, {len(processed)} processed")
        
        # Show up-to-date libraries first
        if up_to_date:
            _format_libraries_summary(up_to_date, "Up-to-date libraries", 
                                     show_status=True, command_context="install")
        
        # Show installed/updated libraries
        if processed:
            if up_to_date:
                click.echo()  # Add blank line between sections
            _format_libraries_summary(processed, "Processed libraries", 
                                     show_status=True, command_context="install")
        
        # Show summary message if nothing was processed
        if not all_libraries:
            click.echo("No libraries to install")
            
        logger.info("Install command completed successfully")
            
    except InstallationError as e:
        _handle_installation_error(e)


@main.command()
@click.argument('libraries', nargs=-1)
@click.option('--force', is_flag=True, default=False,
              help='Force reinstall all libraries (ignore up-to-date check)')
def update(libraries: tuple, force: bool):
    """Update libraries by checking remote repositories for newer versions.
    
    This command specifically checks remote repositories for updates and installs
    any libraries that have newer versions available. Use this when you want to
    ensure you have the latest versions of your dependencies.
    
    LIBRARIES: Optional list of specific libraries to update.
               If not provided, checks all libraries from configuration.
    """
    try:
        logger.info("Starting update command")
        installer = _get_installer()
        logger.debug("Created installer instance")
        
        # Convert tuple to list for installer
        library_list = list(libraries) if libraries else None
        logger.debug(f"Library list: {library_list}")
        
        if library_list:
            click.echo(f"Checking for updates: {', '.join(library_list)}")
        else:
            click.echo("Checking all libraries for updates from remote repositories")
        
        logger.debug("About to call installer.install_all() with remote update check")
        all_libraries = installer.install_all(library_list, force=force, check_remote_updates=True)
        logger.debug("install_all() completed")
        
        logger.debug(f"Got {len(all_libraries)} libraries from install_all")
        
        # Filter libraries by install_status
        up_to_date = {name: entry for name, entry in all_libraries.items() 
                     if entry.install_status == "up_to_date"}
        processed = {name: entry for name, entry in all_libraries.items() 
                    if entry.install_status in ["installed", "updated"]}
        
        logger.debug(f"{len(up_to_date)} up-to-date, {len(processed)} processed")
        
        # Show results
        if processed:
            _format_libraries_summary(processed, "Updated libraries", 
                                     show_status=True, command_context="install")
            if up_to_date:
                click.echo()  # Add blank line between sections
        
        if up_to_date:
            _format_libraries_summary(up_to_date, "Up-to-date libraries", 
                                     show_status=True, command_context="install")
        
        # Show summary message if nothing was processed
        if not all_libraries:
            click.echo("No libraries to update")
        elif not processed:
            click.echo("All libraries are up-to-date")
            
        logger.info("Update command completed successfully")
            
    except InstallationError as e:
        _handle_installation_error(e)


@main.command('list')
def list_libraries():
    """List installed libraries."""
    try:
        installer = _get_installer()
        installed = installer.list_installed_libraries()
        
        _format_libraries_summary(installed, "Installed libraries", "No libraries installed", 
                                 show_status=False)
                
    except InstallationError as e:
        _handle_installation_error(e)


@main.command()
def validate():
    """Validate ams-compose.yaml configuration and installation state."""
    try:
        installer = _get_installer()
        
        # Validate configuration
        try:
            config = installer.load_config()
            click.echo(f"Configuration valid: {len(config.imports)} libraries defined")
        except Exception as e:
            click.echo(f"Configuration error: {e}")
            sys.exit(1)
        
        # Validate installation state
        validation_results = installer.validate_installation()
        
        # Separate libraries by validation status
        valid_libraries = {}
        invalid_libraries = {}
        
        for library_name, lock_entry in validation_results.items():
            if lock_entry.validation_status == "valid":
                valid_libraries[library_name] = lock_entry
            else:
                invalid_libraries[library_name] = lock_entry
        
        # Show validation results using unified formatting
        if invalid_libraries:
            _format_libraries_summary(invalid_libraries, "Invalid libraries", 
                                     show_status=True, command_context="validate")
            click.echo()
            if valid_libraries:
                _format_libraries_summary(valid_libraries, "Valid libraries", 
                                         show_status=True, command_context="validate")
            sys.exit(1)
        else:
            _format_libraries_summary(valid_libraries, "Valid libraries", "All libraries are valid", 
                                     show_status=True, command_context="validate")
            
    except InstallationError as e:
        _handle_installation_error(e)


@main.command()
@click.option('--library_root', default='designs/libs', 
              help='Default directory for library installations (default: designs/libs)')
@click.option('--force', is_flag=True, 
              help='Overwrite existing ams-compose.yaml file')
def init(library_root: str, force: bool):
    """Initialize a new ams-compose project.
    
    Creates an ams-compose.yaml configuration file and sets up the project
    directory structure for analog IC design dependency management.
    """
    config_path = Path.cwd() / "ams-compose.yaml"
    
    # Check if config already exists
    if config_path.exists() and not force:
        click.echo(f"Error: {config_path.name} already exists. Use --force to overwrite.", err=True)
        sys.exit(1)
    
    # Create scaffold directory structure
    libs_path = Path.cwd() / library_root
    if not libs_path.exists():
        libs_path.mkdir(parents=True, exist_ok=True)
        click.echo(f"Created directory: {library_root}/")
    
    # Load template configuration from file
    try:
        template_path = Path(__file__).parent.parent / "config_template.yaml"
        template_config = template_path.read_text().format(library_root=library_root)
    except FileNotFoundError:
        click.echo("Error: Template configuration file not found.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error reading template configuration: {e}", err=True)
        sys.exit(1)
    
    # Write configuration file
    config_path.write_text(template_config)
    
    click.echo(f"Initialized ams-compose project in {Path.cwd()}")
    click.echo(f"Edit {config_path.name} to add library dependencies, then run 'ams-compose install'")


@main.command()
def clean():
    """Clean unused mirrors and orphaned libraries."""
    try:
        installer = _get_installer()
        
        # Clean unused mirrors
        removed_mirrors = installer.clean_unused_mirrors()
        if removed_mirrors:
            click.echo(f"Removed {len(removed_mirrors)} unused mirrors")
        else:
            click.echo("No unused mirrors found")
        
        # Clean orphaned libraries from lockfile
        removed_libraries = installer.clean_orphaned_libraries()
        if removed_libraries:
            click.echo(f"Removed {len(removed_libraries)} orphaned libraries from lockfile:")
            for lib in removed_libraries:
                click.echo(f"  {lib}")
        else:
            click.echo("No orphaned libraries found")
        
        # Run validation after cleanup
        validation_results = installer.validate_installation()
        
        # Separate libraries by validation status
        valid_libraries = []
        remaining_issues = []
        
        for library_name, lock_entry in validation_results.items():
            if lock_entry.validation_status == "valid":
                valid_libraries.append(library_name)
            elif lock_entry.validation_status != "orphaned":  # Skip orphaned since we just cleaned them
                remaining_issues.append(f"{library_name}: {lock_entry.validation_status}")
        
        if remaining_issues:
            click.echo(f"Found {len(remaining_issues)} remaining issues:")
            for issue in remaining_issues:
                click.echo(f"  {issue}")
        else:
            click.echo(f"All {len(valid_libraries)} libraries are valid")
            
    except InstallationError as e:
        _handle_installation_error(e)


@main.command()
def schema():
    """Show the complete ams-compose.yaml configuration schema."""
    try:
        # Load schema documentation from file
        schema_path = Path(__file__).parent.parent / "schema.txt"
        schema_content = schema_path.read_text()
        click.echo(schema_content)
    except FileNotFoundError:
        click.echo("Error: Schema documentation file not found.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error reading schema documentation: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()