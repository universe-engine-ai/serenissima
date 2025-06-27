#!/usr/bin/env python3
"""
Claude Helper - Arsenale scaffolding for autonomous Claude Code interactions
Enables programmatic interaction with Claude Code CLI for autonomous actions
"""

import subprocess
import json
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime


class ClaudeHelper:
    """Interface for programmatic Claude Code interactions"""
    
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.getcwd()
        self.session_log = []
        
    def send_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message to Claude Code and get the response
        
        Args:
            message: The message/prompt to send
            context: Optional context about the current task
            
        Returns:
            Dict containing response, success status, and metadata
        """
        timestamp = datetime.now().isoformat()
        
        # Build the command
        cmd = [
            "claude",
            message,
            "--print",
            "--dangerously-skip-permissions",
            "--continue"
        ]
        
        try:
            # Execute claude command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=300  # 5 minute timeout
            )
            
            response = {
                "success": result.returncode == 0,
                "response": result.stdout if result.returncode == 0 else result.stderr,
                "timestamp": timestamp,
                "message": message,
                "context": context,
                "exit_code": result.returncode
            }
            
            # Log the interaction
            self.session_log.append(response)
            
            return response
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "response": "Command timed out after 5 minutes",
                "timestamp": timestamp,
                "message": message,
                "context": context,
                "exit_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "response": f"Error executing command: {str(e)}",
                "timestamp": timestamp,
                "message": message,
                "context": context,
                "exit_code": -1
            }
    
    def save_session_log(self, filepath: str):
        """Save the session log to a JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.session_log, f, indent=2)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session"""
        return {
            "total_interactions": len(self.session_log),
            "successful": sum(1 for log in self.session_log if log["success"]),
            "failed": sum(1 for log in self.session_log if not log["success"]),
            "session_start": self.session_log[0]["timestamp"] if self.session_log else None,
            "session_end": self.session_log[-1]["timestamp"] if self.session_log else None
        }


def main():
    """CLI interface for testing the helper"""
    if len(sys.argv) < 2:
        print("Usage: python claude_helper.py 'your message here'")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    helper = ClaudeHelper()
    
    print(f"Sending message to Claude: {message}")
    print("-" * 50)
    
    response = helper.send_message(message)
    
    if response["success"]:
        print(response["response"])
    else:
        print(f"Error: {response['response']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()