"""Main CLI entry point for analog-hub."""

import sys
from pathlib import Path
from typing import Optional, List

import click
from analog_hub import __version__
from analog_hub.core.installer import LibraryInstaller, InstallationError
from analog_hub.core.config import AnalogHubConfig


def _get_installer() -> LibraryInstaller:
    """Get LibraryInstaller instance for current directory."""
    return LibraryInstaller(project_root=Path.cwd())


def _handle_installation_error(e: InstallationError) -> None:
    """Handle installation errors with user-friendly messages."""
    click.echo(f"Error: {e}", err=True)
    sys.exit(1)


def _auto_generate_gitignore() -> None:
    """Auto-generate .gitignore entries for .mirror/ directory."""
    gitignore_path = Path.cwd() / ".gitignore"
    mirror_entry = ".mirror/"
    
    # Check if .gitignore exists and already contains mirror entry
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if mirror_entry in content:
            return
        
        # Add mirror entry
        if not content.endswith('\n'):
            content += '\n'
        content += f"\n# analog-hub mirrors\n{mirror_entry}\n"
    else:
        # Create new .gitignore
        content = f"# analog-hub mirrors\n{mirror_entry}\n"
    
    gitignore_path.write_text(content)
    click.echo(f"Added '{mirror_entry}' to .gitignore")


@click.group()
@click.version_option(version=__version__)
def main():
    """analog-hub: Dependency management for analog IC design repositories."""
    pass


@main.command()
@click.argument('libraries', nargs=-1)
@click.option('--auto-gitignore', is_flag=True, default=True, 
              help='Automatically add .mirror/ to .gitignore (default: enabled)')
@click.option('--force', is_flag=True, default=False,
              help='Force reinstall all libraries (ignore up-to-date check)')
def install(libraries: tuple, auto_gitignore: bool, force: bool):
    """Install libraries from analog-hub.yaml.
    
    LIBRARIES: Optional list of specific libraries to install.
               If not provided, installs all libraries from configuration.
    """
    try:
        installer = _get_installer()
        
        # Auto-generate .gitignore if requested
        if auto_gitignore:
            _auto_generate_gitignore()
        
        # Convert tuple to list for installer
        library_list = list(libraries) if libraries else None
        
        if library_list:
            click.echo(f"Installing libraries: {', '.join(library_list)}")
        else:
            click.echo("Installing all libraries from analog-hub.yaml")
        
        installed = installer.install_all(library_list, force=force)
        
        if installed:
            click.echo(f"Installed {len(installed)} libraries")
        else:
            click.echo("No libraries to install")
            
    except InstallationError as e:
        _handle_installation_error(e)




@main.command('list')
@click.option('--detailed', is_flag=True, help='Show detailed library information')
def list_libraries(detailed: bool):
    """List installed libraries."""
    try:
        installer = _get_installer()
        installed = installer.list_installed_libraries()
        
        if not installed:
            click.echo("No libraries installed")
            return
        
        click.echo(f"Installed libraries ({len(installed)}):")
        
        for library_name, lock_entry in installed.items():
            if detailed:
                click.echo(f"{library_name}")
                click.echo(f"  Repository: {lock_entry.repo}")
                click.echo(f"  Reference:  {lock_entry.ref}")
                click.echo(f"  Commit:     {lock_entry.commit}")
                click.echo(f"  Path:       {lock_entry.local_path}")
                click.echo(f"  Installed:  {lock_entry.installed_at}")
                click.echo()
            else:
                click.echo(f"  {library_name:<20} {lock_entry.commit[:8]} ({lock_entry.ref})")
                
    except InstallationError as e:
        _handle_installation_error(e)


@main.command()
def validate():
    """Validate analog-hub.yaml configuration and installation state."""
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
        valid_libraries, invalid_libraries = installer.validate_installation()
        
        if invalid_libraries:
            click.echo(f"Invalid libraries ({len(invalid_libraries)}):")
            for issue in invalid_libraries:
                click.echo(f"  {issue}")
            sys.exit(1)
        else:
            click.echo(f"All {len(valid_libraries)} libraries are valid")
            
    except InstallationError as e:
        _handle_installation_error(e)


@main.command()
@click.option('--library-root', default='designs/libs', 
              help='Default directory for library installations (default: libs)')
@click.option('--force', is_flag=True, 
              help='Overwrite existing analog-hub.yaml file')
def init(library_root: str, force: bool):
    """Initialize a new analog-hub project.
    
    Creates an analog-hub.yaml configuration file and sets up the project
    directory structure for analog IC design dependency management.
    """
    config_path = Path.cwd() / "analog-hub.yaml"
    
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
    template_config = f"""# analog-hub configuration file
# For more information, see: https://github.com/Jianxun/analog-hub

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
# 5. Run 'analog-hub install' to fetch the library
#
# Example commands:
#   analog-hub install           # Install missing libraries, update outdated ones
#   analog-hub install my_lib    # Install/update specific library  
#   analog-hub install --force   # Force reinstall all libraries
#   analog-hub list             # List installed libraries
#   analog-hub validate         # Validate configuration
"""
    
    # Write configuration file
    config_path.write_text(template_config)
    
    # Auto-generate .gitignore
    _auto_generate_gitignore()
    
    click.echo(f"Initialized analog-hub project in {Path.cwd()}")
    click.echo(f"Edit {config_path.name} to add library dependencies, then run 'analog-hub install'")


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
        valid_libraries, invalid_libraries = installer.validate_installation()
        
        if invalid_libraries:
            # Filter out warnings (since we just cleaned orphaned libraries)
            actual_issues = [issue for issue in invalid_libraries if not issue.startswith('WARNING')]
            if actual_issues:
                click.echo(f"Found {len(actual_issues)} remaining issues:")
                for issue in actual_issues:
                    click.echo(f"  {issue}")
            else:
                click.echo(f"All {len(valid_libraries)} libraries are valid")
        else:
            click.echo(f"All {len(valid_libraries)} libraries are valid")
            
    except InstallationError as e:
        _handle_installation_error(e)


if __name__ == "__main__":
    main()