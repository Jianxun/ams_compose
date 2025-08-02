"""Tests for the validate CLI command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, Mock

from ams_compose.cli.main import main
from ams_compose.core.config import LockEntry


class TestValidateCommand:
    """Test cases for the ams-compose validate command."""
    
    @patch('ams_compose.cli.main._get_installer')
    def test_validate_command_with_new_return_type(self, mock_get_installer):
        """Test validate command processes Dict[str, LockEntry] return type correctly."""
        # Create mock installer
        mock_installer = Mock()
        mock_get_installer.return_value = mock_installer
        
        # Mock config validation success
        mock_config = Mock()
        mock_config.imports = {"lib1": Mock(), "lib2": Mock()}
        mock_installer.load_config.return_value = mock_config
        
        # Mock validate_installation to return Dict[str, LockEntry] with validation status
        validation_results = {
            "lib1": LockEntry(
                repo="https://github.com/example/repo1",
                ref="main",
                commit="abc123",
                source_path="lib",
                local_path="designs/libs/lib1",
                checksum="checksum1",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                validation_status="valid"
            ),
            "lib2": LockEntry(
                repo="https://github.com/example/repo2",
                ref="v1.0", 
                commit="def456",
                source_path="src",
                local_path="designs/libs/lib2",
                checksum="checksum2",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                validation_status="modified"
            )
        }
        mock_installer.validate_installation.return_value = validation_results
        
        runner = CliRunner()
        result = runner.invoke(main, ['validate'])
        
        # This test verifies the CLI correctly handles the new return format
        # After fixing the CLI, this should pass
        assert result.exit_code == 1  # Should exit with error due to invalid library
        
        # Verify the output contains proper validation information
        output = result.output
        assert "Configuration valid: 2 libraries defined" in output
        assert "Invalid libraries" in output
        # Should show lib2 as modified, not individual characters
        assert "lib2" in output or "modified" in output
    
    @patch('ams_compose.cli.main._get_installer')
    def test_validate_command_config_error(self, mock_get_installer):
        """Test validate command handles config errors properly."""
        mock_installer = Mock()
        mock_get_installer.return_value = mock_installer
        
        # Mock config loading to raise exception
        mock_installer.load_config.side_effect = Exception("Invalid YAML syntax")
        
        runner = CliRunner()
        result = runner.invoke(main, ['validate'])
        
        assert result.exit_code == 1
        assert "Configuration error: Invalid YAML syntax" in result.output
    
    @patch('ams_compose.cli.main._get_installer')
    def test_validate_command_uses_unified_formatting(self, mock_get_installer):
        """Test that validate command uses the same formatting style as install command."""
        # Create mock installer
        mock_installer = Mock()
        mock_get_installer.return_value = mock_installer
        
        # Mock config validation success
        mock_config = Mock()
        mock_config.imports = {"test_lib": Mock()}
        mock_installer.load_config.return_value = mock_config
        
        # Mock validate_installation to return valid library with rich data
        validation_results = {
            "test_lib": LockEntry(
                repo="https://github.com/example/test-lib",
                ref="main",
                commit="abc123def",
                source_path="lib",
                local_path="designs/libs/test_lib",
                checksum="checksum1",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                validation_status="valid",
                license="MIT"
            )
        }
        mock_installer.validate_installation.return_value = validation_results
        
        runner = CliRunner()
        result = runner.invoke(main, ['validate'])
        
        # Should succeed with valid library
        assert result.exit_code == 0
        
        # Verify output uses same tabular format as install command:
        # "test_lib | commit:abc123de | ref:main | license:MIT | status:valid"
        output = result.output
        assert "test_lib" in output
        assert "commit:abc123de" in output  # 8-character commit hash
        assert "license:MIT" in output
        assert "status:valid" in output