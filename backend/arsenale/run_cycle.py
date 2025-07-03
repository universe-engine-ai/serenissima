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
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Arsenale autonomous improvement cycle')
    parser.add_argument('message', nargs='?', default=None, 
                       help='Optional message to guide Arsenale (e.g., "Focus on fixing hunger crisis")')
    parser.add_argument('--mock', action='store_true', 
                       help='Run in mock mode for demonstration')
    
    args = parser.parse_args()
    
    print("🏗️  Arsenale v1: Prompt-Driven Creative Autonomy")
    print("=" * 60)
    
    if args.mock:
        print("🔧 Running in MOCK MODE for demonstration")
        print("   (Use when Claude CLI is not available)")
    else:
        print("Starting autonomous improvement cycle for La Serenissima...")
    
    if args.message:
        print(f"\n📋 Custom directive: {args.message}")
    print()
    
    cycle = ArsenaleCycle(mock_mode=args.mock)
    results = cycle.run_cycle(custom_message=args.message)
    
    print("\n" + "=" * 60)
    if results["success"]:
        print("✅ Cycle completed successfully!")
        print(f"📁 Detailed logs: arsenale/logs/sessions/cycle_{results['cycle_id']}.json")
        if args.mock:
            print("\n📝 Note: This was a mock demonstration.")
            print("   To run with real Claude, ensure Claude CLI is installed and remove --mock flag.")
    else:
        print("❌ Cycle encountered errors. Check logs for details.")


if __name__ == "__main__":
    main()