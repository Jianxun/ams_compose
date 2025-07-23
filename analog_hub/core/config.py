"""Configuration models for analog-hub."""

from pathlib import Path
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
import yaml


class ExportSpec(BaseModel):
    """Specification for an exported library."""
    model_config = ConfigDict(extra="allow")
    
    path: str = Field(..., description="Relative path to the library from repository root")
    type: str = Field(..., description="Library category (design, testbench, pdk, etc.)")
    license: Optional[str] = Field(None, description="License information for the library")
    description: Optional[str] = Field(None, description="Description of the library")


class ImportSpec(BaseModel):
    """Specification for an imported library."""
    model_config = ConfigDict(extra="allow")
    
    repo: str = Field(..., description="Repository URL to import from")
    ref: str = Field(..., description="Git reference (branch, tag, or commit hash)")
    library: Optional[str] = Field(None, description="Specific library name to import (optional)")


class LockEntry(BaseModel):
    """Lock file entry for tracking installed libraries."""
    model_config = ConfigDict(extra="allow")
    
    repo: str = Field(..., description="Repository URL")
    ref: str = Field(..., description="Original git reference")
    commit: str = Field(..., description="Resolved commit hash")
    path: str = Field(..., description="Source path in repository")
    type: str = Field(..., description="Library type")
    license: Optional[str] = Field(None, description="License at time of installation")
    checksum: str = Field(..., description="Content checksum for validation")
    installed_at: str = Field(..., description="Installation timestamp")


class AnalogHubConfig(BaseModel):
    """Main configuration model for analog-hub.yaml."""
    model_config = ConfigDict(extra="allow")
    
    analog_hub_root: str = Field(
        default="libs", 
        description="Root directory for imported libraries",
        alias="analog-hub-root"
    )
    imports: Optional[Dict[str, ImportSpec]] = Field(
        default_factory=dict,
        description="Libraries to import"
    )
    exports: Optional[Dict[str, ExportSpec]] = Field(
        default_factory=dict,
        description="Libraries available for export"
    )
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "AnalogHubConfig":
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


class LockFile(BaseModel):
    """Lock file model for tracking installed state."""
    model_config = ConfigDict(extra="allow")
    
    version: str = Field(default="1", description="Lock file format version")
    analog_hub_root: str = Field(..., description="Root directory for libraries")
    libraries: Dict[str, LockEntry] = Field(
        default_factory=dict,
        description="Installed library entries"
    )
    
    @classmethod
    def from_yaml(cls, lock_path: Path) -> "LockFile":
        """Load lock file from YAML."""
        if not lock_path.exists():
            return cls(analog_hub_root="libs")
        
        with open(lock_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, lock_path: Path) -> None:
        """Save lock file to YAML."""
        data = self.model_dump(exclude_none=True)
        with open(lock_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)