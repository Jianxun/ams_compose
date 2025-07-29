"""Tests for the init CLI command."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from ams_compose.cli.main import main


class TestInitCommand:
    """Test cases for the ams-compose init command."""
    
    def test_init_creates_config_and_directory(self, tmp_path):
        """Test that init creates config file and library directory."""
        # Change to temporary directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            runner = CliRunner()
            result = runner.invoke(main, ['init'])
            
            # Check command succeeded
            assert result.exit_code == 0
            
            # Check config file was created
            config_file = tmp_path / "ams-compose.yaml"
            assert config_file.exists()
            
            # Check default library directory was created
            libs_dir = tmp_path / "designs/libs"
            assert libs_dir.exists()
            assert libs_dir.is_dir()
            
            # Check .gitignore was created/updated
            gitignore = tmp_path / ".gitignore"
            assert gitignore.exists()
            assert ".mirror/" in gitignore.read_text()
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_with_custom_library_root(self, tmp_path):
        """Test init with custom library-root directory."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            runner = CliRunner()
            result = runner.invoke(main, ['init', '--library-root', 'custom/libs'])
            
            assert result.exit_code == 0
            
            # Check custom directory was created
            custom_dir = tmp_path / "custom/libs"
            assert custom_dir.exists()
            assert custom_dir.is_dir()
            
            # Check config contains custom library-root
            config_file = tmp_path / "ams-compose.yaml"
            config_content = config_file.read_text()
            assert "library-root: custom/libs" in config_content
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_config_file_content(self, tmp_path):
        """Test that init creates proper config file content."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            runner = CliRunner()
            result = runner.invoke(main, ['init'])
            
            assert result.exit_code == 0
            
            config_file = tmp_path / "ams-compose.yaml"
            content = config_file.read_text()
            
            # Check required sections are present
            assert "library-root: designs/libs" in content
            assert "imports:" in content
            assert "# Example library import" in content
            assert "# my_analog_lib:" in content
            assert "#   repo: https://github.com/example/analog-library.git" in content
            assert "#   ref: main" in content
            assert "#   source_path: lib/analog" in content
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_fails_if_config_exists(self, tmp_path):
        """Test that init fails if ams-compose.yaml already exists."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create existing config file
            config_file = tmp_path / "ams-compose.yaml"
            config_file.write_text("existing config")
            
            runner = CliRunner()
            result = runner.invoke(main, ['init'])
            
            # Should fail
            assert result.exit_code == 1
            assert "already exists" in result.output
            assert "Use --force to overwrite" in result.output
            
            # Config should be unchanged
            assert config_file.read_text() == "existing config"
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_force_overwrites_existing_config(self, tmp_path):
        """Test that init --force overwrites existing config."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create existing config file
            config_file = tmp_path / "ams-compose.yaml"
            config_file.write_text("existing config")
            
            runner = CliRunner()
            result = runner.invoke(main, ['init', '--force'])
            
            # Should succeed
            assert result.exit_code == 0
            assert "Initialized ams-compose project" in result.output
            
            # Config should be overwritten
            content = config_file.read_text()
            assert "existing config" not in content
            assert "library-root: designs/libs" in content
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_creates_nested_directory_structure(self, tmp_path):
        """Test that init creates nested directories properly."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            runner = CliRunner()
            result = runner.invoke(main, ['init', '--library-root', 'deep/nested/libs'])
            
            assert result.exit_code == 0
            
            # Check nested directory was created
            nested_dir = tmp_path / "deep/nested/libs"
            assert nested_dir.exists()
            assert nested_dir.is_dir()
            
            # Check all parent directories exist
            assert (tmp_path / "deep").exists()
            assert (tmp_path / "deep/nested").exists()
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_output_messages(self, tmp_path):
        """Test that init provides helpful output messages."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            runner = CliRunner()
            result = runner.invoke(main, ['init'])
            
            assert result.exit_code == 0
            
            output = result.output
            assert "Initialized ams-compose project" in output
            assert "Created directory: designs/libs/" in output
            assert "Added '.mirror/' to .gitignore" in output
            assert "Edit ams-compose.yaml to add library dependencies" in output
            assert "run 'ams-compose install'" in output
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_updates_existing_gitignore(self, tmp_path):
        """Test that init updates existing .gitignore file."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create existing .gitignore
            gitignore = tmp_path / ".gitignore"
            gitignore.write_text("*.pyc\n__pycache__/\n")
            
            runner = CliRunner()
            result = runner.invoke(main, ['init'])
            
            assert result.exit_code == 0
            
            # Check .gitignore was updated
            content = gitignore.read_text()
            assert "*.pyc" in content  # Original content preserved
            assert "__pycache__/" in content
            assert ".mirror/" in content  # New content added
            assert "# ams-compose mirrors" in content
            
        finally:
            os.chdir(original_cwd)
    
    def test_init_skips_gitignore_if_already_present(self, tmp_path):
        """Test that init doesn't duplicate .gitignore entries."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .gitignore with mirror entry already present
            gitignore = tmp_path / ".gitignore"
            gitignore.write_text("*.pyc\n.mirror/\n")
            
            runner = CliRunner()
            result = runner.invoke(main, ['init'])
            
            assert result.exit_code == 0
            
            # Check .gitignore wasn't duplicated
            content = gitignore.read_text()
            assert content.count(".mirror/") == 1
            
        finally:
            os.chdir(original_cwd)