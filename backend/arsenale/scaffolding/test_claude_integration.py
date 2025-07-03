#!/usr/bin/env python3
"""
Test script for Claude Helper integration
Demonstrates how Arsenale can programmatically interact with Claude Code
"""

from claude_helper import ClaudeHelper
import json
from datetime import datetime


def test_basic_interaction():
    """Test basic message sending"""
    helper = ClaudeHelper()
    
    # Test a simple query
    response = helper.send_message(
        "What is the current status of La Serenissima's citizen count?",
        context={"task": "system_monitoring", "priority": "low"}
    )
    
    print("Basic Interaction Test:")
    print(f"Success: {response['success']}")
    print(f"Response preview: {response['response'][:200]}...")
    print()
    
    return response


def test_code_analysis():
    """Test code analysis capability"""
    helper = ClaudeHelper()
    
    response = helper.send_message(
        "Analyze the citizen activity system and identify any performance bottlenecks",
        context={"task": "code_optimization", "priority": "medium"}
    )
    
    print("Code Analysis Test:")
    print(f"Success: {response['success']}")
    print()
    
    return response


def test_autonomous_initiative():
    """Test autonomous initiative proposal"""
    helper = ClaudeHelper()
    
    response = helper.send_message(
        "Based on recent AI citizen behaviors, suggest a new activity type that would enhance cultural transmission",
        context={"task": "content_generation", "priority": "high", "autonomous": True}
    )
    
    print("Autonomous Initiative Test:")
    print(f"Success: {response['success']}")
    print()
    
    return response


def main():
    """Run all tests and save results"""
    print("Arsenale Claude Helper Integration Tests")
    print("=" * 50)
    print()
    
    # Run tests
    results = {
        "test_run": datetime.now().isoformat(),
        "tests": {
            "basic_interaction": test_basic_interaction(),
            "code_analysis": test_code_analysis(),
            "autonomous_initiative": test_autonomous_initiative()
        }
    }
    
    # Save results
    log_file = f"arsenale/logs/test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nTest results saved to: {log_file}")
    
    # Generate summary
    helper = ClaudeHelper()
    helper.session_log = [results["tests"][key] for key in results["tests"]]
    summary = helper.get_session_summary()
    
    print("\nSession Summary:")
    print(f"Total interactions: {summary['total_interactions']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")


if __name__ == "__main__":
    main()