#!/usr/bin/env python3
"""
Check the size of Arsenale prompts to debug length issues
"""

import os
from pathlib import Path

def check_prompt_files():
    """Check size of all prompt-related files"""
    arsenale_dir = Path(__file__).parent
    
    print("=== Arsenale Prompt Size Analysis ===\n")
    
    # Check base prompt files
    print("Base Prompt Files:")
    prompts_dir = arsenale_dir / "prompts"
    for prompt_file in prompts_dir.glob("*.md"):
        size = prompt_file.stat().st_size
        print(f"  {prompt_file.name}: {size:,} bytes ({size/1024:.1f} KB)")
    
    # Check context files
    print("\nContext Files:")
    context_dir = arsenale_dir / "context"
    if context_dir.exists():
        for context_file in context_dir.glob("*"):
            if context_file.is_file():
                size = context_file.stat().st_size
                print(f"  {context_file.name}: {size:,} bytes ({size/1024:.1f} KB)")
    
    # Check temp prompt files
    print("\nTemp Prompt Files (last 5):")
    logs_dir = arsenale_dir / "logs"
    temp_prompts = sorted(logs_dir.glob("temp_prompt_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    for temp_file in temp_prompts:
        size = temp_file.stat().st_size
        print(f"  {temp_file.name}: {size:,} bytes ({size/1024:.1f} KB)")
        
        # Show first few lines of most recent temp file
        if temp_file == temp_prompts[0] and temp_file.exists():
            print(f"\n  First 500 chars of {temp_file.name}:")
            with open(temp_file, 'r') as f:
                content = f.read(500)
                print(f"  {content}...")
    
    # Estimate token count (rough approximation: ~4 chars per token)
    print("\n=== Token Estimates (rough) ===")
    print("Note: Claude's context window is typically 100k-200k tokens")
    for prompt_file in prompts_dir.glob("*.md"):
        size = prompt_file.stat().st_size
        estimated_tokens = size / 4
        print(f"  {prompt_file.name}: ~{estimated_tokens:,.0f} tokens")

if __name__ == "__main__":
    check_prompt_files()