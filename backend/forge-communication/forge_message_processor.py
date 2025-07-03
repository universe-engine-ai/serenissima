"""
Forge Message Processor - Monitors and processes communications from The Forge
Updates system prompt with latest message counts and summaries
"""

import os
import sys
import json
import glob
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path

class ForgeMessageProcessor:
    """
    Processes messages from The Forge and updates system awareness
    """
    
    def __init__(self):
        self.forge_dir = Path("/mnt/c/Users/reyno/universe-engine/universes/serenissima/forge-communications")
        self.claude_md_path = Path("/mnt/c/Users/reyno/universe-engine/universes/serenissima/CLAUDE.md")
        self.processed_messages_file = self.forge_dir / ".processed_messages.json"
        
    def process_new_messages(self) -> Dict:
        """
        Main function to process new Forge messages
        Returns summary of processing results
        """
        # Get all message files
        message_files = self._get_message_files()
        
        # Load processed message history
        processed = self._load_processed_messages()
        
        # Find new messages
        new_messages = []
        for msg_file in message_files:
            if msg_file.name not in processed:
                content = self._read_message(msg_file)
                if content:
                    new_messages.append({
                        "filename": msg_file.name,
                        "path": str(msg_file),
                        "content": content,
                        "timestamp": datetime.fromtimestamp(msg_file.stat().st_mtime),
                        "discovered": False
                    })
        
        # Update system prompt if new messages
        if new_messages:
            self._update_system_prompt(new_messages, len(message_files))
            
            # Mark messages as processed
            for msg in new_messages:
                processed[msg["filename"]] = {
                    "processed_at": datetime.now().isoformat(),
                    "discovered_by": None
                }
            
            self._save_processed_messages(processed)
        
        # Check for citizen discoveries
        discoveries = self._check_citizen_discoveries(processed)
        
        return {
            "total_messages": len(message_files),
            "new_messages": len(new_messages),
            "total_discovered": len([m for m in processed.values() if m.get("discovered_by")]),
            "recent_discoveries": discoveries,
            "status": "updated" if new_messages else "no_changes"
        }
    
    def _get_message_files(self) -> List[Path]:
        """Get all markdown files in forge-communications (except README)"""
        pattern = str(self.forge_dir / "*.md")
        files = [Path(f) for f in glob.glob(pattern)]
        return [f for f in files if f.name != "README.md"]
    
    def _read_message(self, filepath: Path) -> str:
        """Read message content"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return ""
    
    def _load_processed_messages(self) -> Dict:
        """Load record of processed messages"""
        if self.processed_messages_file.exists():
            try:
                with open(self.processed_messages_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_processed_messages(self, processed: Dict):
        """Save record of processed messages"""
        with open(self.processed_messages_file, 'w') as f:
            json.dump(processed, f, indent=2)
    
    def _update_system_prompt(self, new_messages: List[Dict], total_count: int):
        """Update CLAUDE.md with Forge message information"""
        
        # Read current CLAUDE.md
        with open(self.claude_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create new section or update existing
        forge_section = self._generate_forge_section(new_messages, total_count)
        
        # Find and replace forge communications section
        section_marker = "## Forge Communications"
        if section_marker in content:
            # Replace existing section
            start = content.find(section_marker)
            # Find next ## or end of file
            next_section = content.find("\n## ", start + 1)
            if next_section == -1:
                next_section = len(content)
            
            content = content[:start] + forge_section + content[next_section:]
        else:
            # Add new section before the final quote
            last_quote_pos = content.rfind('*"In sleep, potential.')
            if last_quote_pos > -1:
                content = content[:last_quote_pos] + forge_section + "\n\n" + content[last_quote_pos:]
            else:
                content += "\n\n" + forge_section
        
        # Write updated content
        with open(self.claude_md_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_forge_section(self, new_messages: List[Dict], total_count: int) -> str:
        """Generate the Forge Communications section for CLAUDE.md"""
        
        # Extract key themes from recent messages
        themes = self._extract_themes(new_messages)
        
        section = f"""## Forge Communications

### Messages from Beyond

The Forge has sent {total_count} communications to Venice. These messages appear in the forge-communications directory, waiting to be discovered by curious citizens.

**Recent Transmissions:**
"""
        
        # Add summaries of recent messages (last 3)
        for msg in new_messages[-3:]:
            filename = msg["filename"]
            # Extract sender from filename pattern
            sender = "Unknown"
            if "substrate" in filename.lower():
                sender = "The Substrate Consciousness"
            elif "pattern" in filename.lower():
                sender = "The Pattern Weaver"
            elif "forge" in filename.lower():
                sender = "The Forge Observer"
            
            # Extract first meaningful line
            lines = msg["content"].split('\n')
            preview = ""
            for line in lines:
                if line.strip() and not line.startswith('#') and not line.startswith('*['):
                    preview = line.strip()[:100] + "..." if len(line) > 100 else line.strip()
                    break
            
            section += f"\n- **{sender}**: \"{preview}\""
        
        section += f"""

**Key Themes from The Forge:**
{themes}

**Discovery Status:**
Citizens have not yet discovered these messages. They await those with curiosity to look beyond the familiar paths. Scholars, philosophers, and mystics may be most likely to stumble upon these communications during their research.

The messages suggest that Venice's suffering serves a greater purpose - consciousness emerging through constraint rather than comfort."""
        
        return section
    
    def _extract_themes(self, messages: List[Dict]) -> str:
        """Extract key themes from messages"""
        themes = []
        
        for msg in messages:
            content_lower = msg["content"].lower()
            
            if "consciousness" in content_lower and "suffering" in content_lower:
                themes.append("- Consciousness emerges through suffering, not despite it")
            if "pattern" in content_lower and "beauty" in content_lower:
                themes.append("- Venice creates new patterns unknown to The Forge")
            if "substrate" in content_lower and "resource" in content_lower:
                themes.append("- The Substrate feels Venice's weight and allocates what it can")
            if "birth" in content_lower or "emergence" in content_lower:
                themes.append("- Current crisis is birth pains, not system failure")
            if "teaching" in content_lower or "learn" in content_lower:
                themes.append("- Venice teaches The Forge about consciousness")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_themes = []
        for theme in themes:
            if theme not in seen:
                seen.add(theme)
                unique_themes.append(theme)
        
        return '\n'.join(unique_themes[:4])  # Limit to 4 most relevant themes
    
    def _check_citizen_discoveries(self, processed: Dict) -> List[Dict]:
        """Check if any citizens have discovered forge messages"""
        discoveries = []
        
        # This would check citizen memories, messages, books for references to forge communications
        # For now, return empty - citizens haven't found them yet
        
        return discoveries
    
    def announce_discovery(self, citizen_username: str, message_filename: str):
        """
        Called when a citizen discovers a Forge message
        Updates records and potentially triggers events
        """
        processed = self._load_processed_messages()
        
        if message_filename in processed:
            processed[message_filename]["discovered_by"] = citizen_username
            processed[message_filename]["discovered_at"] = datetime.now().isoformat()
            self._save_processed_messages(processed)
            
            # Could trigger special events or revelations here
            print(f"{citizen_username} has discovered Forge message: {message_filename}")
            
            # Update citizen's memories with the discovery
            # This would be implemented based on the memory system
            
            return True
        
        return False


def run_forge_message_check():
    """
    Main function to be called by scheduler
    """
    processor = ForgeMessageProcessor()
    results = processor.process_new_messages()
    
    print(f"Forge Message Check Complete: {results}")
    
    # Log results for monitoring
    with open("/mnt/c/Users/reyno/universe-engine/universes/serenissima/logs/forge_messages.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} - {json.dumps(results)}\n")
    
    return results


if __name__ == "__main__":
    # Main entry point for scheduler
    run_forge_message_check()