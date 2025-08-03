"""Configuration models for ams-compose."""

from pathlib import Path
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field, ConfigDict
import yaml


class ImportSpec(BaseModel):
    """Specification for an imported library."""
    model_config = ConfigDict(extra="forbid")
    
    repo: str = Field(..., description="Git repository URL")
    ref: str = Field(..., description="Git reference (branch, tag, or commit)")
    source_path: str = Field(..., description="Path within repo to extract")
    local_path: Optional[str] = Field(
        None, 
        description="Local path override (defaults to {library_root}/{import_key}). If specified, overrides library_root completely."
    )
    checkin: bool = Field(
        default=True,
        description="Whether to include this library in version control"
    )
    ignore_patterns: List[str] = Field(
        default_factory=list,
        description="Additional gitignore-style patterns to ignore during extraction"
    )
    license: Optional[str] = Field(
        default=None,
        description="Override for library license (auto-detected if not specified)"
    )


class LockEntry(BaseModel):
    """Lock file entry for tracking installed libraries."""
    model_config = ConfigDict(extra="forbid")
    
    repo: str = Field(..., description="Repository URL")
    ref: str = Field(..., description="Original git reference")
    commit: str = Field(..., description="Resolved commit hash")
    source_path: str = Field(..., description="Source path in repository")
    local_path: str = Field(..., description="Local path under ams-compose-root")
    checksum: str = Field(..., description="Content checksum for validation")
    installed_at: str = Field(..., description="Installation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    last_validated: Optional[str] = Field(default=None, description="Last validation timestamp")
    validation_status: str = Field(default="unknown", description="Validation status: valid/modified/missing/unknown")
    checkin: bool = Field(default=True, description="Whether library is included in version control")
    license: Optional[str] = Field(default=None, description="Library license (user-specified or auto-detected)")
    detected_license: Optional[str] = Field(default=None, description="Auto-detected license from repository")
    install_status: Optional[str] = Field(default=None, description="Install operation status: installed/updated/up_to_date/error")
    license_change: Optional[str] = Field(default=None, description="License change information for updates") 
    license_warning: Optional[str] = Field(default=None, description="License compatibility warning")


class ComposeConfig(BaseModel):
    """Main configuration model for ams-compose.yaml."""
    model_config = ConfigDict(extra="forbid")
    
    library_root: str = Field(
        default="designs/libs", 
        description="Default root directory for imported libraries (used when local_path not specified)"
    )
    imports: Optional[Dict[str, ImportSpec]] = Field(
        default_factory=dict,
        description="Libraries to import"
    )
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "ComposeConfig":
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        data = self.model_dump(exclude_none=True)
        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


class LockFile(BaseModel):
    """Lock file model for tracking installed state."""
    model_config = ConfigDict(extra="forbid")
    
    version: str = Field(default="1", description="Lock file format version")
    library_root: str = Field(..., description="Default root directory for libraries")
    libraries: Dict[str, LockEntry] = Field(
        default_factory=dict,
        description="Installed library entries"
    )
    
    @classmethod
    def from_yaml(cls, lock_path: Path) -> "LockFile":
        """Load lock file from YAML."""
        if not lock_path.exists():
            return cls(library_root="libs")
        
        with open(lock_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, lock_path: Path) -> None:
        """Save lock file to YAML."""
        data = self.model_dump(exclude_none=True)
        with open(lock_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)