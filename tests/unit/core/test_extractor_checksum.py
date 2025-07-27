"""Unit tests for PathExtractor checksum operations."""

import tempfile
import shutil
from pathlib import Path

from analog_hub.utils.checksum import ChecksumCalculator


class TestChecksumOperations:
    """Test checksum calculation methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_mirror = Path(self.temp_dir) / "mirror"
        self.mock_mirror.mkdir()
        
        # Create test directory structure
        self.create_mock_library_structure()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def create_mock_library_structure(self):
        """Create mock library files in mirror for testing."""
        # Create a mock library directory
        lib_dir = self.mock_mirror / "libs" / "test_lib"
        lib_dir.mkdir(parents=True)
        
        # Create some mock analog design files
        (lib_dir / "amplifier.sch").write_text("* Amplifier schematic\n.subckt amp in out\n.ends")
        (lib_dir / "amplifier.sym").write_text("v {xschem version=3.4.4}\nG {type=symbol}")
        (lib_dir / "testbench.sch").write_text("* Testbench\n.include amplifier.sch")
        
        # Create subdirectory with more files
        models_dir = lib_dir / "models"
        models_dir.mkdir()
        (models_dir / "nmos.sp").write_text(".model nmos_model nmos")
        (models_dir / "pmos.sp").write_text(".model pmos_model pmos")
    
    def test_calculate_directory_checksum(self):
        """Test directory checksum calculation."""
        lib_dir = self.mock_mirror / "libs" / "test_lib"
        
        # Calculate checksum
        checksum1 = ChecksumCalculator.calculate_directory_checksum(lib_dir)
        assert len(checksum1) == 64  # SHA256 hex length
        assert checksum1 != ""
        
        # Same directory should produce same checksum
        checksum2 = ChecksumCalculator.calculate_directory_checksum(lib_dir)
        assert checksum1 == checksum2
        
        # Modified directory should produce different checksum
        (lib_dir / "new_file.txt").write_text("new content")
        checksum3 = ChecksumCalculator.calculate_directory_checksum(lib_dir)
        assert checksum3 != checksum1
    
    def test_calculate_directory_checksum_empty_dir(self):
        """Test checksum of empty directory."""
        empty_dir = self.mock_mirror / "empty"
        empty_dir.mkdir()
        
        checksum = ChecksumCalculator.calculate_directory_checksum(empty_dir)
        assert len(checksum) == 64
        assert checksum != ""
    
    def test_calculate_directory_checksum_nonexistent(self):
        """Test checksum of nonexistent directory."""
        nonexistent = self.mock_mirror / "nonexistent"
        checksum = ChecksumCalculator.calculate_directory_checksum(nonexistent)
        assert checksum == ""