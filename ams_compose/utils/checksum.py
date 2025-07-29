"""Checksum calculation utilities for ams-compose.

This module provides centralized checksum operations for:
- Directory content validation
- File content validation  
- Repository URL hashing
"""

import hashlib
from pathlib import Path


class ChecksumCalculator:
    """Centralized checksum calculation utilities."""
    
    @staticmethod
    def calculate_directory_checksum(directory: Path) -> str:
        """Calculate SHA256 checksum of directory contents.
        
        Args:
            directory: Directory to checksum
            
        Returns:
            Hex string of SHA256 checksum, empty string if directory doesn't exist
        """
        if not directory.exists() or not directory.is_dir():
            return ""
        
        sha256_hash = hashlib.sha256()
        
        # Get all files recursively, sorted for consistent ordering
        files = sorted(directory.rglob("*"))
        
        for file_path in files:
            if file_path.is_file():
                # Skip metadata files when calculating checksum
                if file_path.name.startswith(".ams-compose-meta"):
                    continue
                
                # Include relative path in hash for structure validation
                relative_path = file_path.relative_to(directory)
                sha256_hash.update(str(relative_path).encode('utf-8'))
                
                # Include file content in hash
                try:
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(chunk)
                except (OSError, PermissionError):
                    # Include placeholder for unreadable files
                    sha256_hash.update(b"<unreadable>")
        
        return sha256_hash.hexdigest()
    
    @staticmethod
    def calculate_file_checksum(file_path: Path) -> str:
        """Calculate SHA256 checksum of a single file.
        
        Args:
            file_path: Path to file to checksum
            
        Returns:
            Hex string of SHA256 checksum, empty string if file doesn't exist
        """
        if not file_path.exists() or not file_path.is_file():
            return ""
        
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, PermissionError):
            return ""
    
    @staticmethod
    def normalize_repo_url(repo_url: str) -> str:
        """Normalize repository URL for consistent hashing.
        
        Args:
            repo_url: Repository URL in various formats
            
        Returns:
            Normalized URL string
        """
        # Remove trailing slashes and .git suffixes
        normalized = repo_url.rstrip('/')
        if normalized.endswith('.git'):
            normalized = normalized[:-4]
        
        # Convert SSH URLs to HTTPS for consistency
        if normalized.startswith('git@github.com:'):
            normalized = normalized.replace('git@github.com:', 'https://github.com/')
        elif normalized.startswith('git@gitlab.com:'):
            normalized = normalized.replace('git@gitlab.com:', 'https://gitlab.com/')
        
        return normalized.lower()
    
    @staticmethod
    def generate_repo_hash(repo_url: str) -> str:
        """Generate SHA256 hash for repository URL.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            16-character hex hash (first 64 bits of SHA256)
        """
        normalized_url = ChecksumCalculator.normalize_repo_url(repo_url)
        hash_bytes = hashlib.sha256(normalized_url.encode('utf-8')).digest()
        return hash_bytes[:8].hex()  # First 8 bytes = 16 hex chars