#!/usr/bin/env python3
"""
Test Arsenale mock cycle
"""

import subprocess
import sys
import json
from pathlib import Path

def test_mock_cycle():
    """Run a mock cycle and verify it works"""
    print("Testing Arsenale Mock Cycle")
    print("=" * 50)
    
    # Run mock cycle
    result = subprocess.run(
        [sys.executable, "run_cycle.py", "--mock"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    print("Exit code:", result.returncode)
    print("\nOutput:")
    print(result.stdout)
    
    if result.stderr:
        print("\nErrors:")
        print(result.stderr)
    
    # Check if cycle completed
    if "Cycle completed successfully!" in result.stdout:
        print("\n✅ Mock cycle ran successfully!")
        
        # Find the log file
        import re
        match = re.search(r'cycle_(\d+_\d+)\.json', result.stdout)
        if match:
            cycle_id = match.group(1)
            log_file = Path(__file__).parent / "logs" / "sessions" / f"cycle_{cycle_id}.json"
            
            if log_file.exists():
                with open(log_file, 'r') as f:
                    cycle_data = json.load(f)
                
                print(f"\n📊 Cycle Summary:")
                print(f"- Phases completed: {len(cycle_data.get('phases', {}))}")
                for phase, data in cycle_data.get('phases', {}).items():
                    status = "✅" if data.get('success') else "❌"
                    print(f"  {status} {phase}")
                
                # Show a snippet of the observe phase
                if 'observe' in cycle_data.get('phases', {}):
                    response = cycle_data['phases']['observe'].get('response', '')
                    print(f"\n🔍 Sample from OBSERVE phase:")
                    print(response[:300] + "...")
            
    else:
        print("\n❌ Mock cycle failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(test_mock_cycle())