"""Tests for the install CLI command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import Mock, patch

from ams_compose.cli.main import main
from ams_compose.core.config import LockEntry


class TestInstallCommand:
    """Test cases for the ams-compose install command."""
    
    @patch('ams_compose.cli.main._get_installer')
    def test_install_command_uses_structured_data_output(self, mock_get_installer, tmp_path):
        """Test that install command uses structured data from installer for output (TDD Cycle 5 RED)."""
        # Setup mock installer
        mock_installer = Mock()
        mock_get_installer.return_value = mock_installer
        
        # Mock install_all to return dictionary of all processed libraries
        mock_installer.install_all.return_value = {
            "library1": LockEntry(
                repo="https://github.com/example/lib1",
                ref="main",
                commit="abc123def",
                source_path="lib",
                local_path="designs/libs/library1",
                checksum="checksum1",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                install_status="installed",
                license="MIT",
                license_warning="Test license warning"
            ),
            "library2": LockEntry(
                repo="https://github.com/example/lib2",
                ref="v1.0.0",
                commit="def456ghi",
                source_path="src",
                local_path="designs/libs/library2",
                checksum="checksum2",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T12:00:00",
                install_status="updated",
                license="GPL-3.0",
                license_change="license changed: MIT → GPL-3.0"
            )
        }
        
        # Change to temporary directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            runner = CliRunner()
            result = runner.invoke(main, ['install'])
            
            # Check command succeeded
            assert result.exit_code == 0
            
            # Verify that the output contains structured information from the LockEntry
            output = result.output
            
            # Should show library names and their status
            assert "library1" in output
            assert "library2" in output
            
            # Should show install status
            assert "installed" in output or "[installed]" in output
            assert "updated" in output or "[updated]" in output
            
            # Should show commit information
            assert "abc123de" in output  # Short commit hash
            assert "def456gh" in output
            
            # Should show license information
            assert "MIT" in output
            assert "GPL-3.0" in output
            
            # Should show warnings
            assert "WARNING" in output or "warning" in output
            
            # Should show license change information
            assert "license changed" in output or "changed" in output
            
        finally:
            os.chdir(original_cwd)
    
    @patch('ams_compose.cli.main._get_installer')
    def test_install_command_handles_no_libraries(self, mock_get_installer, tmp_path):
        """Test install command when no libraries need installation."""
        # Setup mock installer
        mock_installer = Mock()
        mock_get_installer.return_value = mock_installer
        
        # Mock install_all to return empty dictionary
        mock_installer.install_all.return_value = {}
        
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            runner = CliRunner()
            result = runner.invoke(main, ['install'])
            
            assert result.exit_code == 0
            assert "No libraries to install" in result.output
            
        finally:
            os.chdir(original_cwd)
    
    @patch('ams_compose.cli.main._get_installer')
    def test_install_command_specific_libraries(self, mock_get_installer, tmp_path):
        """Test install command with specific library names."""
        # Setup mock installer
        mock_installer = Mock()
        mock_get_installer.return_value = mock_installer
        
        # Mock install_all to return dictionary with one library
        mock_installer.install_all.return_value = {
            "specific_lib": LockEntry(
                repo="https://github.com/example/specific",
                ref="main",
                commit="xyz789abc",
                source_path="lib",
                local_path="designs/libs/specific_lib",
                checksum="checksum3",
                installed_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                install_status="installed",
                license="BSD-3-Clause"
            )
        }
        
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            runner = CliRunner()
            result = runner.invoke(main, ['install', 'specific_lib'])
            
            assert result.exit_code == 0
            
            # Should show it's installing specific libraries
            assert "Installing libraries: specific_lib" in result.output
            
            # Verify install_all was called with the specific library
            mock_installer.install_all.assert_called_once_with(['specific_lib'], force=False, check_remote_updates=False)
            
        finally:
            os.chdir(original_cwd)