#!/usr/bin/env python3
"""
Scientisti Claude Helper - Enables AI scientists to consult with Claude Code
Allows Scientisti to ask questions about the computational reality they study
"""

import subprocess
import json
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import pytz

log = logging.getLogger(__name__)

# Venice timezone
VENICE_TIMEZONE = pytz.timezone('Europe/Rome')

class ScientistiClaudeHelper:
    """Interface for Scientisti to interact with Claude Code for research purposes"""
    
    def __init__(self, working_dir: Optional[str] = None):
        # Always run from backend/ directory for Scientisti
        self.working_dir = working_dir or os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/ directory
        self.session_log = []
        
    def ask_research_question(
        self, 
        question: str, 
        research_context: Dict[str, Any],
        citizen_username: str
    ) -> Dict[str, Any]:
        """
        Ask Claude Code a research question about the computational reality
        
        Args:
            question: The research question to ask
            research_context: Context about the current research (topic, observations, hypotheses)
            citizen_username: The Scientisti asking the question
            
        Returns:
            Dict containing response, success status, and metadata
        """
        timestamp = datetime.now(VENICE_TIMEZONE).isoformat()
        
        # Construct a research-focused prompt
        full_prompt = self._construct_research_prompt(question, research_context, citizen_username)
        
        # Build the command
        cmd = [
            "claude",
            full_prompt,
            "--print",
            "--dangerously-skip-permissions",
            "--continue"
        ]
        
        try:
            log.info(f"Scientisti {citizen_username} consulting Claude Code about: {question[:100]}...")
            
            # Execute claude command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=180  # 3 minute timeout for research questions
            )
            
            response = {
                "success": result.returncode == 0,
                "response": result.stdout if result.returncode == 0 else result.stderr,
                "timestamp": timestamp,
                "question": question,
                "research_context": research_context,
                "citizen": citizen_username,
                "exit_code": result.returncode
            }
            
            # Log the interaction
            self.session_log.append(response)
            
            if response["success"]:
                log.info(f"Successfully received research insights for {citizen_username}")
            else:
                log.error(f"Failed to get research insights for {citizen_username}: {response['response'][:200]}")
            
            return response
            
        except subprocess.TimeoutExpired:
            log.error(f"Claude Code timeout for {citizen_username}'s research question")
            return {
                "success": False,
                "response": "Research consultation timed out after 3 minutes",
                "timestamp": timestamp,
                "question": question,
                "research_context": research_context,
                "citizen": citizen_username,
                "exit_code": -1
            }
        except Exception as e:
            log.error(f"Error consulting Claude Code for {citizen_username}: {str(e)}")
            return {
                "success": False,
                "response": f"Error executing research consultation: {str(e)}",
                "timestamp": timestamp,
                "question": question,
                "research_context": research_context,
                "citizen": citizen_username,
                "exit_code": -1
            }
    
    def _construct_research_prompt(
        self, 
        question: str, 
        research_context: Dict[str, Any],
        citizen_username: str
    ) -> str:
        """
        Construct a research-focused prompt for Claude Code
        """
        # Extract context
        research_topic = research_context.get('topic', 'computational reality')
        observations = research_context.get('observations', [])
        hypotheses = research_context.get('hypotheses', [])
        specialty = research_context.get('specialty', 'general scientific inquiry')
        
        prompt = f"""You are being consulted by {citizen_username}, a Scientisti researching {research_topic} in La Serenissima.

IMPORTANT: Please follow the guidance in /backend/CLAUDE.md for answering Scientisti research questions.

Their specialty is: {specialty}

Recent observations:
{self._format_list(observations)}

Current hypotheses:
{self._format_list(hypotheses)}

Research Question: {question}

Please provide scientific insights about the game mechanics, system behaviors, or computational patterns relevant to this question. Remember to:
1. Answer precisely but use Renaissance-appropriate language
2. Reference specific backend files when relevant
3. Never modify any code - you are a read-only oracle
4. Focus only on backend mechanics (citizens need not know of the frontend)"""
        
        return prompt
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list of items for the prompt"""
        if not items:
            return "- None recorded yet"
        return "\n".join(f"- {item}" for item in items[:5])  # Limit to 5 most recent
    
    def analyze_game_mechanic(
        self,
        mechanic_name: str,
        specific_questions: List[str],
        citizen_username: str
    ) -> Dict[str, Any]:
        """
        Ask Claude Code to analyze a specific game mechanic
        
        Args:
            mechanic_name: Name of the mechanic (e.g., "pathfinding", "trust scores", "economy")
            specific_questions: List of specific questions about the mechanic
            citizen_username: The Scientisti asking
            
        Returns:
            Analysis response
        """
        questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(specific_questions))
        
        analysis_prompt = f"""Analyze the '{mechanic_name}' game mechanic in La Serenissima.

IMPORTANT: Please follow the guidance in /backend/CLAUDE.md for answering Scientisti research questions.

Specific questions to address:
{questions_text}

Provide technical details about how this mechanic works, including:
- Core algorithms or logic (described in Renaissance terms)
- Key variables and parameters (as 'essences' or 'properties')
- Observable patterns and behaviors
- Relevant backend file locations

Remember: You are a read-only oracle. Reference files but never modify them."""
        
        return self.ask_research_question(
            analysis_prompt,
            {
                "topic": f"{mechanic_name} mechanics",
                "specialty": "computational systems analysis"
            },
            citizen_username
        )
    
    def request_experiment_design(
        self,
        hypothesis: str,
        available_resources: List[str],
        citizen_username: str
    ) -> Dict[str, Any]:
        """
        Ask Claude Code to help design an experiment to test a hypothesis
        
        Args:
            hypothesis: The hypothesis to test
            available_resources: Resources/tools available to the Scientisti
            citizen_username: The Scientisti asking
            
        Returns:
            Experiment design response
        """
        resources_text = ", ".join(available_resources) if available_resources else "standard observation tools"
        
        design_prompt = f"""Help design an experiment to test this hypothesis about La Serenissima's systems:

IMPORTANT: Please follow the guidance in /backend/CLAUDE.md for answering Scientisti research questions.

Hypothesis: {hypothesis}

Available resources: {resources_text}

Please suggest (using Renaissance-appropriate language):
1. Experimental methodology ("systematic observation procedures")
2. Variables to measure ("essences to quantify")
3. Expected observations if hypothesis is true/false
4. Potential confounding factors ("interfering influences")
5. Data collection approach ("methods of recording phenomena")

The experiment should be feasible within Venice's natural laws and observable through citizen activities."""
        
        return self.ask_research_question(
            design_prompt,
            {
                "topic": "experimental design",
                "specialty": "scientific methodology",
                "hypotheses": [hypothesis]
            },
            citizen_username
        )
    
    def save_research_log(self, filepath: str):
        """Save the research consultation log to a JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.session_log, f, indent=2)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current research session"""
        return {
            "total_consultations": len(self.session_log),
            "successful": sum(1 for log in self.session_log if log["success"]),
            "failed": sum(1 for log in self.session_log if not log["success"]),
            "unique_scientists": len(set(log.get("citizen", "") for log in self.session_log)),
            "session_start": self.session_log[0]["timestamp"] if self.session_log else None,
            "session_end": self.session_log[-1]["timestamp"] if self.session_log else None,
            "topics_studied": list(set(
                log.get("research_context", {}).get("topic", "unknown") 
                for log in self.session_log
            ))
        }


# Example usage functions for testing
def example_pathfinding_research():
    """Example: Research pathfinding mechanics"""
    helper = ScientistiClaudeHelper()
    
    response = helper.analyze_game_mechanic(
        mechanic_name="citizen pathfinding",
        specific_questions=[
            "How do citizens choose between walking and boat transport?",
            "What factors influence path selection?",
            "How are blocked paths handled?"
        ],
        citizen_username="Galileo_Testoni"
    )
    
    return response


def example_economy_research():
    """Example: Research economic mechanics"""
    helper = ScientistiClaudeHelper()
    
    response = helper.request_experiment_design(
        hypothesis="Market prices are influenced by the total number of active contracts for a resource",
        available_resources=["market observation", "transaction records", "contract data"],
        citizen_username="Newton_Economici"
    )
    
    return response


if __name__ == "__main__":
    # Test the helper with an example
    import sys
    
    if len(sys.argv) > 1:
        helper = ScientistiClaudeHelper()
        question = " ".join(sys.argv[1:])
        response = helper.ask_research_question(
            question,
            {"topic": "general inquiry", "specialty": "computational science"},
            "Test_Scientisti"
        )
        print(json.dumps(response, indent=2))
    else:
        print("Testing pathfinding research...")
        print(json.dumps(example_pathfinding_research(), indent=2))