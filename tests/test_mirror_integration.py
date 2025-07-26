"""Integration tests for repository mirroring with real repositories."""

import tempfile
from pathlib import Path

import pytest

from analog_hub.core.mirror import RepositoryMirror
from analog_hub.core.config import AnalogHubConfig
from analog_hub.utils.checksum import ChecksumCalculator


class TestMirrorIntegration:
    """Integration tests using real analog design repositories."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.mirror_root = Path(self.temp_dir) / "mirrors"
        self.mirror = RepositoryMirror(self.mirror_root)
        
        # Load test repositories from analog-hub.yaml
        config_path = Path("analog-hub.yaml")
        if config_path.exists():
            self.config = AnalogHubConfig.from_yaml(config_path)
        else:
            # Fallback test repositories if config doesn't exist
            self.test_repos = {
                "model_pll": {
                    "repo": "https://github.com/peterkinget/testing-project-template",
                    "ref": "PK_PLL_modeling", 
                    "source_path": "designs/libs/model_pll"
                },
                "switch_matrix": {
                    "repo": "https://github.com/mosbiuschip/switch_matrix_gf180mcu_9t5v0",
                    "ref": "main",
                    "source_path": "."
                }
            }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.slow
    def test_create_mirror_real_repo_pll(self):
        """Test creating mirror with real PLL modeling repository."""
        repo_url = "https://github.com/peterkinget/testing-project-template"
        ref = "PK_PLL_modeling"
        
        # Create mirror
        metadata = self.mirror.create_mirror(repo_url, ref)
        
        # Verify metadata
        assert metadata.repo_url == repo_url
        assert metadata.current_ref == ref
        assert len(metadata.resolved_commit) == 40  # SHA hash length
        assert metadata.repo_hash == ChecksumCalculator.generate_repo_hash(repo_url)
        
        # Verify mirror directory exists
        mirror_path = self.mirror.get_mirror_path(repo_url)
        assert mirror_path.exists()
        assert mirror_path.is_dir()
        
        # Verify it's a valid git repository
        assert (mirror_path / ".git").exists()
        
        # Verify metadata file exists
        metadata_file = mirror_path / ".mirror-meta.yaml"
        assert metadata_file.exists()
        
        # Verify the source path we want exists
        source_path = mirror_path / "designs" / "libs" / "model_pll"
        assert source_path.exists()
        assert source_path.is_dir()
        
        # Verify analog design files exist (xschem files)
        xschem_files = list(source_path.glob("*.sch"))
        sym_files = list(source_path.glob("*.sym"))
        assert len(xschem_files) > 0, "Should have xschem schematic files"
        assert len(sym_files) > 0, "Should have xschem symbol files"
        
        print(f"✅ PLL Mirror created successfully:")
        print(f"   Repository: {repo_url}")
        print(f"   Branch: {ref}")
        print(f"   Commit: {metadata.resolved_commit}")
        print(f"   Mirror path: {mirror_path}")
        print(f"   Xschem files: {len(xschem_files)}")
        print(f"   Symbol files: {len(sym_files)}")
    
    @pytest.mark.slow 
    def test_create_mirror_real_repo_switch_matrix(self):
        """Test creating mirror with real switch matrix repository."""
        repo_url = "https://github.com/mosbiuschip/switch_matrix_gf180mcu_9t5v0"
        ref = "main"
        
        # Create mirror
        metadata = self.mirror.create_mirror(repo_url, ref)
        
        # Verify metadata
        assert metadata.repo_url == repo_url
        assert metadata.current_ref == ref
        assert len(metadata.resolved_commit) == 40
        assert metadata.repo_hash == ChecksumCalculator.generate_repo_hash(repo_url)
        
        # Verify mirror directory exists
        mirror_path = self.mirror.get_mirror_path(repo_url)
        assert mirror_path.exists()
        assert mirror_path.is_dir()
        
        # Verify it's a valid git repository
        assert (mirror_path / ".git").exists()
        
        # Verify metadata file exists
        metadata_file = mirror_path / ".mirror-meta.yaml"
        assert metadata_file.exists()
        
        # Verify typical analog design files exist
        # This repo should have various design files
        design_files = []
        for pattern in ["*.v", "*.sv", "*.spice", "*.cir", "*.sch", "*.mag", "*.gds"]:
            design_files.extend(list(mirror_path.rglob(pattern)))
        
        assert len(design_files) > 0, "Should have analog design files"
        
        print(f"✅ Switch Matrix Mirror created successfully:")
        print(f"   Repository: {repo_url}")
        print(f"   Branch: {ref}")
        print(f"   Commit: {metadata.resolved_commit}")
        print(f"   Mirror path: {mirror_path}")
        print(f"   Design files found: {len(design_files)}")
    
    @pytest.mark.slow
    def test_repo_hash_consistency(self):
        """Test that repository hashes are consistent across calls."""
        test_urls = [
            "https://github.com/peterkinget/testing-project-template",
            "https://github.com/mosbiuschip/switch_matrix_gf180mcu_9t5v0",
            "git@github.com:example/repo.git",
            "https://gitlab.com/example/repo"
        ]
        
        for repo_url in test_urls:
            hash1 = ChecksumCalculator.generate_repo_hash(repo_url)
            hash2 = ChecksumCalculator.generate_repo_hash(repo_url)
            assert hash1 == hash2, f"Hash inconsistent for {repo_url}"
            
            # Test that different URLs produce different hashes
            for other_url in test_urls:
                if other_url != repo_url:
                    other_hash = self.mirror._generate_repo_hash(other_url)
                    assert hash1 != other_hash, f"Hash collision between {repo_url} and {other_url}"
    
    @pytest.mark.slow
    def test_update_mirror_real_repo(self):
        """Test updating an existing mirror with real repository."""
        repo_url = "https://github.com/peterkinget/testing-project-template"
        ref = "PK_PLL_modeling"
        
        # Create initial mirror
        initial_metadata = self.mirror.create_mirror(repo_url, ref)
        initial_commit = initial_metadata.resolved_commit
        
        # Update the mirror (should fetch latest changes)
        updated_metadata = self.mirror.update_mirror(repo_url, ref)
        
        # Verify metadata updated
        assert updated_metadata.repo_url == repo_url
        assert updated_metadata.current_ref == ref
        assert updated_metadata.resolved_commit == initial_commit  # Should be same for same ref
        assert updated_metadata.created_at == initial_metadata.created_at  # Preserved
        assert updated_metadata.updated_at >= initial_metadata.updated_at  # Should be newer or same
        
        # Verify mirror still exists and is valid
        mirror_path = self.mirror.get_mirror_path(repo_url)
        assert mirror_path.exists()
        assert (mirror_path / ".git").exists()
        
        print(f"✅ Mirror updated successfully:")
        print(f"   Initial commit: {initial_commit}")
        print(f"   Updated commit: {updated_metadata.resolved_commit}")
        print(f"   Created: {initial_metadata.created_at}")
        print(f"   Updated: {updated_metadata.updated_at}")
    
    @pytest.mark.slow
    def test_mirror_with_invalid_ref(self):
        """Test error handling with invalid git reference."""
        repo_url = "https://github.com/peterkinget/testing-project-template"
        invalid_ref = "nonexistent-branch-12345"
        
        with pytest.raises(ValueError, match=f"Reference '{invalid_ref}' not found"):
            self.mirror.create_mirror(repo_url, invalid_ref)
        
        # Verify no mirror was created
        assert not self.mirror.mirror_exists(repo_url)
    
    @pytest.mark.slow
    def test_list_multiple_mirrors(self):
        """Test listing multiple real mirrors."""
        test_repos = [
            ("https://github.com/peterkinget/testing-project-template", "PK_PLL_modeling"),
            ("https://github.com/mosbiuschip/switch_matrix_gf180mcu_9t5v0", "main")
        ]
        
        created_mirrors = []
        for repo_url, ref in test_repos:
            metadata = self.mirror.create_mirror(repo_url, ref)
            created_mirrors.append(metadata)
        
        # List all mirrors
        mirrors = self.mirror.list_mirrors()
        
        # Verify all mirrors are listed
        assert len(mirrors) == len(test_repos)
        
        for repo_url, _ in test_repos:
            assert repo_url in mirrors
            metadata = mirrors[repo_url]
            assert metadata.repo_url == repo_url
            assert len(metadata.resolved_commit) == 40
        
        print(f"✅ Listed {len(mirrors)} mirrors successfully:")
        for repo_url, metadata in mirrors.items():
            print(f"   {repo_url} -> {metadata.current_ref} ({metadata.resolved_commit[:8]})")
    
    @pytest.mark.slow
    def test_cleanup_and_remove_mirrors(self):
        """Test cleanup and removal of real mirrors."""
        repo_url = "https://github.com/peterkinget/testing-project-template"
        ref = "PK_PLL_modeling"
        
        # Create mirror
        self.mirror.create_mirror(repo_url, ref)
        assert self.mirror.mirror_exists(repo_url)
        
        # Remove mirror
        removed = self.mirror.remove_mirror(repo_url)
        assert removed is True
        assert not self.mirror.mirror_exists(repo_url)
        
        # Try to remove again (should return False)
        removed_again = self.mirror.remove_mirror(repo_url)
        assert removed_again is False
        
        print(f"✅ Mirror cleanup successful for {repo_url}")


def test_analog_hub_yaml_config():
    """Test that we can load the analog-hub.yaml configuration."""
    config_path = Path("analog-hub.yaml")
    if not config_path.exists():
        pytest.skip("analog-hub.yaml not found")
    
    config = AnalogHubConfig.from_yaml(config_path)
    
    # Verify expected repositories are configured
    assert "model_pll" in config.imports
    assert "switch_matrix_gf180mcu_9t5v0" in config.imports
    
    # Verify repository details
    pll_spec = config.imports["model_pll"]
    assert pll_spec.repo == "https://github.com/peterkinget/testing-project-template"
    assert pll_spec.ref == "PK_PLL_modeling"
    assert pll_spec.source_path == "designs/libs/model_pll"
    
    switch_spec = config.imports["switch_matrix_gf180mcu_9t5v0"]
    assert switch_spec.repo == "https://github.com/mosbiuschip/switch_matrix_gf180mcu_9t5v0"
    assert switch_spec.ref == "main"
    assert switch_spec.source_path == "."
    
    print(f"✅ Configuration loaded successfully:")
    print(f"   Library root: {config.library_root}")
    print(f"   Imports: {list(config.imports.keys())}")