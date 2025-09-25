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
    
    def __init__(self, data_file: Path, output_file: Path, digest_type: str = "manager"):
        self.data_file = data_file
        self.output_file = output_file
        self.digest_type = digest_type
    
    def generate_digest(self) -> bool:
        """Generate digest using Claude Code"""
        try:
            # Load the data to get some context
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Create the prompt based on digest type
            if self.digest_type == "engineer":
                prompt = self._create_engineer_analysis_prompt(data)
            else:
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
                        f.write(f"\n\n## 🧠 AI Insight for {self.digest_type}\n{stdout.strip()}\n")
                    
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

    def _create_engineer_analysis_prompt(self, data: Dict[Any, Any]) -> str:
        prompt = f"""I am an a software engineer. Can you read my team's github activity in the data file and give me a prioritized list of what I should review?
        Rank by impact and urgency.

        For each action, provide:
        - Specific PR numbers to review, with links to the PR
        - Why this matters technically (not just process)
        - Time estimate for providing this review
        - Any blockers or dependencies"""
        return prompt

def main():
    """Standalone analyzer for testing"""
    import sys
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python claude_analyzer.py <data_file> <output_file> [digest_type]")
        print("  digest_type: 'manager' (default) or 'engineer'")
        sys.exit(1)
    
    data_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    digest_type = sys.argv[3] if len(sys.argv) == 4 else "manager"
    
    if digest_type not in ["manager", "engineer"]:
        print("Error: digest_type must be 'manager' or 'engineer'")
        sys.exit(1)
    
    analyzer = ClaudeAnalyzer(data_file, output_file, digest_type)
    success = analyzer.generate_digest()
    
    if success:
        print(f"{digest_type.title()} digest generated successfully: {output_file}")
    else:
        print("Failed to generate digest")
        sys.exit(1)


if __name__ == "__main__":
    main()