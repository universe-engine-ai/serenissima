#!/usr/bin/env python3
"""
Arsenale v1: Minimal Cycle Coordinator
Orchestrates prompt-driven creative autonomy for La Serenissima
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class ArsenaleCycle:
    """Simple orchestrator that runs prompt sequence"""
    
    def __init__(self, base_dir: str = None, mock_mode: bool = False):
        self.base_dir = Path(base_dir or os.path.dirname(os.path.abspath(__file__)))
        self.prompts_dir = self.base_dir / "prompts"
        self.context_dir = self.base_dir / "context"
        self.logs_dir = self.base_dir / "logs"
        self.cycle_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.mock_mode = mock_mode
        
        if mock_mode:
            from mock_claude_responses import MOCK_RESPONSES
            self.mock_responses = MOCK_RESPONSES
        
    def run_cycle(self) -> Dict[str, Any]:
        """Execute complete OBSERVE → ASSESS → EXECUTE → DOCUMENT cycle"""
        print(f"Starting Arsenale Cycle {self.cycle_id}")
        if self.mock_mode:
            print("🔧 Running in MOCK MODE (Claude CLI not available)")
        print("=" * 50)
        
        cycle_results = {
            "cycle_id": self.cycle_id,
            "start_time": datetime.now().isoformat(),
            "phases": {}
        }
        
        try:
            # 1. Gather current La Serenissima state
            context = self.build_context_package()
            
            # 2. OBSERVE: Analyze citizen problems
            print("\n🔍 OBSERVE: Analyzing citizen welfare...")
            problems = self.execute_phase("observe_citizens", context)
            cycle_results["phases"]["observe"] = problems
            if problems["success"]:
                print("\n--- OBSERVE Results ---")
                print(problems["response"][:1000] + "..." if len(problems["response"]) > 1000 else problems["response"])
            
            # 3. ASSESS: Design solutions
            print("\n💡 ASSESS: Designing creative solutions...")
            solutions = self.execute_phase("assess_solutions", {
                **context, 
                "problems": problems["response"]
            })
            cycle_results["phases"]["assess"] = solutions
            if solutions["success"]:
                print("\n--- ASSESS Results ---")
                print(solutions["response"][:1000] + "..." if len(solutions["response"]) > 1000 else solutions["response"])
            
            # 4. EXECUTE: Implement fix
            print("\n🔧 EXECUTE: Implementing solution...")
            implementation = self.execute_phase("implement_fix", {
                **context,
                "solutions": solutions["response"]
            })
            cycle_results["phases"]["execute"] = implementation
            if implementation["success"]:
                print("\n--- EXECUTE Results ---")
                print(implementation["response"][:1000] + "..." if len(implementation["response"]) > 1000 else implementation["response"])
            
            # 5. DOCUMENT: Measure impact
            print("\n📊 DOCUMENT: Measuring impact...")
            impact = self.execute_phase("measure_impact", {
                **context,
                "implementation": implementation["response"]
            })
            cycle_results["phases"]["document"] = impact
            if impact["success"]:
                print("\n--- DOCUMENT Results ---")
                print(impact["response"][:1000] + "..." if len(impact["response"]) > 1000 else impact["response"])
            
            # 6. Complete cycle
            cycle_results["end_time"] = datetime.now().isoformat()
            cycle_results["success"] = True
            
            # Save cycle log
            self.log_cycle_results(cycle_results)
            
            print(f"\n✅ Cycle {self.cycle_id} completed successfully!")
            
        except Exception as e:
            cycle_results["error"] = str(e)
            cycle_results["success"] = False
            self.log_cycle_results(cycle_results)
            print(f"\n❌ Cycle failed: {e}")
            
        return cycle_results
    
    def execute_phase(self, phase_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single phase with Claude Code"""
        prompt_file = self.prompts_dir / f"{phase_name}.md"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        # Read prompt template
        with open(prompt_file, 'r') as f:
            prompt_template = f.read()
        
        # Build full prompt with context
        full_prompt = self._build_prompt_with_context(prompt_template, context)
        
        # Execute with Claude Code or use mock
        if self.mock_mode:
            result = self._get_mock_response(phase_name)
        else:
            result = self._execute_claude_command(full_prompt)
        
        return {
            "phase": phase_name,
            "timestamp": datetime.now().isoformat(),
            "success": result["success"],
            "response": result["response"]
        }
    
    def build_context_package(self) -> Dict[str, Any]:
        """Gather current La Serenissima state for Claude"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "cycle_id": self.cycle_id
        }
        
        # Load static context files
        context_files = {
            "serenissima_context": "serenissima_context.md",
            "airtable_schema": "airtable_schema.md"
        }
        
        for key, filename in context_files.items():
            filepath = self.context_dir / filename
            if filepath.exists():
                with open(filepath, 'r') as f:
                    context[key] = f.read()
        
        # Load dynamic citizen data if available
        citizens_file = self.context_dir / "current_citizens.json"
        if citizens_file.exists():
            with open(citizens_file, 'r') as f:
                context["current_citizens"] = json.load(f)
        
        return context
    
    def _build_prompt_with_context(self, prompt_template: str, context: Dict[str, Any]) -> str:
        """Combine prompt template with context information"""
        context_section = "\n\n## Context Information\n"
        
        # Add relevant context
        if "serenissima_context" in context:
            context_section += f"\n### Technical Context\n{context['serenissima_context'][:1000]}...\n"
        
        if "current_citizens" in context:
            context_section += f"\n### Current Citizens\nTotal: {len(context.get('current_citizens', []))}\n"
        
        if "problems" in context:
            context_section += f"\n### Identified Problems\n{context['problems'][:2000]}...\n"
            
        if "solutions" in context:
            context_section += f"\n### Proposed Solutions\n{context['solutions'][:2000]}...\n"
            
        if "implementation" in context:
            context_section += f"\n### Implementation Details\n{context['implementation'][:2000]}...\n"
        
        return prompt_template + context_section
    
    def _get_mock_response(self, phase_name: str) -> Dict[str, Any]:
        """Get mock response for testing"""
        import time
        time.sleep(1)  # Simulate processing time
        
        response = self.mock_responses.get(phase_name, "Mock response not found")
        return {
            "success": True,
            "response": response,
            "exit_code": 0
        }
    
    def _execute_claude_command(self, prompt: str) -> Dict[str, Any]:
        """Execute Claude Code command and capture response"""
        # Save prompt to temporary file (handles complex prompts better)
        # Use phase-specific filename to avoid conflicts
        import random
        temp_id = f"{self.cycle_id}_{random.randint(1000, 9999)}"
        temp_prompt_file = self.logs_dir / f"temp_prompt_{temp_id}.md"
        with open(temp_prompt_file, 'w') as f:
            f.write(prompt)
        
        # Use claude.exe on Windows
        import platform
        claude_cmd = "claude.exe" if platform.system() == "Windows" else "claude"
        
        cmd = [
            claude_cmd,
            f"@{temp_prompt_file}",
            "--print",
            "--dangerously-skip-permissions",
            "--continue"
        ]
        
        try:
            # Debug: Print command being executed
            print(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.base_dir.parent),  # Run from project root
                timeout=600,  # 10 minute timeout
                shell=True if platform.system() == "Windows" else False
            )
            
            # Clean up temp file
            if temp_prompt_file.exists():
                temp_prompt_file.unlink()
            
            # Debug: Show result
            if result.returncode != 0:
                print(f"Command failed with code {result.returncode}")
                print(f"STDERR: {result.stderr[:500]}")
            
            return {
                "success": result.returncode == 0,
                "response": result.stdout if result.returncode == 0 else result.stderr,
                "exit_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            if temp_prompt_file.exists():
                temp_prompt_file.unlink()
            return {
                "success": False,
                "response": "Command timed out after 10 minutes"
            }
        except Exception as e:
            if temp_prompt_file.exists():
                temp_prompt_file.unlink()
            return {
                "success": False,
                "response": f"Error executing command: {str(e)} (Command: {' '.join(cmd)})"
            }
    
    def log_cycle_results(self, results: Dict[str, Any]):
        """Save cycle results to logs"""
        # Append to cycles log
        cycles_log = self.logs_dir / "cycles.jsonl"
        with open(cycles_log, 'a') as f:
            f.write(json.dumps(results) + '\n')
        
        # Save detailed session log
        session_file = self.logs_dir / "sessions" / f"cycle_{self.cycle_id}.json"
        with open(session_file, 'w') as f:
            json.dump(results, f, indent=2)


def main():
    """Run a single Arsenale cycle"""
    import sys
    
    # Check for --mock flag
    mock_mode = "--mock" in sys.argv
    
    cycle = ArsenaleCycle(mock_mode=mock_mode)
    results = cycle.run_cycle()
    
    if results["success"]:
        print("\nCycle completed! Check logs for details.")
    else:
        print(f"\nCycle failed: {results.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()