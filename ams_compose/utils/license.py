"""License detection utilities for ams-compose."""

import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class LicenseInfo:
    """Information about a detected license."""
    license_type: Optional[str]  # e.g., "MIT", "Apache-2.0", "GPL-3.0"
    license_file: Optional[str]  # Path to the license file found
    content_snippet: Optional[str]  # First few lines of license for verification


class LicenseDetector:
    """Detects and identifies licenses in repositories."""
    
    # Common license file names (in order of preference)
    LICENSE_FILENAMES = [
        'LICENSE',
        'LICENSE.txt',
        'LICENSE.md',
        'LICENSE.rst',
        'license',
        'license.txt', 
        'license.md',
        'license.rst',
        'COPYING',
        'COPYRIGHT',
        'LICENCE',  # British spelling
        'LICENCE.txt',
        'LICENCE.md',
    ]
    
    # License type patterns for content-based detection
    LICENSE_PATTERNS = {
        'MIT': [
            r'MIT License',
            r'Permission is hereby granted, free of charge',
            r'MIT.*license',
        ],
        'Apache-2.0': [
            r'Apache License.*Version 2\.0',
            r'Licensed under the Apache License, Version 2\.0',
        ],
        'GPL-3.0': [
            r'GNU GENERAL PUBLIC LICENSE.*Version 3',
            r'GPL.*version 3',
            r'GPLv3',
        ],
        'GPL-2.0': [
            r'GNU GENERAL PUBLIC LICENSE.*Version 2',
            r'GPL.*version 2', 
            r'GPLv2',
        ],
        'BSD-3-Clause': [
            r'BSD.*3.*clause',
            r'Redistribution and use in source and binary forms.*with or without modification',
        ],
        'BSD-2-Clause': [
            r'BSD.*2.*clause',
            r'Redistribution and use in source and binary forms.*provided that',
        ],
        'ISC': [
            r'ISC License',
            r'Permission to use, copy, modify.*distribute this software',
        ],
        'MPL-2.0': [
            r'Mozilla Public License.*Version 2\.0',
            r'MPL.*2\.0',
        ],
        'LGPL-3.0': [
            r'GNU LESSER GENERAL PUBLIC LICENSE.*Version 3',
            r'LGPL.*version 3',
        ],
        'LGPL-2.1': [
            r'GNU LESSER GENERAL PUBLIC LICENSE.*Version 2\.1',
            r'LGPL.*version 2\.1',
        ],
    }
    
    def detect_license(self, repo_path: Path) -> LicenseInfo:
        """
        Detect license information from a repository path.
        
        Args:
            repo_path: Path to the repository root
            
        Returns:
            LicenseInfo with detected license information
        """
        # First, try to find a license file
        license_file = self._find_license_file(repo_path)
        
        if not license_file:
            return LicenseInfo(
                license_type=None,
                license_file=None,
                content_snippet=None
            )
        
        # Read license file content
        try:
            content = license_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            # Fallback to ignore errors if encoding issues
            try:
                content = license_file.read_text(encoding='latin1', errors='ignore')
            except Exception:
                return LicenseInfo(
                    license_type="Unknown",
                    license_file=str(license_file.relative_to(repo_path)),
                    content_snippet=None
                )
        
        # Detect license type from content
        license_type = self._identify_license_type(content)
        
        # Get content snippet (first 3 lines of actual content)
        content_snippet = self._extract_content_snippet(content)
        
        return LicenseInfo(
            license_type=license_type,
            license_file=str(license_file.relative_to(repo_path)),
            content_snippet=content_snippet
        )
    
    def _find_license_file(self, repo_path: Path) -> Optional[Path]:
        """Find the most likely license file in the repository."""
        for filename in self.LICENSE_FILENAMES:
            license_path = repo_path / filename
            if license_path.is_file():
                return license_path
        return None
    
    def _identify_license_type(self, content: str) -> Optional[str]:
        """Identify license type from file content using pattern matching."""
        # Normalize content for pattern matching
        normalized_content = ' '.join(content.split())
        
        # Check more specific patterns first (GPL, Apache) before generic ones (MIT)
        license_priority = [
            'GPL-3.0', 'GPL-2.0', 'LGPL-3.0', 'LGPL-2.1', 
            'Apache-2.0', 'MPL-2.0', 'BSD-3-Clause', 'BSD-2-Clause', 
            'ISC', 'MIT'
        ]
        
        for license_type in license_priority:
            if license_type in self.LICENSE_PATTERNS:
                patterns = self.LICENSE_PATTERNS[license_type]
                for pattern in patterns:
                    if re.search(pattern, normalized_content, re.IGNORECASE):
                        return license_type
        
        # If no specific type detected but we have content, return "Unknown"
        if content.strip():
            return "Unknown"
        
        return None
    
    def _extract_content_snippet(self, content: str) -> str:
        """Extract first few meaningful lines from license content."""
        lines = content.strip().split('\n')
        meaningful_lines = []
        
        # Detect lines that are surrounded by decoration (headers/titles)
        decoration_chars = set('=-*#')
        is_in_header_block = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a decoration line
            is_decoration = (line.startswith('===') or line.startswith('---') or 
                           line.startswith('***') or line.startswith('###') or
                           (len(set(line)) == 1 and line[0] in decoration_chars))
            
            if is_decoration:
                is_in_header_block = not is_in_header_block
                continue
            
            # Skip lines that are in header blocks (between decoration lines)
            if is_in_header_block:
                continue
                
            meaningful_lines.append(line)
            if len(meaningful_lines) >= 3:
                break
        
        return '\n'.join(meaningful_lines)
    
    def get_license_compatibility_warning(self, license_type: Optional[str]) -> Optional[str]:
        """
        Get compatibility warning for potentially problematic licenses.
        
        Args:
            license_type: The detected license type
            
        Returns:
            Warning message if license may cause compatibility issues, None otherwise
        """
        if not license_type:
            return "No license detected - verify legal compliance before use"
        
        # GPL licenses have strict copyleft requirements
        if license_type.startswith('GPL'):
            return "GPL license detected - may require derivative works to be GPL licensed"
        
        # LGPL is less restrictive but still has requirements
        if license_type.startswith('LGPL'):
            return "LGPL license detected - review linking requirements for proprietary code"
        
        # Unknown licenses require manual review
        if license_type == "Unknown":
            return "Unknown license type - manual review required for compliance"
        
        return None