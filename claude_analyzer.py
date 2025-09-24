#!/usr/bin/env python3
"""
Claude Code integration for GitDigest analysis
"""

import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any


class ClaudeAnalyzer:
    """Handle Claude Code integration for digest generation"""
    
    def __init__(self, data_file: Path, output_file: Path):
        self.data_file = data_file
        self.output_file = output_file
    
    def generate_digest(self) -> bool:
        """Generate digest using Claude Code"""
        try:
            # Load the data to get some context
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Create the prompt with the JSON data embedded
            prompt = self._create_manager_analysis_prompt(data)
            full_prompt = f"{prompt}\n\nAnalyze this data:\n{json.dumps(data, indent=2)}"
            
            try:
                # Use Popen with stdin/pipe interface
                process = subprocess.Popen(
                    ['claude'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate(input=full_prompt, timeout=60)  # 1 minute timeout
                
                if process.returncode == 0 and stdout.strip():
                    # Write Claude's output to the digest file
                    with open(self.output_file, 'a') as f:
                        f.write(f"\n\n## 🧠 AI Insight\n{stdout.strip()}\n")
                    
                    logging.info("Claude analysis completed successfully")
                    return True
                else:
                    logging.error(f"Claude command failed. Return code: {process.returncode}, Error: {stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                logging.warning("Claude command timed out")
                process.kill()
                return False
                
        except Exception as e:
            logging.error(f"Failed to generate digest: {e}")
            return False
    
    def _create_manager_analysis_prompt(self, data: Dict[Any, Any]) -> str:
        prompt = f"""I am an engineering manager. Can you read the data and give me a summary of what would be important for me to help with?
        Most important to me:
        - Inconsistent review participation across team
        - Lack of clear PR descriptions or context
        - Unproductive disagreements in reviews
        - Team member struggling with a specific concept
        Always include the PR numbers and links where relevant."""
        return prompt

def main():
    """Standalone analyzer for testing"""
    import sys
    if len(sys.argv) != 3:
        print("Usage: python claude_analyzer.py <data_file> <output_file>")
        sys.exit(1)
    
    data_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    analyzer = ClaudeAnalyzer(data_file, output_file)
    success = analyzer.generate_digest()
    
    if success:
        print(f"Digest generated successfully: {output_file}")
    else:
        print("Failed to generate digest")
        sys.exit(1)


if __name__ == "__main__":
    main()