#!/usr/bin/env python3
"""
Sparse Checkout Prototype for analog-hub

Test script to validate GitPython sparse checkout approach for selective library extraction.
Target: Extract model_pll from peterkinget/testing-project-template
"""

import git
import tempfile
import shutil
import time
from pathlib import Path
import sys
import os

# Add parent directory to path to import ams_compose modules if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

def sparse_checkout_library(repo_url: str, ref: str, source_path: str, dest_path: str):
    """
    Extract specific library path from remote repo using sparse checkout
    
    Args:
        repo_url: Git repository URL
        ref: Git reference (branch, tag, commit)
        source_path: Path within repo to extract
        dest_path: Local destination path
    
    Returns:
        dict: Results with timing, status, and file count
    """
    start_time = time.time()
    result = {
        'success': False,
        'duration': 0,
        'files_copied': 0,
        'error': None,
        'temp_dir_size': 0
    }
    
    temp_dir = None
    try:
        print(f"🚀 Starting sparse checkout...")
        print(f"   Repository: {repo_url}")
        print(f"   Reference: {ref}")
        print(f"   Source Path: {source_path}")
        print(f"   Destination: {dest_path}")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='analog_hub_sparse_')
        print(f"   Temp Directory: {temp_dir}")
        
        # Clone repository normally first
        print("📦 Cloning repository...")
        repo = git.Repo.clone_from(url=repo_url, to_path=temp_dir)
        
        # Checkout to specified reference
        print(f"🌿 Checking out reference: {ref}")
        repo.git.checkout(ref)
        
        # Enable sparse checkout using git command directly
        print("🔧 Enabling sparse checkout...")
        repo.git.config('core.sparseCheckout', 'true')
        
        # Configure sparse checkout for specific path
        sparse_checkout_file = Path(temp_dir) / '.git' / 'info' / 'sparse-checkout'
        print(f"📝 Configuring sparse checkout: {sparse_checkout_file}")
        
        # Ensure the info directory exists
        sparse_checkout_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sparse_checkout_file, 'w') as f:
            f.write(f"{source_path}\n")
        
        # Apply sparse checkout by reading the tree
        print("🔄 Applying sparse checkout...")
        repo.git.read_tree('-m', '-u', 'HEAD')
        
        # Check if source path exists in repo
        source_full_path = Path(temp_dir) / source_path
        if not source_full_path.exists():
            raise FileNotFoundError(f"Source path '{source_path}' not found in repository")
        
        # Calculate temp directory size (for efficiency measurement)
        def get_dir_size(path):
            total = 0
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
            return total
        
        result['temp_dir_size'] = get_dir_size(temp_dir)
        print(f"📊 Temporary directory size: {result['temp_dir_size']:,} bytes")
        
        # Create destination directory
        dest_full_path = Path(dest_path)
        dest_full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing destination if it exists
        if dest_full_path.exists():
            print(f"🗑️  Removing existing destination: {dest_full_path}")
            shutil.rmtree(dest_full_path)
        
        # Copy source to destination
        print(f"📋 Copying {source_full_path} to {dest_full_path}")
        shutil.copytree(source_full_path, dest_full_path)
        
        # Count copied files
        def count_files(path):
            count = 0
            for entry in os.scandir(path):
                if entry.is_file():
                    count += 1
                elif entry.is_dir():
                    count += count_files(entry.path)
            return count
        
        result['files_copied'] = count_files(dest_full_path)
        result['success'] = True
        
        print(f"✅ Success! Copied {result['files_copied']} files")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ Error: {e}")
        
    finally:
        # Cleanup temporary directory
        if temp_dir and Path(temp_dir).exists():
            print(f"🧹 Cleaning up: {temp_dir}")
            shutil.rmtree(temp_dir)
        
        result['duration'] = time.time() - start_time
        print(f"⏱️  Total duration: {result['duration']:.2f} seconds")
    
    return result

def full_clone_comparison(repo_url: str, ref: str):
    """
    Compare sparse checkout performance against full clone
    """
    print("\n🔍 Performance Comparison: Full Clone")
    start_time = time.time()
    temp_dir = None
    
    try:
        temp_dir = tempfile.mkdtemp(prefix='analog_hub_full_')
        print(f"   Temp Directory: {temp_dir}")
        
        # Full clone
        repo = git.Repo.clone_from(url=repo_url, to_path=temp_dir)
        repo.git.checkout(ref)
        
        # Calculate directory size
        def get_dir_size(path):
            total = 0
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
            return total
        
        full_size = get_dir_size(temp_dir)
        duration = time.time() - start_time
        
        print(f"📊 Full clone size: {full_size:,} bytes")
        print(f"⏱️  Full clone duration: {duration:.2f} seconds")
        
        return {'size': full_size, 'duration': duration}
        
    except Exception as e:
        print(f"❌ Full clone error: {e}")
        return None
        
    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)

def main():
    """Main test function"""
    print("🧪 analog-hub Sparse Checkout Prototype Test")
    print("=" * 50)
    
    # Test parameters
    repo_url = "https://github.com/peterkinget/testing-project-template"
    ref = "PK_PLL_modeling"
    source_path = "designs/libs/model_pll"
    dest_path = "designs/libs/model_pll"
    
    # Test sparse checkout
    result = sparse_checkout_library(repo_url, ref, source_path, dest_path)
    
    # Test full clone for comparison
    full_result = full_clone_comparison(repo_url, ref)
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 50)
    print(f"Sparse Checkout Success: {result['success']}")
    if result['success']:
        print(f"Files Copied: {result['files_copied']}")
        print(f"Duration: {result['duration']:.2f} seconds")
        print(f"Temp Size: {result['temp_dir_size']:,} bytes")
        
        if full_result:
            size_ratio = result['temp_dir_size'] / full_result['size'] * 100
            time_ratio = result['duration'] / full_result['duration'] * 100
            print(f"\nEfficiency vs Full Clone:")
            print(f"Size: {size_ratio:.1f}% of full clone")
            print(f"Time: {time_ratio:.1f}% of full clone")
    else:
        print(f"Error: {result['error']}")
    
    # Check if destination exists
    dest_check = Path(dest_path)
    if dest_check.exists():
        print(f"\n✅ Destination created: {dest_check.absolute()}")
        print(f"   Contents: {list(dest_check.iterdir())}")
    else:
        print(f"\n❌ Destination not found: {dest_check.absolute()}")

if __name__ == "__main__":
    main()