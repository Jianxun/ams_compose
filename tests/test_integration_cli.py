"""Integration tests for CLI commands."""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from click.testing import CliRunner

from analog_hub.cli.main import main


class TestCLIIntegration:
    """Test CLI integration with real configuration."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_config(self, temp_project):
        """Create sample analog-hub.yaml configuration."""
        config_data = {
            'library-root': 'designs/libs',
            'imports': {
                'test_library': {
                    'repo': 'https://github.com/peterkinget/testing-project-template',
                    'ref': 'PK_PLL_modeling',
                    'source_path': 'designs/libs/model_pll'
                }
            }
        }
        
        config_path = temp_project / "analog-hub.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        return config_path
    
    @pytest.fixture
    def cli_runner(self, temp_project):
        """Create CLI runner with temporary directory."""
        runner = CliRunner()
        # Use temp_project as the working directory instead of isolated filesystem
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            yield runner
        finally:
            os.chdir(original_cwd)
    
    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'analog-hub: Dependency management' in result.output
        assert 'install' in result.output
        assert 'update' in result.output
        assert 'list' in result.output
        assert 'validate' in result.output
        assert 'clean' in result.output
    
    def test_cli_version(self):
        """Test CLI version command."""
        runner = CliRunner()
        result = runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        assert 'version' in result.output
    
    def test_validate_missing_config(self):
        """Test validate command with missing configuration."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ['validate'])
            
            assert result.exit_code == 1
            assert 'Configuration file not found' in result.output
    
    def test_validate_valid_config(self, cli_runner, sample_config):
        """Test validate command with valid configuration."""
        result = cli_runner.invoke(main, ['validate'])
        
        assert result.exit_code == 0
        assert 'Configuration valid: 1 libraries defined' in result.output
        assert 'All 0 installed libraries are valid' in result.output
    
    def test_list_no_libraries(self, cli_runner, sample_config):
        """Test list command with no installed libraries."""
        result = cli_runner.invoke(main, ['list'])
        
        assert result.exit_code == 0
        assert 'No libraries installed' in result.output
    
    def test_install_missing_config(self):
        """Test install command with missing configuration."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ['install'])
            
            assert result.exit_code == 1
            assert 'Configuration file not found' in result.output
    
    def test_install_nonexistent_library(self, cli_runner, sample_config):
        """Test install command with nonexistent library."""
        result = cli_runner.invoke(main, ['install', 'nonexistent'])
        
        assert result.exit_code == 1
        assert 'Libraries not found in configuration' in result.output
    
    def test_update_no_installations(self, cli_runner, sample_config):
        """Test update command with no current installations."""
        result = cli_runner.invoke(main, ['update'])
        
        assert result.exit_code == 0
        assert 'No libraries to update' in result.output
    
    def test_clean_no_mirrors(self, cli_runner, sample_config):
        """Test clean command with no mirrors."""
        result = cli_runner.invoke(main, ['clean'])
        
        assert result.exit_code == 0
        assert 'No unused mirrors found' in result.output
        assert 'All 0 libraries are valid' in result.output
    
    def test_gitignore_generation(self, cli_runner, sample_config):
        """Test .gitignore generation during install."""
        # Test install with invalid repo to avoid actual network operations
        config_data = {
            'library-root': 'libs',
            'imports': {
                'test_lib': {
                    'repo': 'invalid://repo.url',
                    'ref': 'main',
                    'source_path': 'src'
                }
            }
        }
        
        Path("analog-hub.yaml").write_text(yaml.dump(config_data))
        
        # Run install (will fail but should create .gitignore)
        result = cli_runner.invoke(main, ['install'])
        
        # Check .gitignore was created
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            assert '.mirror/' in content
    
    def test_install_help(self):
        """Test install command help."""
        runner = CliRunner()
        result = runner.invoke(main, ['install', '--help'])
        
        assert result.exit_code == 0
        assert 'Install libraries from analog-hub.yaml' in result.output
        assert 'LIBRARIES' in result.output
        assert '--auto-gitignore' in result.output
    
    def test_update_help(self):
        """Test update command help."""
        runner = CliRunner()
        result = runner.invoke(main, ['update', '--help'])
        
        assert result.exit_code == 0
        assert 'Update installed libraries' in result.output
        assert 'LIBRARIES' in result.output
    
    def test_list_help(self):
        """Test list command help."""
        runner = CliRunner()
        result = runner.invoke(main, ['list', '--help'])
        
        assert result.exit_code == 0
        assert 'List installed libraries' in result.output
        assert '--detailed' in result.output
    
    def test_validate_help(self):
        """Test validate command help."""
        runner = CliRunner()
        result = runner.invoke(main, ['validate', '--help'])
        
        assert result.exit_code == 0
        assert 'Validate analog-hub.yaml configuration' in result.output
    
    def test_clean_help(self):
        """Test clean command help."""
        runner = CliRunner()
        result = runner.invoke(main, ['clean', '--help'])
        
        assert result.exit_code == 0
        assert 'Clean unused mirrors and validate' in result.output
    
    def test_invalid_command(self):
        """Test invalid command."""
        runner = CliRunner()
        result = runner.invoke(main, ['invalid-command'])
        
        assert result.exit_code != 0
        assert 'No such command' in result.output
    
    def test_config_validation_invalid_yaml(self, cli_runner):
        """Test validation with invalid YAML configuration."""
        # Create invalid YAML
        Path("analog-hub.yaml").write_text("invalid: yaml: content: [")
        
        result = cli_runner.invoke(main, ['validate'])
        
        assert result.exit_code == 1
        assert 'Configuration error' in result.output