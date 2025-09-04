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
            
            # Create a detailed prompt for Claude
            prompt = self._create_analysis_prompt(data)
            
            # Create a temporary prompt file
            prompt_file = self.data_file.parent / "analysis_prompt.txt"
            with open(prompt_file, 'w') as f:
                f.write(prompt)
            
            # Run Claude Code - try different approaches
            commands_to_try = [
                # Modern Claude Code syntax
                ["claude", "code", f"Please analyze {self.data_file} using the prompt in {prompt_file} and save to {self.output_file}"],
                # Alternative approach
                ["claude", f"Analyze the GitHub data in {self.data_file} and create a digest at {self.output_file}"],
            ]
            
            for cmd in commands_to_try:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # 30 second timeout
                    if result.returncode == 0:
                        logging.info("Claude analysis completed successfully")
                        # Clean up
                        if prompt_file.exists():
                            prompt_file.unlink()
                        return True
                except subprocess.TimeoutExpired:
                    logging.warning(f"Claude command timed out: {' '.join(cmd)}")
                    continue
            
            # If all commands failed
            logging.error(f"All Claude commands failed. Last error: {result.stderr}")
            
            # Clean up
            if prompt_file.exists():
                prompt_file.unlink()
            return False
                
        except Exception as e:
            logging.error(f"Failed to generate digest: {e}")
            return False
    
    def _create_analysis_prompt(self, data: Dict[Any, Any]) -> str:
        """Create a detailed prompt for Claude analysis"""
        stats = data.get('summary_stats', {})
        team_members = data.get('team_members', [])
        
        return f"""
Analyze this GitHub PR data for the Vault team and create a comprehensive daily digest.

**Context:**
- Team has {len(team_members)} members: {', '.join(team_members)}
- Data covers {len(data.get('repositories', []))} repositories
- Found {stats.get('total_active_prs', 0)} active PRs with team involvement

**Required Output Format (Markdown):**

# Vault Team Daily Digest - {data.get('generated_at', '').split('T')[0]}

## 🎯 Executive Summary
- **Active PRs:** {stats.get('total_active_prs', 0)} total
- **Team Authored:** {stats.get('team_authored_prs', 0)} 
- **Needs Review:** [count PRs waiting for reviews]
- **Stale Items:** {stats.get('stale_prs', 0)} PRs with >7 days no activity
- **Recent Merges:** {stats.get('merged_prs', 0)} PRs merged recently

## 🚨 Action Items
[List PRs that need immediate attention - reviews, approvals, or are blocked]

## 📋 Active Pull Requests by Priority

### High Priority (Blocking/Critical)
[PRs with "priority-high" or "critical" labels, or blocking labels]

### Ready for Review
[Open PRs authored by team members that need reviews]

### In Review
[PRs currently being reviewed by team members]

### Waiting on Author
[PRs where team members requested changes]

## 👥 Team Activity Summary

### [For each team member who has activity]
**[Member Name]:**
- Authored: [list of PRs they authored]
- Reviewed: [PRs they reviewed] 
- Comments: [PRs they commented on]

## ⚠️ Stale Items Needing Attention
[PRs with >7 days no activity, what's blocking them]

## ✅ Recent Completions
[Recently merged PRs with brief description of what was accomplished]

## 📊 Repository Breakdown
[Brief stats per repository]

**Analysis Instructions:**
1. Focus on actionable insights
2. Highlight blockers and bottlenecks
3. Use emoji indicators for visual clarity
4. Group similar items together
5. Include PR numbers and links where relevant
6. Identify patterns (e.g., many PRs waiting on specific reviewer)
7. Calculate metrics like average days to merge, review turnaround time
8. Flag any concerning trends (e.g., increasing stale PR count)

Make the digest scannable and immediately useful for standup meetings.
"""


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