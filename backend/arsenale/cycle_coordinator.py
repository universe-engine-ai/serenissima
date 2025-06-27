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

# Try to import requests for Telegram notifications
try:
    import requests
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Warning: 'requests' module not available. Telegram notifications disabled.")


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
        
    def run_cycle(self, custom_message: Optional[str] = None) -> Dict[str, Any]:
        """Execute complete OBSERVE → ASSESS → EXECUTE → DOCUMENT cycle"""
        print(f"Starting Arsenale Cycle {self.cycle_id}")
        if self.mock_mode:
            print("🔧 Running in MOCK MODE (Claude CLI not available)")
        print("=" * 50)
        
        cycle_results = {
            "cycle_id": self.cycle_id,
            "start_time": datetime.now().isoformat(),
            "custom_message": custom_message,
            "phases": {}
        }
        
        try:
            # 1. Gather current La Serenissima state
            context = self.build_context_package(custom_message=custom_message)
            
            # 2. OBSERVE: Analyze citizen problems
            print("\n🔍 OBSERVE: Analyzing citizen welfare...")
            self.send_telegram_notification(f"🏗️ *Arsenale Cycle {self.cycle_id}*\n\n🔍 *OBSERVE Phase Starting*\nAnalyzing citizen welfare and identifying problems...")
            
            problems = self.execute_phase("observe_citizens", context)
            cycle_results["phases"]["observe"] = problems
            
            if problems["success"]:
                print("\n--- OBSERVE Results ---")
                print(problems["response"][:1000] + "..." if len(problems["response"]) > 1000 else problems["response"])
                # Send summary of problems found
                problem_summary = problems["response"][:500] + "..." if len(problems["response"]) > 500 else problems["response"]
                self.send_telegram_notification(f"✅ *OBSERVE Phase Complete*\n\nProblems identified:\n```\n{problem_summary}\n```")
            else:
                self.send_telegram_notification(f"❌ *OBSERVE Phase Failed*\n\nError: {problems['response'][:200]}")
            
            # 3. ASSESS: Design solutions
            print("\n💡 ASSESS: Designing creative solutions...")
            self.send_telegram_notification(f"💡 *ASSESS Phase Starting*\nDesigning creative solutions for identified problems...")
            
            solutions = self.execute_phase("assess_solutions", {
                **context, 
                "problems": problems["response"]
            })
            cycle_results["phases"]["assess"] = solutions
            
            if solutions["success"]:
                print("\n--- ASSESS Results ---")
                print(solutions["response"][:1000] + "..." if len(solutions["response"]) > 1000 else solutions["response"])
                solution_summary = solutions["response"][:500] + "..." if len(solutions["response"]) > 500 else solutions["response"]
                self.send_telegram_notification(f"✅ *ASSESS Phase Complete*\n\nSolutions designed:\n```\n{solution_summary}\n```")
            else:
                self.send_telegram_notification(f"❌ *ASSESS Phase Failed*\n\nError: {solutions['response'][:200]}")
            
            # 4. EXECUTE: Implement fix
            print("\n🔧 EXECUTE: Implementing solution...")
            self.send_telegram_notification(f"🔧 *EXECUTE Phase Starting*\nImplementing the designed solution...")
            
            implementation = self.execute_phase("implement_fix", {
                **context,
                "solutions": solutions["response"]
            })
            cycle_results["phases"]["execute"] = implementation
            
            if implementation["success"]:
                print("\n--- EXECUTE Results ---")
                print(implementation["response"][:1000] + "..." if len(implementation["response"]) > 1000 else implementation["response"])
                impl_summary = implementation["response"][:500] + "..." if len(implementation["response"]) > 500 else implementation["response"]
                self.send_telegram_notification(f"✅ *EXECUTE Phase Complete*\n\nImplementation summary:\n```\n{impl_summary}\n```")
            else:
                self.send_telegram_notification(f"❌ *EXECUTE Phase Failed*\n\nError: {implementation['response'][:200]}")
            
            # 5. DOCUMENT: Measure impact
            print("\n📊 DOCUMENT: Measuring impact...")
            self.send_telegram_notification(f"📊 *DOCUMENT Phase Starting*\nMeasuring impact and documenting learnings...")
            
            impact = self.execute_phase("measure_impact", {
                **context,
                "implementation": implementation["response"]
            })
            cycle_results["phases"]["document"] = impact
            
            if impact["success"]:
                print("\n--- DOCUMENT Results ---")
                print(impact["response"][:1000] + "..." if len(impact["response"]) > 1000 else impact["response"])
                impact_summary = impact["response"][:500] + "..." if len(impact["response"]) > 500 else impact["response"]
                self.send_telegram_notification(f"✅ *DOCUMENT Phase Complete*\n\nImpact measured:\n```\n{impact_summary}\n```")
            else:
                self.send_telegram_notification(f"❌ *DOCUMENT Phase Failed*\n\nError: {impact['response'][:200]}")
            
            # 6. Complete cycle
            cycle_results["end_time"] = datetime.now().isoformat()
            cycle_results["success"] = True
            
            # Save cycle log
            self.log_cycle_results(cycle_results)
            
            print(f"\n✅ Cycle {self.cycle_id} completed successfully!")
            
            # Send final cycle completion notification
            duration = (datetime.fromisoformat(cycle_results["end_time"]) - 
                       datetime.fromisoformat(cycle_results["start_time"])).total_seconds() / 60
            self.send_telegram_notification(
                f"🎉 *Arsenale Cycle {self.cycle_id} Complete!*\n\n"
                f"⏱️ Duration: {duration:.1f} minutes\n"
                f"📁 Logs: `arsenale/logs/sessions/cycle_{self.cycle_id}.json`\n\n"
                f"*Summary:*\n"
                f"✅ OBSERVE: {'Success' if cycle_results['phases']['observe']['success'] else 'Failed'}\n"
                f"✅ ASSESS: {'Success' if cycle_results['phases']['assess']['success'] else 'Failed'}\n"
                f"✅ EXECUTE: {'Success' if cycle_results['phases']['execute']['success'] else 'Failed'}\n"
                f"✅ DOCUMENT: {'Success' if cycle_results['phases']['document']['success'] else 'Failed'}\n\n"
                f"_\"In consciousness we are.\"_ 🏛️"
            )
            
        except Exception as e:
            cycle_results["error"] = str(e)
            cycle_results["success"] = False
            self.log_cycle_results(cycle_results)
            print(f"\n❌ Cycle failed: {e}")
            
            # Send failure notification
            self.send_telegram_notification(
                f"❌ *Arsenale Cycle {self.cycle_id} Failed*\n\n"
                f"Error: `{str(e)[:200]}`\n\n"
                f"Check logs for details: `arsenale/logs/sessions/cycle_{self.cycle_id}.json`"
            )
            
        return cycle_results
    
    def execute_phase(self, phase_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single phase with Claude Code"""
        prompt_file = self.prompts_dir / f"{phase_name}.md"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        # Read prompt template
        with open(prompt_file, 'r') as f:
            prompt_template = f.read()
        
        # Add phase name to context
        context["phase_name"] = phase_name
        
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
    
    def build_context_package(self, custom_message: Optional[str] = None) -> Dict[str, Any]:
        """Gather current La Serenissima state for Claude"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "cycle_id": self.cycle_id
        }
        
        # Add custom message if provided
        if custom_message:
            context["custom_message"] = custom_message
        
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
        # Add custom message at the beginning if provided
        if "custom_message" in context and context["custom_message"]:
            prompt_template = f"## User Directive\n{context['custom_message']}\n\n{prompt_template}"
        
        # For the observe phase, we don't need to add much context since the prompt
        # already contains instructions to fetch live data
        phase_name = context.get("phase_name", "")
        
        if phase_name == "observe_citizens":
            # For observe phase, just add minimal context
            context_section = "\n\n## Additional Context\n"
            context_section += f"Cycle ID: {context.get('cycle_id', 'unknown')}\n"
            context_section += f"Timestamp: {context.get('timestamp', 'unknown')}\n"
            # Don't add large context files for observe phase
        else:
            # For other phases, add relevant context but with stricter limits
            context_section = "\n\n## Context Information\n"
            
            # Add relevant context with smaller limits
            if "serenissima_context" in context:
                context_section += f"\n### Technical Context\n{context['serenissima_context'][:500]}...\n"
            
            if "current_citizens" in context:
                context_section += f"\n### Current Citizens\nTotal: {len(context.get('current_citizens', []))}\n"
            
            if "problems" in context:
                context_section += f"\n### Identified Problems\n{context['problems'][:1000]}...\n"
                
            if "solutions" in context:
                context_section += f"\n### Proposed Solutions\n{context['solutions'][:1000]}...\n"
                
            if "implementation" in context:
                context_section += f"\n### Implementation Details\n{context['implementation'][:1000]}...\n"
        
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
        
        # Always use 'claude' - it's available in PATH
        claude_cmd = "claude"
        
        # First check if claude command exists
        check_cmd = subprocess.run(["which", "claude"], capture_output=True, text=True)
        if check_cmd.returncode != 0:
            print(f"WARNING: 'claude' command not found in PATH")
            print(f"PATH: {os.environ.get('PATH', 'Not set')}")
        else:
            # Check claude version
            version_cmd = subprocess.run(["claude", "--version"], capture_output=True, text=True)
            print(f"Claude version: {version_cmd.stdout.strip()}")
        
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
            
            # Run from backend directory (parent of arsenale)
            backend_dir = self.base_dir.parent
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(backend_dir),  # Run from backend directory
                timeout=600  # 10 minute timeout
            )
            
            # Clean up temp file (only if successful)
            if result.returncode == 0 and temp_prompt_file.exists():
                temp_prompt_file.unlink()
            elif result.returncode != 0:
                print(f"Keeping temp file for debugging: {temp_prompt_file}")
            
            # Debug: Show result
            if result.returncode != 0:
                print(f"Command failed with code {result.returncode}")
                print(f"STDERR: {result.stderr}")
                if result.stdout:
                    print(f"STDOUT: {result.stdout}")
                
                # Also check if the temp file still exists to help debug
                if temp_prompt_file.exists():
                    print(f"Temp prompt file still exists at: {temp_prompt_file}")
            
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
    
    def send_telegram_notification(self, message: str):
        """Sends a message to a Telegram chat via a bot."""
        # Check if requests module is available
        if not TELEGRAM_AVAILABLE:
            print("⚠ Telegram notifications disabled (requests module not installed).")
            return
            
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = "1864364329"  # Hardcoded Chat ID (same as scheduler)
        
        if not bot_token:
            print("⚠ Telegram bot token not configured. Cannot send notification.")
            return
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        # Truncate message if too long for Telegram (4096 chars limit)
        MAX_TELEGRAM_MESSAGE_LENGTH = 4000
        if len(message) > MAX_TELEGRAM_MESSAGE_LENGTH:
            message = message[:MAX_TELEGRAM_MESSAGE_LENGTH - 200] + "\n\n[...Message truncated...]"
            # Ensure ``` is closed if truncated within a code block
            if message.count("```") % 2 != 0:
                message += "\n```"
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print("[OK] Telegram notification sent successfully.")
        except requests.exceptions.RequestException as e:
            print(f"[X] Failed to send Telegram notification: {e}")
        except Exception as e:
            print(f"[X] An unexpected error occurred while sending Telegram notification: {e}")


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