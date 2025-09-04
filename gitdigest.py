#!/usr/bin/env python3
"""
GitDigest - GitHub Activity Data Collection and Analysis Tool
Collects PR data for Vault team members and generates daily summaries using Claude Code.
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import requests
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Base configuration for GitDigest"""
    team_members: List[str]
    repositories: List[str]
    activity_days: int = 7
    recent_merge_days: int = 2
    github_token: str = None
    output_dir: Path = None
    max_comment_length: int = 500
    max_key_files: int = 5
    api_delay: float = 0.1
    max_retries: int = 3
    per_page: int = 100
    
    @classmethod
    def from_file(cls, config_file: Path = None):
        """Load configuration from JSON file"""
        if config_file is None:
            config_file = Path(__file__).parent / "config.json"
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_file}\n\n"
                "Please create config.json with the following structure:\n"
                "{\n"
                '  "team_members": ["github_user1", "github_user2"],\n'
                '  "repositories": ["org/repo1", "org/repo2"],\n'
                '  "settings": {\n'
                '    "activity_days": 7,\n'
                '    "recent_merge_days": 2,\n'
                '    "max_comment_length": 500,\n'
                '    "max_key_files": 5\n'
                '  },\n'
                '  "output": {"directory": "output"},\n'
                '  "github": {\n'
                '    "api_delay_seconds": 0.1,\n'
                '    "max_retries": 3,\n'
                '    "per_page": 100\n'
                '  }\n'
                "}\n"
            )
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Validate required fields
        if not config_data.get("team_members"):
            raise ValueError("config.json must contain 'team_members' with GitHub usernames")
        if not config_data.get("repositories"):
            raise ValueError("config.json must contain 'repositories' in 'owner/repo' format")
        
        # Set defaults for optional sections
        settings = config_data.get("settings", {
            "activity_days": 7, "recent_merge_days": 2, "max_comment_length": 500, "max_key_files": 5
        })
        output_config = config_data.get("output", {"directory": "output"})
        github_config = config_data.get("github", {
            "api_delay_seconds": 0.1, "max_retries": 3, "per_page": 100
        })
        
        return cls(
            team_members=config_data["team_members"],
            repositories=config_data["repositories"],
            activity_days=settings.get("activity_days", 7),
            recent_merge_days=settings.get("recent_merge_days", 2),
            max_comment_length=settings.get("max_comment_length", 500),
            max_key_files=settings.get("max_key_files", 5),
            github_token=os.getenv("GITHUB_TOKEN"),
            output_dir=Path(__file__).parent / output_config.get("directory", "output"),
            api_delay=github_config.get("api_delay_seconds", 0.1),
            max_retries=github_config.get("max_retries", 3),
            per_page=github_config.get("per_page", 100)
        )


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    pass


class GitHubClient:
    """GitHub API client with rate limiting and pagination support"""
    
    def __init__(self, token: str, config: Config = None):
        self.token = token
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        })
        self.base_url = "https://api.github.com"
        
    def _make_request(self, url: str, params: Optional[Dict] = None) -> requests.Response:
        """Make a request with rate limit handling"""
        response = self.session.get(url, params=params)
        
        if response.status_code == 403 and "rate limit" in response.text.lower():
            reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 3600))
            wait_time = max(reset_time - int(time.time()) + 10, 60)
            logging.warning(f"Rate limit exceeded. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            response = self.session.get(url, params=params)
        
        if response.status_code != 200:
            raise GitHubAPIError(f"GitHub API error: {response.status_code} - {response.text}")
        
        return response
    
    def get_paginated_data(self, url: str, params: Optional[Dict] = None) -> List[Dict]:
        """Fetch all pages of data from a paginated endpoint"""
        all_data = []
        page = 1
        params = params or {}
        per_page = self.config.per_page if self.config else 100
        api_delay = self.config.api_delay if self.config else 0.1
        
        while True:
            params['page'] = page
            params['per_page'] = per_page
            
            response = self._make_request(url, params)
            data = response.json()
            
            if not data or len(data) == 0:
                break
                
            all_data.extend(data)
            
            if len(data) < per_page:
                break
                
            page += 1
            time.sleep(api_delay)
            
        return all_data
    
    def validate_token(self) -> bool:
        """Validate GitHub token and permissions"""
        try:
            response = self._make_request(f"{self.base_url}/user")
            user_data = response.json()
            logging.info(f"Authenticated as: {user_data.get('login')}")
            return True
        except GitHubAPIError as e:
            logging.error(f"Token validation failed: {e}")
            return False


class GitDigestCollector:
    """Main data collection class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.github = GitHubClient(config.github_token, config)
        # Use timezone-aware datetimes to match GitHub API
        now_utc = datetime.now(timezone.utc)
        self.cutoff_date = now_utc - timedelta(days=config.activity_days)
        self.merge_cutoff_date = now_utc - timedelta(days=config.recent_merge_days)
        
    def setup_logging(self):
        """Configure logging"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.config.output_dir / "gitdigest.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def collect_pr_data(self, repo: str) -> List[Dict]:
        """Collect PR data for a repository with smart filtering"""
        logging.info(f"Collecting PR data for {repo}")
        
        relevant_prs = []
        
        # Strategy 1: Get PRs authored by team members (most efficient)
        for member in self.config.team_members:
            logging.info(f"Fetching PRs authored by {member} in {repo}")
            member_prs = self.get_prs_by_author(repo, member)
            relevant_prs.extend(member_prs)
        
        # Strategy 2: Get recently updated PRs for review involvement
        # Only get last 20-30 PRs to check for team reviews/comments
        logging.info(f"Fetching recently updated PRs in {repo} for team involvement")
        recent_prs = self.get_recent_prs_for_team_involvement(repo, limit=30)
        relevant_prs.extend(recent_prs)
        
        # Remove duplicates based on PR number
        seen_prs = set()
        unique_prs = []
        for pr in relevant_prs:
            if pr['number'] not in seen_prs:
                seen_prs.add(pr['number'])
                unique_prs.append(pr)
        
        logging.info(f"Found {len(unique_prs)} relevant PRs in {repo}")
        return unique_prs
    
    def get_prs_by_author(self, repo: str, author: str) -> List[Dict]:
        """Get PRs authored by a specific team member"""
        url = f"{self.github.base_url}/search/issues"
        params = {
            "q": f"repo:{repo} type:pr author:{author} updated:>={self.cutoff_date.strftime('%Y-%m-%d')}",
            "sort": "updated",
            "per_page": 50
        }
        
        try:
            response = self.github._make_request(url, params)
            search_results = response.json()
            
            prs = []
            for item in search_results.get('items', []):
                # Convert search result to PR format by fetching full PR data
                pr_url = item['pull_request']['url']
                pr_response = self.github._make_request(pr_url)
                pr_data = pr_response.json()
                
                processed_pr = self.process_pr(repo, pr_data)
                if processed_pr:
                    prs.append(processed_pr)
            
            logging.info(f"Found {len(prs)} PRs authored by {author}")
            return prs
            
        except Exception as e:
            logging.warning(f"Failed to get PRs by author {author}: {e}")
            return []
    
    def get_recent_prs_for_team_involvement(self, repo: str, limit: int = 30) -> List[Dict]:
        """Get recent PRs to check for team member involvement in reviews/comments"""
        url = f"{self.github.base_url}/repos/{repo}/pulls"
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": limit
        }
        
        try:
            response = self.github._make_request(url, params)
            prs = response.json()
            
            relevant_prs = []
            for pr in prs:
                # Quick date check
                updated_at = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
                if updated_at < self.cutoff_date:
                    break
                    
                # Skip if authored by team member (already got those)
                if pr.get('user') and pr['user'] and pr['user']['login'] in self.config.team_members:
                    continue
                    
                # Check for team involvement
                pr_data = self.process_pr(repo, pr)
                if pr_data and ("reviewer" in pr_data['team_involvement'] or "commenter" in pr_data['team_involvement']):
                    relevant_prs.append(pr_data)
            
            logging.info(f"Found {len(relevant_prs)} PRs with team involvement")
            return relevant_prs
            
        except Exception as e:
            logging.warning(f"Failed to get recent PRs: {e}")
            return []
    
    def is_pr_potentially_relevant(self, pr: Dict) -> bool:
        """Quick check if PR might be relevant before expensive processing"""
        if not pr.get('user') or not pr['user']:
            return False
            
        author = pr['user']['login']
        
        # If authored by team member, definitely relevant
        if author in self.config.team_members:
            return True
            
        # For non-team authors, only process if recently active
        updated_at = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
        if updated_at < self.cutoff_date:
            return False
            
        return True
    
    def process_pr(self, repo: str, pr: Dict) -> Optional[Dict]:
        """Process a single PR and determine if it's relevant"""
        pr_number = pr['number']
        
        # Handle deleted users or missing user data
        if not pr.get('user') or not pr['user']:
            logging.warning(f"PR #{pr_number} in {repo} has no user data, skipping")
            return None
        
        author = pr['user']['login']
        
        # Check if author is team member
        is_team_authored = author in self.config.team_members
        
        # Get comments and reviews to check team involvement
        comments = self.get_pr_comments(repo, pr_number)
        reviews = self.get_pr_reviews(repo, pr_number)
        
        team_commenters = set()
        team_reviewers = set()
        
        for comment in comments:
            if comment.get('user') and comment['user']:
                commenter = comment['user']['login']
                if commenter in self.config.team_members:
                    team_commenters.add(commenter)
        
        for review in reviews:
            if review.get('user') and review['user']:
                reviewer = review['user']['login']
                if reviewer in self.config.team_members:
                    team_reviewers.add(reviewer)
        
        # Determine team involvement
        team_involvement = []
        if is_team_authored:
            team_involvement.append("author")
        if team_reviewers:
            team_involvement.append("reviewer")
        if team_commenters:
            team_involvement.append("commenter")
        
        # Skip if no team involvement
        if not team_involvement:
            return None
        
        # Check if it's a recently merged PR or has recent activity
        updated_at = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
        is_recently_merged = (pr['state'] == 'closed' and pr['merged_at'] and 
                             datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00')) >= self.merge_cutoff_date)
        has_recent_activity = updated_at >= self.cutoff_date
        
        if not (is_recently_merged or has_recent_activity):
            return None
        
        # Calculate days since last activity
        days_since_activity = (datetime.now(timezone.utc) - updated_at).days
        
        # Get files changed
        files_data = self.get_pr_files(repo, pr_number)
        files_changed = len(files_data)
        key_files = [f['filename'] for f in files_data[:self.config.max_key_files]]
        
        return {
            "repo": repo,
            "number": pr_number,
            "title": pr['title'],
            "author": author,
            "url": pr['html_url'],
            "status": "merged" if pr['merged_at'] else pr['state'],
            "is_draft": pr['draft'],
            "created_at": pr['created_at'],
            "updated_at": pr['updated_at'],
            "merged_at": pr['merged_at'],
            "last_activity": pr['updated_at'],
            "comments": comments,
            "reviews": reviews,
            "team_involvement": ", ".join(team_involvement),
            "team_members_involved": list(set(team_commenters | team_reviewers | ({author} if is_team_authored else set()))),
            "files_changed": files_changed,
            "key_files": key_files,
            "labels": [label['name'] for label in pr['labels']],
            "assignees": [assignee['login'] for assignee in pr['assignees']],
            "days_since_activity": days_since_activity
        }
    
    def get_pr_comments(self, repo: str, pr_number: int) -> List[Dict]:
        """Get comments for a PR"""
        url = f"{self.github.base_url}/repos/{repo}/issues/{pr_number}/comments"
        comments = self.github.get_paginated_data(url)
        result = []
        for comment in comments:
            if comment.get('user') and comment['user']:
                result.append({
                    "author": comment['user']['login'],
                    "body": comment['body'][:self.config.max_comment_length],
                    "created_at": comment['created_at'],
                    "url": comment['html_url']
                })
        return result
    
    def get_pr_reviews(self, repo: str, pr_number: int) -> List[Dict]:
        """Get reviews for a PR"""
        url = f"{self.github.base_url}/repos/{repo}/pulls/{pr_number}/reviews"
        try:
            reviews = self.github.get_paginated_data(url)
            result = []
            for review in reviews:
                if review.get('user') and review['user']:
                    result.append({
                        "author": review['user']['login'],
                        "state": review['state'],
                        "body": review['body'][:self.config.max_comment_length] if review['body'] else "",
                        "submitted_at": review['submitted_at'],
                        "url": review['html_url']
                    })
            return result
        except GitHubAPIError:
            return []
    
    def get_pr_files(self, repo: str, pr_number: int) -> List[Dict]:
        """Get files changed in a PR"""
        url = f"{self.github.base_url}/repos/{repo}/pulls/{pr_number}/files"
        try:
            return self.github.get_paginated_data(url)
        except GitHubAPIError:
            return []
    
    def generate_summary_stats(self, all_prs: List[Dict]) -> Dict:
        """Generate summary statistics"""
        total_active_prs = len(all_prs)
        team_authored_prs = len([pr for pr in all_prs if "author" in pr['team_involvement']])
        team_reviewed_prs = len([pr for pr in all_prs if "reviewer" in pr['team_involvement']])
        stale_prs = len([pr for pr in all_prs if pr['days_since_activity'] > 7 and pr['status'] == 'open'])
        
        return {
            "total_active_prs": total_active_prs,
            "team_authored_prs": team_authored_prs,
            "team_reviewed_prs": team_reviewed_prs,
            "stale_prs": stale_prs,
            "open_prs": len([pr for pr in all_prs if pr['status'] == 'open']),
            "merged_prs": len([pr for pr in all_prs if pr['status'] == 'merged']),
            "draft_prs": len([pr for pr in all_prs if pr['is_draft']])
        }
    
    def collect_all_data(self) -> Dict:
        """Collect data from all repositories"""
        if not self.github.validate_token():
            raise GitHubAPIError("Invalid GitHub token")
        
        self.config.output_dir.mkdir(exist_ok=True)
        self.setup_logging()
        
        logging.info("Starting GitDigest data collection")
        
        all_prs = []
        for repo in self.config.repositories:
            try:
                prs = self.collect_pr_data(repo)
                all_prs.extend(prs)
            except Exception as e:
                logging.error(f"Failed to collect data for {repo}: {e}")
                continue
        
        summary_stats = self.generate_summary_stats(all_prs)
        
        result = {
            "generated_at": datetime.now().isoformat(),
            "team_members": self.config.team_members,
            "repositories": self.config.repositories,
            "pull_requests": all_prs,
            "summary_stats": summary_stats
        }
        
        logging.info(f"Collection complete. Found {len(all_prs)} relevant PRs")
        return result


def run_claude_analysis(data_file: Path, output_file: Path):
    """Run Claude Code analysis on the collected data"""
    logging.info("Running Claude Code analysis...")
    
    prompt = f"""
    Please analyze the GitHub PR data in {data_file} and generate a comprehensive daily digest for the Vault team.
    
    Create a well-formatted markdown report that includes:
    
    1. **Executive Summary** - Key metrics and highlights
    2. **Active Pull Requests** - PRs that need attention, grouped by priority
    3. **Team Activity** - What each team member has been working on
    4. **Stale Items** - PRs that haven't had activity recently
    5. **Recent Completions** - Recently merged PRs
    6. **Action Items** - Things that need immediate attention
    
    Focus on actionable insights and highlight blockers or PRs that need reviews.
    Use clear formatting with bullet points, tables where helpful, and emoji indicators for status.
    
    Save the analysis to {output_file}
    """
    
    try:
        result = subprocess.run([
            "claude", "code", "--prompt", prompt
        ], capture_output=True, text=True, check=True)
        
        logging.info(f"Claude analysis completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Claude analysis failed: {e}")
        logging.error(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        logging.error("Claude Code not found. Please install Claude Code CLI first.")
        return False


def main():
    """Main entry point"""
    config = Config.from_file()
    
    if not config.github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    try:
        collector = GitDigestCollector(config)
        data = collector.collect_all_data()
        
        # Save data
        timestamp = datetime.now().strftime("%Y-%m-%d")
        data_file = config.output_dir / f"vault-team-data-{timestamp}.json"
        
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data collection complete. Saved to: {data_file}")
        
        # Run Claude analysis
        digest_file = config.output_dir / f"vault-team-digest-{timestamp}.md"
        if run_claude_analysis(data_file, digest_file):
            print(f"Digest generated: {digest_file}")
        else:
            print("Failed to generate digest. You can manually analyze the JSON data.")
    
    except Exception as e:
        logging.error(f"GitDigest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()