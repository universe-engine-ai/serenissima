#!/usr/bin/env python3
"""
Test Claude command availability
"""

import subprocess
import platform
import os

def test_claude_commands():
    """Test various ways to call Claude"""
    
    # Commands to try
    commands_to_test = [
        ["claude", "--version"],
        ["claude.exe", "--version"],
        ["npx", "claude", "--version"],
        ["npm", "run", "claude", "--", "--version"]
    ]
    
    if platform.system() == "Windows":
        # Windows specific paths
        commands_to_test.extend([
            ["C:\\Program Files\\Claude\\claude.exe", "--version"],
            ["C:\\Users\\reyno\\AppData\\Local\\Programs\\claude\\claude.exe", "--version"],
            ["%LOCALAPPDATA%\\Programs\\claude\\claude.exe", "--version"]
        ])
    
    print("Testing Claude command availability...")
    print("=" * 50)
    
    for cmd in commands_to_test:
        try:
            print(f"\nTrying: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True if platform.system() == "Windows" else False,
                timeout=5
            )
            
            if result.returncode == 0:
                print(f"✅ SUCCESS!")
                print(f"Output: {result.stdout[:100]}")
                return cmd[0]  # Return the working command
            else:
                print(f"❌ Failed (code {result.returncode})")
                if result.stderr:
                    print(f"Error: {result.stderr[:100]}")
                    
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Could not find a working Claude command.")
    print("\nPlease ensure Claude is installed and accessible.")
    print("You may need to:")
    print("1. Add Claude to your PATH")
    print("2. Use the full path to claude.exe")
    print("3. Install Claude globally: npm install -g @anthropic-ai/claude-cli")
    
    return None

if __name__ == "__main__":
    working_cmd = test_claude_commands()
    if working_cmd:
        print(f"\n✅ Found working command: {working_cmd}")
        print("\nYou should update cycle_coordinator.py to use this command.")