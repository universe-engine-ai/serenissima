#!/usr/bin/env python3
"""
Simple test to check Scientisti citizens and activities
"""

import os
import sys
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Try to import and run a simple test
    print("🔬 La Serenissima - Scientisti System Test")
    print("=" * 50)
    
    # Check if we can import the required modules
    print("\n✅ Checking imports...")
    
    try:
        from engine.activity_creators import (
            try_create_research_investigation_activity
        )
        print("  ✓ Successfully imported research investigation activity creator")
    except Exception as e:
        print(f"  ✗ Failed to import activity creator: {e}")
    
    try:
        from engine.utils.scientisti_claude_helper import ScientistiClaudeHelper
        print("  ✓ Successfully imported Scientisti Claude Helper")
    except Exception as e:
        print(f"  ✗ Failed to import Claude helper: {e}")
    
    try:
        from engine.handlers.scientisti import _try_process_weighted_scientisti_work
        print("  ✓ Successfully imported Scientisti work handler")
    except Exception as e:
        print(f"  ✗ Failed to import work handler: {e}")
    
    # Check for environment variables
    print("\n✅ Checking environment...")
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    kinos_key = os.getenv("KINOS_API_KEY")
    
    print(f"  Airtable API Key: {'✓ Set' if api_key else '✗ Not set'}")
    print(f"  Airtable Base ID: {'✓ Set' if base_id else '✗ Not set'}")
    print(f"  KinOS API Key: {'✓ Set' if kinos_key else '✗ Not set'}")
    
    # Test Claude helper functionality
    print("\n✅ Testing Claude Helper...")
    try:
        helper = ScientistiClaudeHelper()
        print(f"  ✓ Claude helper initialized")
        print(f"  Working directory: {helper.working_dir}")
        
        # Check if Claude is available
        claude_paths = ["/usr/local/bin/claude", "/opt/homebrew/bin/claude", "claude"]
        claude_found = False
        for path in claude_paths:
            try:
                import subprocess
                result = subprocess.run([path, "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ Claude found at: {path}")
                    claude_found = True
                    break
            except:
                continue
        
        if not claude_found:
            print("  ✗ Claude not found in PATH")
        
    except Exception as e:
        print(f"  ✗ Error testing Claude helper: {e}")
    
    # Test backend/CLAUDE.md exists
    print("\n✅ Checking CLAUDE.md guidance...")
    claude_md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CLAUDE.md")
    if os.path.exists(claude_md_path):
        print(f"  ✓ CLAUDE.md exists at: {claude_md_path}")
        with open(claude_md_path, 'r') as f:
            lines = f.readlines()
            print(f"  ✓ File has {len(lines)} lines")
            if len(lines) > 10:
                print(f"  ✓ Contains guidance for Scientisti research")
    else:
        print(f"  ✗ CLAUDE.md not found at: {claude_md_path}")
    
    print("\n" + "=" * 50)
    print("✅ Test complete!")
    print("\n💡 To run a full test with real data:")
    print("   python backend/scripts/test_scientisti_activities.py --activity research --monitor")
    
except Exception as e:
    print(f"\n❌ Error during test: {e}")
    import traceback
    traceback.print_exc()