"""Unit tests for license detection utilities."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from tempfile import TemporaryDirectory

from analog_hub.utils.license import LicenseDetector, LicenseInfo


class TestLicenseDetector:
    """Test license detection functionality."""
    
    def test_init(self):
        """Test LicenseDetector initialization."""
        detector = LicenseDetector()
        assert detector.LICENSE_FILENAMES
        assert detector.LICENSE_PATTERNS
        assert len(detector.LICENSE_PATTERNS) > 5  # Should have multiple license types
    
    def test_detect_license_no_file(self):
        """Test license detection when no license file exists."""
        detector = LicenseDetector()
        
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            result = detector.detect_license(repo_path)
            
            assert result.license_type is None
            assert result.license_file is None
            assert result.content_snippet is None
    
    def test_detect_license_mit_license(self):
        """Test detection of MIT license."""
        detector = LicenseDetector()
        
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            license_file = repo_path / "LICENSE"
            
            mit_content = """MIT License

Copyright (c) 2023 Test User

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
"""
            license_file.write_text(mit_content)
            
            result = detector.detect_license(repo_path)
            
            assert result.license_type == "MIT"
            assert result.license_file == "LICENSE"
            assert "MIT License" in result.content_snippet
            assert "Copyright (c) 2023 Test User" in result.content_snippet
    
    def test_detect_license_apache_license(self):
        """Test detection of Apache 2.0 license."""
        detector = LicenseDetector()
        
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            license_file = repo_path / "LICENSE.txt"
            
            apache_content = """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
"""
            license_file.write_text(apache_content)
            
            result = detector.detect_license(repo_path)
            
            assert result.license_type == "Apache-2.0"
            assert result.license_file == "LICENSE.txt"
            assert "Apache License" in result.content_snippet
    
    def test_detect_license_gpl3_license(self):
        """Test detection of GPL 3.0 license."""
        detector = LicenseDetector()
        
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            license_file = repo_path / "COPYING"
            
            gpl_content = """GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <http://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.
"""
            license_file.write_text(gpl_content)
            
            result = detector.detect_license(repo_path)
            
            assert result.license_type == "GPL-3.0"
            assert result.license_file == "COPYING"
            assert "GNU GENERAL PUBLIC LICENSE" in result.content_snippet
    
    def test_detect_license_bsd_license(self):
        """Test detection of BSD license."""
        detector = LicenseDetector()
        
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            license_file = repo_path / "LICENSE.md"
            
            bsd_content = """BSD 3-Clause License

Copyright (c) 2023, Test User
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
"""
            license_file.write_text(bsd_content)
            
            result = detector.detect_license(repo_path)
            
            assert result.license_type == "BSD-3-Clause"
            assert result.license_file == "LICENSE.md"
    
    def test_detect_license_unknown_content(self):
        """Test detection when license file has unknown/custom content."""
        detector = LicenseDetector()
        
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            license_file = repo_path / "LICENSE"
            
            custom_content = """Custom Proprietary License

This software is proprietary and confidential.
All rights reserved.
"""
            license_file.write_text(custom_content)
            
            result = detector.detect_license(repo_path)
            
            assert result.license_type == "Unknown"
            assert result.license_file == "LICENSE"
            assert "Custom Proprietary License" in result.content_snippet
    
    def test_detect_license_file_priority(self):
        """Test that LICENSE is preferred over LICENSE.txt."""
        detector = LicenseDetector()
        
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            # Create both files
            (repo_path / "LICENSE").write_text("MIT License")
            (repo_path / "LICENSE.txt").write_text("Apache License Version 2.0")
            
            result = detector.detect_license(repo_path)
            
            # Should prefer LICENSE over LICENSE.txt
            assert result.license_file == "LICENSE"
            assert result.license_type == "MIT"
    
    def test_detect_license_encoding_issues(self):
        """Test handling of encoding issues in license files."""
        detector = LicenseDetector()
        
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            license_file = repo_path / "LICENSE"
            
            # Write binary content that might cause encoding issues
            license_file.write_bytes(b'\xff\xfe\x4d\x00\x49\x00\x54\x00')  # UTF-16 BOM + "MIT"
            
            result = detector.detect_license(repo_path)
            
            # Should handle gracefully and not crash
            assert result.license_file == "LICENSE"
            # Type might be None or Unknown depending on content parsing
            assert result.license_type in [None, "Unknown"]
    
    def test_find_license_file_all_variants(self):
        """Test finding various license file name variants."""
        detector = LicenseDetector()
        
        # Test uppercase variants (these should work)
        uppercase_cases = ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENSE.rst", "COPYING", "COPYRIGHT", "LICENCE"]
        
        for filename in uppercase_cases:
            with TemporaryDirectory() as tmpdir:
                repo_path = Path(tmpdir)
                license_file = repo_path / filename
                license_file.write_text("MIT License")
                
                found_file = detector._find_license_file(repo_path)
                
                assert found_file is not None
                assert found_file.name == filename
        
        # Test lowercase variants separately - on case-insensitive filesystems these might resolve to uppercase
        lowercase_cases = ["license", "license.txt"]
        
        for filename in lowercase_cases:
            with TemporaryDirectory() as tmpdir:
                repo_path = Path(tmpdir)
                license_file = repo_path / filename
                license_file.write_text("MIT License")
                
                found_file = detector._find_license_file(repo_path)
                
                assert found_file is not None
                # On case-insensitive filesystems, this might resolve to the uppercase version
                assert found_file.name.lower() == filename.lower()
    
    def test_identify_license_type_patterns(self):
        """Test license type identification with various patterns."""
        detector = LicenseDetector()
        
        test_cases = [
            ("MIT License\n\nPermission is hereby granted", "MIT"),
            ("Apache License Version 2.0", "Apache-2.0"),
            ("GNU GENERAL PUBLIC LICENSE Version 3", "GPL-3.0"),
            ("GNU GENERAL PUBLIC LICENSE Version 2", "GPL-2.0"),
            ("BSD 3-clause license", "BSD-3-Clause"),
            ("BSD 2-clause license", "BSD-2-Clause"),
            ("ISC License", "ISC"),
            ("Mozilla Public License Version 2.0", "MPL-2.0"),
            ("GNU LESSER GENERAL PUBLIC LICENSE Version 3", "LGPL-3.0"),
            ("GNU LESSER GENERAL PUBLIC LICENSE Version 2.1", "LGPL-2.1"),
            ("Custom license text", "Unknown"),
            ("", None),
        ]
        
        for content, expected_type in test_cases:
            result = detector._identify_license_type(content)
            assert result == expected_type, f"Failed for content: {content[:50]}..."
    
    def test_extract_content_snippet(self):
        """Test content snippet extraction."""
        detector = LicenseDetector()
        
        content = """
MIT License

Copyright (c) 2023 Test User

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files...
"""
        
        snippet = detector._extract_content_snippet(content)
        lines = snippet.split('\n')
        
        assert len(lines) <= 3
        assert "MIT License" in lines[0]
        assert "Copyright (c) 2023 Test User" in lines[1]
        assert "Permission is hereby granted" in lines[2]
    
    def test_extract_content_snippet_with_headers(self):
        """Test content snippet extraction skipping common headers."""
        detector = LicenseDetector()
        
        content = """===================================
MIT LICENSE FILE
===================================

MIT License

Copyright (c) 2023 Test User
"""
        
        snippet = detector._extract_content_snippet(content)
        lines = snippet.split('\n')
        
        # Should skip the header lines
        assert "MIT License" in lines[0]
        assert "Copyright (c) 2023 Test User" in lines[1]
    
    def test_get_license_compatibility_warning_gpl(self):
        """Test GPL compatibility warnings."""
        detector = LicenseDetector()
        
        warning = detector.get_license_compatibility_warning("GPL-3.0")
        assert "GPL license detected" in warning
        assert "derivative works" in warning
        
        warning = detector.get_license_compatibility_warning("GPL-2.0")
        assert "GPL license detected" in warning
    
    def test_get_license_compatibility_warning_lgpl(self):
        """Test LGPL compatibility warnings."""
        detector = LicenseDetector()
        
        warning = detector.get_license_compatibility_warning("LGPL-3.0")
        assert "LGPL license detected" in warning
        assert "linking requirements" in warning
        
        warning = detector.get_license_compatibility_warning("LGPL-2.1")
        assert "LGPL license detected" in warning
    
    def test_get_license_compatibility_warning_unknown(self):
        """Test unknown license warnings."""
        detector = LicenseDetector()
        
        warning = detector.get_license_compatibility_warning("Unknown")
        assert "Unknown license type" in warning
        assert "manual review required" in warning
    
    def test_get_license_compatibility_warning_none(self):
        """Test no license detected warnings."""
        detector = LicenseDetector()
        
        warning = detector.get_license_compatibility_warning(None)
        assert "No license detected" in warning
        assert "verify legal compliance" in warning
    
    def test_get_license_compatibility_warning_permissive(self):
        """Test that permissive licenses don't generate warnings."""
        detector = LicenseDetector()
        
        permissive_licenses = ["MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC"]
        
        for license_type in permissive_licenses:
            warning = detector.get_license_compatibility_warning(license_type)
            assert warning is None


class TestLicenseInfo:
    """Test LicenseInfo dataclass."""
    
    def test_license_info_creation(self):
        """Test LicenseInfo dataclass creation."""
        info = LicenseInfo(
            license_type="MIT",
            license_file="LICENSE",
            content_snippet="MIT License\nCopyright..."
        )
        
        assert info.license_type == "MIT"
        assert info.license_file == "LICENSE"
        assert info.content_snippet == "MIT License\nCopyright..."
    
    def test_license_info_none_values(self):
        """Test LicenseInfo with None values."""
        info = LicenseInfo(
            license_type=None,
            license_file=None,
            content_snippet=None
        )
        
        assert info.license_type is None
        assert info.license_file is None
        assert info.content_snippet is None