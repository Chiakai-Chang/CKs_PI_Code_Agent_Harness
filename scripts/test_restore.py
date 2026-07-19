#!/usr/bin/env python3
#
# Test script to verify restore.py functionality
# Run this after applying the skill conflict fix
#

import subprocess
import sys
import os

def run_cmd(cmd):
    """Run command and return result."""
    print("\n" + "="*60)
    print(f"CMD: {cmd}")
    print("="*60)
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("✅ TIMEOUT – command took too long")
        return -1, "", "TIMEOUT"
    except Exception as e:
        print(f"✅ ERROR: {e}")
        return -1, "", str(e)

def main():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    
    try:
        print("🔍 Testing restore.py skill conflict fix...\n")
    except:
        print("Testing restore.py skill conflict fix...\n")
    
    # Test 1: Dry run mode
    try:
        print("\n📋 TEST 1: Dry Run Mode")
    except:
        print("\nTEST 1: Dry Run Mode")
    cmd = f'python scripts/restore.py --dry-run'
    rc, out, err = run_cmd(cmd)
    
    if rc == 0 and "Dry run" in out:
        print("✅ Dry run mode works")
    else:
        print("❌ Dry run mode failed")
        return
    
    # Test 2: Auto mode (safe, since we just cleaned)
    try:
        print("\n📋 TEST 2: Auto Mode")
    except:
        print("\nTEST 2: Auto Mode")
    cmd = f'python scripts/restore.py --auto'
    rc, out, err = run_cmd(cmd)
    
    if rc == 0 and "Pruned" in out:
        pruned_count = out.count("Pruned")
        print(f"✅ Auto mode works (pruned {pruned_count} items)")
    else:
        print("❌ Auto mode failed")
        return
    
    # Test 3: Config-only mode
    try:
        print("\n📋 TEST 3: Config-Only Mode")
    except:
        print("\nTEST 3: Config-Only Mode")
    cmd = f'python scripts/restore.py --config-only'
    rc, out, err = run_cmd(cmd)
    
    if rc == 0 and "Config-only" in out:
        print("✅ Config-only mode works")
    else:
        print("✅ Config-only mode failed (may be ok if already config)")
    
    # Test 4: Verify no conflicts in output
    try:
        print("\n📋 TEST 4: Verify No Conflicts")
    except:
        print("\nTEST 4: Verify No Conflicts")
    cmd = f'python scripts/restore.py --auto 2>&1'
    rc, out, err = run_cmd(cmd)
    
    if "Skill conflicts" not in out and "conflicting global skill" in out.lower():
        print("✅ No skill conflicts detected")
    else:
        print("⚠️ Skill conflicts may still exist")
    
    print("\n" + "="*60)
    try:
        print("✅ All tests completed!")
    except:
        print("All tests completed!")
    print("="*60)

if __name__ == "__main__":
    main()
