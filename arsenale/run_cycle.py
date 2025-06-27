#!/usr/bin/env python3
"""
Arsenale Cycle Runner
Simple launcher for running autonomous improvement cycles
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cycle_coordinator import ArsenaleCycle


def main():
    """Run a single Arsenale cycle"""
    # Check for --mock flag
    mock_mode = "--mock" in sys.argv
    
    print("🏗️  Arsenale v1: Prompt-Driven Creative Autonomy")
    print("=" * 60)
    
    if mock_mode:
        print("🔧 Running in MOCK MODE for demonstration")
        print("   (Use when Claude CLI is not available)")
    else:
        print("Starting autonomous improvement cycle for La Serenissima...")
    print()
    
    cycle = ArsenaleCycle(mock_mode=mock_mode)
    results = cycle.run_cycle()
    
    print("\n" + "=" * 60)
    if results["success"]:
        print("✅ Cycle completed successfully!")
        print(f"📁 Detailed logs: arsenale/logs/sessions/cycle_{results['cycle_id']}.json")
        if mock_mode:
            print("\n📝 Note: This was a mock demonstration.")
            print("   To run with real Claude, ensure Claude CLI is installed and remove --mock flag.")
    else:
        print("❌ Cycle encountered errors. Check logs for details.")


if __name__ == "__main__":
    main()