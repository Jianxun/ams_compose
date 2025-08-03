"""Main CLI entry point for ams-compose."""

import sys
from pathlib import Path
from typing import Optional, List, Dict

import click
from ams_compose import __version__
from ams_compose.core.installer import LibraryInstaller, InstallationError
from ams_compose.core.config import ComposeConfig, LockEntry


def _get_installer() -> LibraryInstaller:
    """Get LibraryInstaller instance for current directory."""
    return LibraryInstaller(project_root=Path.cwd())


def _handle_installation_error(e: InstallationError) -> None:
    """Handle installation errors with user-friendly messages."""
    click.echo(f"Error: {e}", err=True)
    sys.exit(1)


def _format_libraries_tabular(libraries: Dict[str, LockEntry], show_status: bool = False, 
                             command_context: str = "list") -> None:
    """Format libraries in clean tabular format with proper column alignment.
    
    Args:
        libraries: Dictionary of library name to LockEntry
        show_status: Whether to include status column
        command_context: Command context for status priority ("list", "validate", "install")
    """
    if not libraries:
        return
        
    # Calculate column widths for alignment
    max_name_width = max(len(name) for name in libraries.keys())
    max_ref_width = max(len(entry.ref) for entry in libraries.values())
    max_license_width = max(len(entry.license or "None") for entry in libraries.values())
    
    if show_status:
        # Calculate status width based on command context
        status_values = []
        for entry in libraries.values():
            if command_context == "validate":
                status = entry.validation_status or "unknown"
            elif command_context == "install":
                status = entry.install_status or entry.validation_status or "unknown"
            else:  # list or default
                status = entry.install_status or entry.validation_status or "unknown"
            status_values.append(status)
        max_status_width = max(len(status) for status in status_values)
    
    for library_name, lock_entry in libraries.items():
        commit_hash = lock_entry.commit[:8]
        license_display = lock_entry.license or "None"
        
        if show_status:
            # Select status based on command context
            if command_context == "validate":
                status = lock_entry.validation_status or "unknown"
            elif command_context == "install":
                status = lock_entry.install_status or lock_entry.validation_status or "unknown"
            else:  # list or default
                status = lock_entry.install_status or lock_entry.validation_status or "unknown"
            click.echo(f"{library_name:<{max_name_width}} | commit:{commit_hash} | ref:{lock_entry.ref:<{max_ref_width}} | license:{license_display:<{max_license_width}} | status:{status}")
        else:
            click.echo(f"{library_name:<{max_name_width}} | commit:{commit_hash} | ref:{lock_entry.ref:<{max_ref_width}} | license:{license_display}")
        
        # Show additional info for status commands (install/validate)
        if show_status:
            # Show license change if it occurred
            if lock_entry.license_change:
                click.echo(f"  ↳ {lock_entry.license_change}")
            
            # Show license compatibility warning
            if lock_entry.license_warning:
                click.echo(f"  ⚠️  WARNING: {lock_entry.license_warning}")
            elif lock_entry.license:
                from ams_compose.utils.license import LicenseDetector
                license_detector = LicenseDetector()
                warning = license_detector.get_license_compatibility_warning(lock_entry.license)
                if warning:
                    click.echo(f"  ⚠️  WARNING: {warning}")


def _format_libraries_detailed(libraries: Dict[str, LockEntry], show_status: bool = False) -> None:
    """Format libraries in detailed multi-line format.
    
    Args:
        libraries: Dictionary of library name to LockEntry
        show_status: Whether to show status information
    """
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
                
            # Show license change if it occurred
            if lock_entry.license_change:
                click.echo(f"  Changes:    {lock_entry.license_change}")
        
        # Show license compatibility warning
        if lock_entry.license_warning:
            click.echo(f"  ⚠️  WARNING: {lock_entry.license_warning}")
        elif lock_entry.license:
            from ams_compose.utils.license import LicenseDetector
            license_detector = LicenseDetector()
            warning = license_detector.get_license_compatibility_warning(lock_entry.license)
            if warning:
                click.echo(f"  ⚠️  WARNING: {warning}")
        
        click.echo()


def _format_libraries_summary(libraries: Dict[str, LockEntry], title: str, empty_message: str = None, 
                             detailed: bool = False, show_status: bool = False, 
                             command_context: str = "list") -> None:
    """Unified formatter for library summaries across all commands.
    
    Args:
        libraries: Dictionary of library name to LockEntry
        title: Title to display
        empty_message: Custom message when no libraries found
        detailed: Whether to use detailed multi-line format
        show_status: Whether to show status information
        command_context: Command context for status priority ("list", "validate", "install")
    """
    if not libraries:
        message = empty_message or f"No {title.lower()}"
        click.echo(message)
        return
        
    click.echo(f"{title} ({len(libraries)}):")
    
    if detailed:
        _format_libraries_detailed(libraries, show_status)
    else:
        _format_libraries_tabular(libraries, show_status, command_context)




@click.group()
@click.version_option(version=__version__)
def main():
    """ams-compose: Dependency management for analog/mixed-signal IC design repositories."""
    pass


@main.command()
@click.argument('libraries', nargs=-1)
@click.option('--force', is_flag=True, default=False,
              help='Force reinstall all libraries (ignore up-to-date check)')
def install(libraries: tuple, force: bool):
    """Install libraries from ams-compose.yaml.
    
    LIBRARIES: Optional list of specific libraries to install.
               If not provided, installs all libraries from configuration.
    """
    try:
        installer = _get_installer()
        
        # Convert tuple to list for installer
        library_list = list(libraries) if libraries else None
        
        if library_list:
            click.echo(f"Installing libraries: {', '.join(library_list)}")
        else:
            click.echo("Installing all libraries from ams-compose.yaml")
        
        installed, up_to_date = installer.install_all(library_list, force=force)
        
        # Show up-to-date libraries first
        if up_to_date:
            _format_libraries_summary(up_to_date, "Up-to-date libraries", 
                                     detailed=False, show_status=True, command_context="install")
        
        # Show installed/updated libraries
        if installed:
            if up_to_date:
                click.echo()  # Add blank line between sections
            _format_libraries_summary(installed, "Processed libraries", 
                                     detailed=False, show_status=True, command_context="install")
        
        # Show summary message if nothing was processed
        if not installed and not up_to_date:
            click.echo("No libraries to install")
            
    except InstallationError as e:
        _handle_installation_error(e)




@main.command('list')
def list_libraries():
    """List installed libraries."""
    try:
        installer = _get_installer()
        installed = installer.list_installed_libraries()
        
        _format_libraries_summary(installed, "Installed libraries", "No libraries installed", 
                                 detailed=False, show_status=False)
                
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
                                     detailed=False, show_status=True, command_context="validate")
            click.echo()
            if valid_libraries:
                _format_libraries_summary(valid_libraries, "Valid libraries", 
                                         detailed=False, show_status=True, command_context="validate")
            sys.exit(1)
        else:
            _format_libraries_summary(valid_libraries, "Valid libraries", "All libraries are valid", 
                                     detailed=False, show_status=True, command_context="validate")
            
    except InstallationError as e:
        _handle_installation_error(e)


@main.command()
@click.option('--library-root', default='designs/libs', 
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
    
    # Generate template configuration
    template_config = f"""# ams-compose configuration file
# For more information, see: https://github.com/Jianxun/ams-compose

# Default directory where libraries will be installed
library-root: {library_root}

# Library imports - add your dependencies here
imports:
  # Example library import (remove or modify as needed):
  # my_analog_lib:
  #   repo: https://github.com/example/analog-library.git
  #   ref: main                    # branch, tag, or commit
  #   source_path: lib/analog      # path within the repository
  #   # local_path: custom/path    # optional: override library-root location
  
# To add a new library:
# 1. Add an entry under 'imports' with a unique name
# 2. Specify the git repository URL
# 3. Set the reference (branch/tag/commit)  
# 4. Define the source path within the repository
# 5. Run 'ams-compose install' to fetch the library
#
# Example commands:
#   ams-compose install           # Install missing libraries, update outdated ones
#   ams-compose install my_lib    # Install/update specific library  
#   ams-compose install --force   # Force reinstall all libraries
#   ams-compose list             # List installed libraries
#   ams-compose validate         # Validate configuration
"""
    
    # Write configuration file
    config_path.write_text(template_config)
    
    click.echo(f"Initialized ams-compose project in {Path.cwd()}")
    click.echo(f"Edit {config_path.name} to add library dependencies, then run 'ams-compose install'")


@main.command()
def clean():
    """Clean unused mirrors, orphaned libraries, and validate installations."""
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


if __name__ == "__main__":
    main()