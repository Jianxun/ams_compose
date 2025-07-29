"""Tests for checksum calculation utilities."""

import hashlib
import tempfile
from pathlib import Path

import pytest

from ams_compose.utils.checksum import ChecksumCalculator


class TestChecksumCalculator:
    """Test checksum calculation utilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test directory structure
        self.test_lib_dir = self.temp_dir / "test_lib"
        self.test_lib_dir.mkdir()
        
        # Create test files
        (self.test_lib_dir / "file1.txt").write_text("content1")
        (self.test_lib_dir / "file2.txt").write_text("content2")
        
        # Create subdirectory with files
        sub_dir = self.test_lib_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("content3")
        
        # Create single test file
        self.test_file = self.temp_dir / "single_file.txt"
        self.test_file.write_text("single file content")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_calculate_directory_checksum_basic(self):
        """Test basic directory checksum calculation."""
        checksum = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        
        # Should return a 64-character SHA256 hex string
        assert len(checksum) == 64
        assert checksum != ""
        assert all(c in "0123456789abcdef" for c in checksum)
    
    def test_calculate_directory_checksum_consistency(self):
        """Test that same directory produces same checksum."""
        checksum1 = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        checksum2 = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        
        assert checksum1 == checksum2
    
    def test_calculate_directory_checksum_detects_changes(self):
        """Test that directory changes produce different checksums."""
        checksum1 = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        
        # Add a new file
        (self.test_lib_dir / "new_file.txt").write_text("new content")
        checksum2 = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        
        assert checksum1 != checksum2
        
        # Modify existing file
        (self.test_lib_dir / "file1.txt").write_text("modified content")
        checksum3 = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        
        assert checksum2 != checksum3
    
    def test_calculate_directory_checksum_empty_directory(self):
        """Test checksum of empty directory."""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()
        
        checksum = ChecksumCalculator.calculate_directory_checksum(empty_dir)
        assert len(checksum) == 64
        assert checksum != ""
    
    def test_calculate_directory_checksum_nonexistent_directory(self):
        """Test checksum of nonexistent directory."""
        nonexistent = self.temp_dir / "nonexistent"
        
        checksum = ChecksumCalculator.calculate_directory_checksum(nonexistent)
        assert checksum == ""
    
    def test_calculate_directory_checksum_ignores_metadata_files(self):
        """Test that metadata files are ignored in checksum calculation."""
        checksum1 = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        
        # Add metadata file
        (self.test_lib_dir / ".analog-hub-meta.yaml").write_text("metadata: test")
        checksum2 = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        
        # Checksum should be the same
        assert checksum1 == checksum2
        
        # Add another metadata file variant
        (self.test_lib_dir / ".analog-hub-meta-test.yaml").write_text("metadata: test2")
        checksum3 = ChecksumCalculator.calculate_directory_checksum(self.test_lib_dir)
        
        assert checksum1 == checksum3
    
    def test_calculate_directory_checksum_includes_file_paths(self):
        """Test that file paths are included in checksum calculation."""
        # Create two directories with same content but different structure
        dir1 = self.temp_dir / "dir1"
        dir1.mkdir()
        (dir1 / "file.txt").write_text("content")
        
        dir2 = self.temp_dir / "dir2"
        dir2.mkdir()
        subdir = dir2 / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")
        
        checksum1 = ChecksumCalculator.calculate_directory_checksum(dir1)
        checksum2 = ChecksumCalculator.calculate_directory_checksum(dir2)
        
        # Different structure should produce different checksums
        assert checksum1 != checksum2
    
    def test_calculate_file_checksum_basic(self):
        """Test basic file checksum calculation."""
        checksum = ChecksumCalculator.calculate_file_checksum(self.test_file)
        
        # Should return a 64-character SHA256 hex string
        assert len(checksum) == 64
        assert checksum != ""
        assert all(c in "0123456789abcdef" for c in checksum)
        
        # Verify it matches direct hashlib calculation
        expected = hashlib.sha256(self.test_file.read_bytes()).hexdigest()
        assert checksum == expected
    
    def test_calculate_file_checksum_consistency(self):
        """Test that same file produces same checksum."""
        checksum1 = ChecksumCalculator.calculate_file_checksum(self.test_file)
        checksum2 = ChecksumCalculator.calculate_file_checksum(self.test_file)
        
        assert checksum1 == checksum2
    
    def test_calculate_file_checksum_detects_changes(self):
        """Test that file changes produce different checksums."""
        checksum1 = ChecksumCalculator.calculate_file_checksum(self.test_file)
        
        # Modify file content
        self.test_file.write_text("modified content")
        checksum2 = ChecksumCalculator.calculate_file_checksum(self.test_file)
        
        assert checksum1 != checksum2
    
    def test_calculate_file_checksum_nonexistent_file(self):
        """Test checksum of nonexistent file."""
        nonexistent = self.temp_dir / "nonexistent.txt"
        
        checksum = ChecksumCalculator.calculate_file_checksum(nonexistent)
        assert checksum == ""
    
    def test_calculate_file_checksum_directory_path(self):
        """Test checksum when path is a directory, not a file."""
        checksum = ChecksumCalculator.calculate_file_checksum(self.test_lib_dir)
        assert checksum == ""
    
    def test_normalize_repo_url_basic(self):
        """Test basic URL normalization."""
        test_cases = [
            ("https://github.com/user/repo", "https://github.com/user/repo"),
            ("https://github.com/user/repo/", "https://github.com/user/repo"),
            ("https://github.com/user/repo.git", "https://github.com/user/repo"),
            ("https://github.com/user/repo.git/", "https://github.com/user/repo"),
            ("HTTPS://GITHUB.COM/USER/REPO", "https://github.com/user/repo"),
        ]
        
        for input_url, expected in test_cases:
            result = ChecksumCalculator.normalize_repo_url(input_url)
            assert result == expected, f"Failed for {input_url}"
    
    def test_normalize_repo_url_ssh_conversion(self):
        """Test SSH URL conversion to HTTPS."""
        test_cases = [
            ("git@github.com:user/repo", "https://github.com/user/repo"),
            ("git@github.com:user/repo.git", "https://github.com/user/repo"),
            ("git@gitlab.com:user/repo", "https://gitlab.com/user/repo"),
            ("git@gitlab.com:user/repo.git", "https://gitlab.com/user/repo"),
        ]
        
        for input_url, expected in test_cases:
            result = ChecksumCalculator.normalize_repo_url(input_url)
            assert result == expected, f"Failed for {input_url}"
    
    def test_normalize_repo_url_preserves_other_hosts(self):
        """Test that other SSH hosts are not converted."""
        test_cases = [
            ("git@example.com:user/repo", "git@example.com:user/repo"),
            ("git@bitbucket.org:user/repo", "git@bitbucket.org:user/repo"),
        ]
        
        for input_url, expected in test_cases:
            result = ChecksumCalculator.normalize_repo_url(input_url)
            assert result == expected, f"Failed for {input_url}"
    
    def test_generate_repo_hash_basic(self):
        """Test basic repository hash generation."""
        repo_url = "https://github.com/user/repo"
        hash_result = ChecksumCalculator.generate_repo_hash(repo_url)
        
        # Should return a 16-character hex string
        assert len(hash_result) == 16
        assert all(c in "0123456789abcdef" for c in hash_result)
    
    def test_generate_repo_hash_consistency(self):
        """Test that same URL produces same hash."""
        repo_url = "https://github.com/user/repo"
        hash1 = ChecksumCalculator.generate_repo_hash(repo_url)
        hash2 = ChecksumCalculator.generate_repo_hash(repo_url)
        
        assert hash1 == hash2
    
    def test_generate_repo_hash_normalizes_input(self):
        """Test that equivalent URLs produce same hash."""
        test_cases = [
            "https://github.com/user/repo",
            "https://github.com/user/repo/",
            "https://github.com/user/repo.git",
            "https://github.com/user/repo.git/",
            "git@github.com:user/repo",
            "git@github.com:user/repo.git",
            "HTTPS://GITHUB.COM/USER/REPO",
        ]
        
        hashes = [ChecksumCalculator.generate_repo_hash(url) for url in test_cases]
        
        # All should produce the same hash
        assert all(h == hashes[0] for h in hashes)
    
    def test_generate_repo_hash_different_urls_different_hashes(self):
        """Test that different URLs produce different hashes."""
        urls = [
            "https://github.com/user1/repo",
            "https://github.com/user2/repo", 
            "https://github.com/user1/repo2",
            "https://gitlab.com/user1/repo",
        ]
        
        hashes = [ChecksumCalculator.generate_repo_hash(url) for url in urls]
        
        # All hashes should be different
        assert len(set(hashes)) == len(hashes)
    
    def test_generate_repo_hash_matches_expected_algorithm(self):
        """Test that hash generation matches expected SHA256 algorithm."""
        repo_url = "https://github.com/user/repo"
        expected_normalized = "https://github.com/user/repo"
        expected_hash_bytes = hashlib.sha256(expected_normalized.encode('utf-8')).digest()
        expected_hash = expected_hash_bytes[:8].hex()
        
        result = ChecksumCalculator.generate_repo_hash(repo_url)
        assert result == expected_hash