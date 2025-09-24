#!/usr/bin/env python3
"""
Manual digest generator as fallback when Claude Code is not available
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def create_manual_digest(data: Dict[Any, Any]) -> str:
    """Create a comprehensive digest from the collected data"""
    
    # Extract key information
    generated_at = data.get('generated_at', datetime.now().isoformat())
    date_str = generated_at.split('T')[0]
    team_members = data.get('team_members', [])
    repos = data.get('repositories', [])
    prs = data.get('pull_requests', [])
    stats = data.get('summary_stats', {})
    
    # Group PRs by status and priority
    open_prs = [pr for pr in prs if pr['status'] == 'open']
    merged_prs = [pr for pr in prs if pr['status'] == 'merged']
    team_authored = [pr for pr in prs if 'author' in pr['team_involvement']]
    stale_prs = [pr for pr in prs if pr['days_since_activity'] > 7 and pr['status'] == 'open']
    draft_prs = [pr for pr in prs if pr.get('is_draft', False)]
    
    # Engineering Manager Analysis
    critical_prs = [pr for pr in open_prs if any('critical' in label.lower() or 'hotfix' in label.lower() 
                                                for label in pr.get('labels', []))]
    large_prs = [pr for pr in open_prs if pr.get('files_changed', 0) > 15]  # Large PRs
    old_prs = [pr for pr in open_prs if pr['days_since_activity'] >= 3]  # >3 business days
    review_heavy_prs = [pr for pr in open_prs if len(pr.get('reviews', [])) > 3]  # Lots of back-and-forth
    
    # Priority PRs (has priority labels)
    priority_prs = [pr for pr in prs if any('priority' in label.lower() or 'critical' in label.lower() 
                                          for label in pr.get('labels', []))]
    
    # Group by repository
    repo_breakdown = {}
    for pr in prs:
        repo = pr['repo']
        if repo not in repo_breakdown:
            repo_breakdown[repo] = []
        repo_breakdown[repo].append(pr)
    
    # Team activity summary
    team_activity = {}
    for member in team_members:
        authored = [pr for pr in prs if pr.get('author') == member]
        
        # Check for reviews and comments more safely
        reviewed = []
        commented = []
        
        for pr in prs:
            # Check reviews
            for review in pr.get('reviews', []):
                if isinstance(review, dict) and review.get('author') == member:
                    reviewed.append(pr)
                    break
            
            # Check comments  
            for comment in pr.get('comments', []):
                if isinstance(comment, dict) and comment.get('author') == member:
                    commented.append(pr)
                    break
        
        if authored or reviewed or commented:
            team_activity[member] = {
                'authored': authored,
                'reviewed': len(reviewed),
                'commented': len(commented)
            }
    
    # Generate markdown with executive summary and manager priorities
    digest = f"""# Vault Team Daily Digest - {date_str}

## 📊 Executive Summary

**Team Velocity:** {len(merged_prs)} PRs merged, {len(open_prs)} PRs in progress, {len(draft_prs)} drafts  
**Review Health:** Avg. {sum(pr['days_since_activity'] for pr in open_prs) / max(len(open_prs), 1):.1f} days since activity  
**Workload:** {len(large_prs)} large PRs (>15 files), {len(old_prs)} PRs waiting >3 days for review  
**Team Coverage:** All {len(team_members)} team members have recent activity

## 🚨 Immediate Intervention Needed

"""
    
    immediate_actions = []
    
    if critical_prs:
        immediate_actions.append("**Critical/Hotfix PRs waiting for review:**")
        for pr in critical_prs[:3]:
            labels_str = ", ".join(pr.get('labels', []))
            immediate_actions.append(f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` ({pr['days_since_activity']} days) - Labels: {labels_str}")
    
    if old_prs:
        immediate_actions.append(f"**{len(old_prs)} PRs waiting >3 business days for review:**")
        for pr in sorted(old_prs, key=lambda x: x['days_since_activity'], reverse=True)[:5]:
            immediate_actions.append(f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` - @{pr['author']} ({pr['days_since_activity']} days)")
    
    if review_heavy_prs:
        immediate_actions.append(f"**{len(review_heavy_prs)} PRs with extensive review cycles (potential communication issues):**")
        for pr in review_heavy_prs[:3]:
            immediate_actions.append(f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` - {len(pr.get('reviews', []))} reviews, {len(pr.get('comments', []))} comments")
    
    if not immediate_actions:
        immediate_actions.append("✅ **No immediate interventions needed** - team is operating smoothly")
    
    digest += "\n".join(immediate_actions)
    
    digest += f"""

## ⚠️ Monitoring Situations

"""
    
    monitoring_items = []
    
    if large_prs:
        monitoring_items.append(f"**Large PRs requiring careful review ({len(large_prs)} total):**")
        for pr in sorted(large_prs, key=lambda x: x.get('files_changed', 0), reverse=True)[:5]:
            monitoring_items.append(f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` - {pr.get('files_changed', 0)} files changed")
    
    # Team members with lots of open PRs (potential overload)
    author_counts = {}
    for pr in open_prs:
        author = pr.get('author')
        if author in team_members:
            author_counts[author] = author_counts.get(author, 0) + 1
    
    overloaded_authors = [(author, count) for author, count in author_counts.items() if count >= 3]
    if overloaded_authors:
        monitoring_items.append("**Team members with high PR load:**")
        for author, count in sorted(overloaded_authors, key=lambda x: x[1], reverse=True):
            monitoring_items.append(f"  - @{author}: {count} open PRs")
    
    # PRs approaching the "old" threshold
    approaching_old = [pr for pr in open_prs if pr['days_since_activity'] == 2]  # 2 days, about to hit 3
    if approaching_old:
        monitoring_items.append(f"**PRs approaching 3-day threshold ({len(approaching_old)} PRs):**")
        for pr in approaching_old[:3]:
            monitoring_items.append(f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` - @{pr['author']}")
    
    if not monitoring_items:
        monitoring_items.append("✅ **No monitoring concerns** - PR sizes and timing look healthy")
    
    digest += "\n".join(monitoring_items)
    
    digest += "\n\n## 🎯 Key Actions for Engineering Manager\n\n"
    
    manager_actions = []
    
    if old_prs or critical_prs:
        manager_actions.append("**Review Assignment:**")
        if critical_prs:
            manager_actions.append("  - Prioritize critical/hotfix PR reviews immediately")
        if old_prs:
            manager_actions.append(f"  - Follow up on {len(old_prs)} PRs waiting >3 days - may need reviewer assignment")
    
    if review_heavy_prs:
        manager_actions.append("**Communication Facilitation:**")
        manager_actions.append(f"  - Check {len(review_heavy_prs)} PRs with extensive reviews for communication breakdowns")
        manager_actions.append("  - Consider offline discussion for complex technical decisions")
    
    if large_prs:
        manager_actions.append("**Process Improvement:**")
        manager_actions.append(f"  - Review {len(large_prs)} large PRs - consider work breakdown guidance")
        manager_actions.append("  - Discuss smaller, incremental changes in team retrospective")
    
    if overloaded_authors:
        manager_actions.append("**Workload Management:**")
        for author, count in overloaded_authors:
            manager_actions.append(f"  - Check with @{author} on {count} open PRs - may need support or prioritization")
    
    # Positive reinforcement
    if len(merged_prs) > 5:
        manager_actions.append("**Team Recognition:**")
        manager_actions.append(f"  - Acknowledge strong velocity: {len(merged_prs)} PRs merged recently")
    
    if len(stale_prs) == 0:
        manager_actions.append("**Process Health:**")
        manager_actions.append("  - Excellent review turnaround - no stale PRs!")
    
    if not (old_prs or critical_prs or review_heavy_prs or large_prs):
        manager_actions.append("✅ **No immediate manager actions needed** - team is self-managing effectively")
    
    digest += "\n".join(manager_actions)
    
    digest += "\n\n---\n\n## 📋 Detailed PR Status\n"
    
    if priority_prs:
        digest += "\n### High Priority PRs:\n"
        for pr in priority_prs[:5]:  # Top 5
            labels_str = ", ".join(pr.get('labels', []))
            digest += f"- **[#{pr['number']}]({pr['url']})** `{pr['title']}`\n"
            digest += f"  - Author: @{pr['author']} | Days: {pr['days_since_activity']} | Labels: {labels_str}\n"
    
    if stale_prs:
        digest += "\n### Stale PRs (>7 days):\n"
        for pr in stale_prs:
            digest += f"- **[#{pr['number']}]({pr['url']})** `{pr['title']}` ({pr['days_since_activity']} days)\n"
    
    # Open PRs ready for review
    ready_for_review = [pr for pr in open_prs if not pr.get('is_draft', False) and 'author' in pr['team_involvement']]
    if ready_for_review:
        digest += "\n## 📋 Ready for Review\n"
        for pr in ready_for_review:
            digest += f"- **[#{pr['number']}]({pr['url']})** `{pr['title']}`\n"
            digest += f"  - Author: @{pr['author']} | Files: {pr['files_changed']} | Days: {pr['days_since_activity']}\n"
    
    # Team activity
    if team_activity:
        digest += "\n## 👥 Team Activity Summary\n"
        for member, activity in team_activity.items():
            digest += f"\n### @{member}\n"
            if activity['authored']:
                digest += f"- **Authored:** {len(activity['authored'])} PRs\n"
                for pr in activity['authored']:
                    digest += f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}`\n"
            if activity['reviewed']:
                digest += f"- **Reviewed:** {activity['reviewed']} PRs\n"
            if activity['commented']:
                digest += f"- **Commented:** {activity['commented']} PRs\n"
    
    # Recent completions
    if merged_prs:
        digest += "\n## ✅ Recent Completions\n"
        for pr in merged_prs[:10]:  # Last 10
            digest += f"- **[#{pr['number']}]({pr['url']})** `{pr['title']}`\n"
            digest += f"  - Author: @{pr['author']} | Merged: {pr.get('merged_at', 'Unknown')}\n"
    
    # Repository breakdown
    digest += "\n## 📊 Repository Breakdown\n"
    for repo, repo_prs in repo_breakdown.items():
        open_count = len([pr for pr in repo_prs if pr['status'] == 'open'])
        merged_count = len([pr for pr in repo_prs if pr['status'] == 'merged'])
        digest += f"\n### {repo} ({len(repo_prs)} PRs)\n"
        digest += f"- Open: {open_count}, Merged: {merged_count}\n"
        
        # Show most active PRs
        active_prs = sorted([pr for pr in repo_prs if pr['status'] == 'open'], 
                           key=lambda x: x['days_since_activity'])[:3]
        if active_prs:
            digest += "- Recent activity:\n"
            for pr in active_prs:
                digest += f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` ({pr['days_since_activity']} days)\n"
    
    digest += f"\n---\n*Generated at {generated_at} by GitDigest*"
    
    return digest


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 manual_digest.py <data_file> <output_file>")
        sys.exit(1)
    
    data_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not data_file.exists():
        print(f"Error: Data file {data_file} not found")
        sys.exit(1)
    
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        digest = create_manual_digest(data)
        
        with open(output_file, 'w') as f:
            f.write(digest)
        
        print(f"✅ Manual digest created: {output_file}")
        
    except Exception as e:
        print(f"❌ Error creating digest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()