#!/usr/bin/env python3
"""
Engineer-focused digest generator
Creates a digest focused on what engineers need to review/action
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def create_engineer_digest(data: Dict[Any, Any]) -> str:
    """Create an engineer-focused digest from the collected data"""
    
    # Extract key information
    generated_at = data.get('generated_at', datetime.now().isoformat())
    date_str = generated_at.split('T')[0]
    team_members = data.get('team_members', [])
    repos = data.get('repositories', [])
    prs = data.get('pull_requests', [])
    stats = data.get('summary_stats', {})
    
    # Group PRs by what engineers need to focus on
    open_prs = [pr for pr in prs if pr['status'] == 'open']
    
    # PRs that need reviews from team
    needs_review = []
    my_prs_needing_attention = []
    high_priority = []
    
    for pr in open_prs:
        # High priority items
        if any('priority' in label.lower() or 'critical' in label.lower() or 'urgent' in label.lower() 
               for label in pr.get('labels', [])):
            high_priority.append(pr)
        
        # PRs authored by team that might need reviews
        if pr.get('author') in team_members:
            if not pr.get('is_draft', False):
                # Check if it has recent reviews or if it's ready for review
                reviews = pr.get('reviews', [])
                if len(reviews) == 0 or pr['days_since_activity'] <= 1:
                    needs_review.append(pr)
        
        # PRs where team members have been active (reviews/comments) but might need follow-up
        if ("reviewer" in pr.get('team_involvement', '') or 
            "commenter" in pr.get('team_involvement', '')):
            # If there's been recent activity and team is involved
            if pr['days_since_activity'] <= 2:
                my_prs_needing_attention.append(pr)
    
    # Remove duplicates
    needs_review = [pr for pr in needs_review if pr not in high_priority]
    
    # Large PRs that need extra attention
    large_prs = [pr for pr in open_prs if pr.get('files_changed', 0) > 15]
    
    # PRs approaching staleness
    getting_stale = [pr for pr in open_prs if pr['days_since_activity'] >= 5 and pr['days_since_activity'] < 7]
    
    # Recently merged PRs (good to know what landed)
    merged_prs = [pr for pr in prs if pr['status'] == 'merged'][:10]  # Last 10
    
    # Generate engineer-focused markdown
    digest = f"""# Team Development Digest - {date_str}

## 🎯 At a Glance
**{len(open_prs)} open PRs** | **{len(needs_review)} ready for review** | **{len(high_priority)} high priority** | **{len(merged_prs)} recently merged**

## 🔥 High Priority - Action Needed

"""
    
    if high_priority:
        for pr in high_priority[:5]:  # Top 5 high priority
            labels_str = ", ".join([l for l in pr.get('labels', []) if 'priority' in l.lower() or 'critical' in l.lower() or 'urgent' in l.lower()])
            digest += f"**[#{pr['number']}]({pr['url']})** `{pr['title']}`  \n"
            digest += f"📍 **{pr['repo']}** | 👤 @{pr['author']} | ⏱️ {pr['days_since_activity']} days | 🏷️ {labels_str}  \n\n"
    else:
        digest += "✅ No high priority items\n\n"
    
    digest += "## 👀 Ready for Review\n\n"
    
    if needs_review:
        for pr in sorted(needs_review, key=lambda x: x['days_since_activity'], reverse=True):
            digest += f"**[#{pr['number']}]({pr['url']})** `{pr['title']}`  \n"
            digest += f"📍 **{pr['repo']}** | 👤 @{pr['author']} | 📁 {pr['files_changed']} files | ⏱️ {pr['days_since_activity']} days  \n"
            
            # Show if it has any reviews yet
            review_count = len(pr.get('reviews', []))
            if review_count > 0:
                digest += f"💬 {review_count} reviews  \n"
            else:
                digest += f"🆕 No reviews yet  \n"
            digest += "\n"
    else:
        digest += "✅ No PRs waiting for review\n\n"
    
    digest += "## ⚠️ Needs Attention\n\n"
    
    attention_items = []
    
    if large_prs:
        attention_items.append(f"**{len(large_prs)} Large PRs** (>15 files) - consider breaking down:")
        for pr in large_prs[:3]:
            attention_items.append(f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` - {pr['files_changed']} files")
    
    if getting_stale:
        attention_items.append(f"**{len(getting_stale)} PRs Getting Stale** (5-7 days old):")
        for pr in getting_stale[:3]:
            attention_items.append(f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` - @{pr['author']} ({pr['days_since_activity']} days)")
    
    if my_prs_needing_attention:
        attention_items.append("**PRs with Recent Team Activity** (may need follow-up):")
        for pr in my_prs_needing_attention[:3]:
            digest += f"  - [#{pr['number']}]({pr['url']}) `{pr['title']}` - {pr.get('team_involvement', 'unknown')} involvement\n"
    
    if attention_items:
        digest += "\n".join(attention_items) + "\n\n"
    else:
        digest += "✅ Nothing needs immediate attention\n\n"
    
    # Show what landed recently
    if merged_prs:
        digest += "## ✅ Recently Shipped\n\n"
        for pr in merged_prs:
            digest += f"- **[#{pr['number']}]({pr['url']})** `{pr['title']}` - @{pr['author']}\n"
        digest += "\n"
    
    # Repository-specific view for engineers
    digest += "## 📊 By Repository\n\n"
    
    repo_breakdown = {}
    for pr in open_prs:
        repo = pr['repo']
        if repo not in repo_breakdown:
            repo_breakdown[repo] = {'total': 0, 'ready_for_review': 0, 'in_review': 0}
        repo_breakdown[repo]['total'] += 1
        
        if pr in needs_review:
            repo_breakdown[repo]['ready_for_review'] += 1
        elif len(pr.get('reviews', [])) > 0:
            repo_breakdown[repo]['in_review'] += 1
    
    for repo, stats in repo_breakdown.items():
        digest += f"**{repo}**: {stats['total']} open PRs "
        digest += f"({stats['ready_for_review']} ready for review, {stats['in_review']} in review)\n"
    
    digest += f"\n---\n*Generated at {generated_at} by GitDigest*"
    
    return digest


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 engineer_digest.py <data_file> <output_file>")
        sys.exit(1)
    
    data_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not data_file.exists():
        print(f"Error: Data file {data_file} not found")
        sys.exit(1)
    
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        digest = create_engineer_digest(data)
        
        with open(output_file, 'w') as f:
            f.write(digest)
        
        print(f"✅ Engineer digest created: {output_file}")
        
    except Exception as e:
        print(f"❌ Error creating engineer digest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()