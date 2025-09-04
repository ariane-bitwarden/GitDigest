# GitDigest - GitHub Activity Data Collection & Analysis

A tool that collects GitHub activity data for your development team and automatically generates daily summaries with engineering insights.

## 🚀 Quick Start

1. **Set up your environment:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Configure your team and repositories:**
   ```bash
   cp config_template.json config.json
   # Edit config.json with your team members and repositories
   ```

3. **Set your GitHub token:**
   ```bash
   export GITHUB_TOKEN=your_github_token_here
   ```

4. **Run GitDigest:**
   ```bash
   python3 run_digest.py
   ```

## 📋 Requirements

- Python 3.7+
- GitHub token with repo access
- Claude Code CLI (optional, for automated digest generation)

## 🔧 Configuration

Copy `config_template.json` to `config.json` and customize:

- **Team members**: Add your team's GitHub usernames
- **Repositories**: Add repos to monitor in "owner/repo" format
- **Time ranges**: Adjust activity and merge timeframes
- **Output settings**: Customize file naming and location

Example config.json:
```json
{
  "team_members": ["alice", "bob", "charlie"],
  "repositories": ["myorg/backend", "myorg/frontend"],
  "settings": {
    "activity_days": 7,
    "recent_merge_days": 2,
    "digest_type": "manager"
  }
}
```

## 📊 What It Collects

For each repository, GitDigest finds PRs where team members are involved as:
- **Authors** - PRs created by team members
- **Reviewers** - PRs reviewed by team members  
- **Commenters** - PRs with team member comments

### Data Collected Per PR:
- Basic info (title, number, URL, author, dates)
- Status (open/closed/merged, draft status)
- All comments and reviews with timestamps
- Files changed and key modified files
- Labels, assignees, and team involvement
- Time since last activity

### Filtering Rules:
- PRs with activity in last 7 days (configurable)
- Recently merged PRs (last 2 days, configurable)
- Only PRs with team member involvement

## 📁 Output Files

- **Raw data**: `output/team-data-YYYY-MM-DD.json`
- **Daily digest**: `output/team-digest-YYYY-MM-DD.md`
- **Logs**: `output/gitdigest.log`

## 📊 Digest Types

GitDigest generates different digest formats based on your role:

### 👔 Manager Digest (`"digest_type": "manager"`)
- **Executive Summary** - Team velocity, review health, workload overview
- **🚨 Immediate Intervention Needed** - Critical PRs, communication issues
- **⚠️ Monitoring Situations** - Large PRs, team workload, approaching deadlines  
- **🎯 Key Manager Actions** - Specific recommendations for process and team management
- **📋 Detailed PR Status** - Complete team activity and recent completions

### 👨‍💻 Engineer Digest (`"digest_type": "engineer"`)
- **At a Glance** - Quick PR counts and status overview
- **🔥 High Priority** - Critical/urgent items needing immediate action
- **👀 Ready for Review** - PRs waiting for team reviews
- **⚠️ Needs Attention** - Large PRs, getting stale, follow-up needed
- **✅ Recently Shipped** - What just merged
- **📊 By Repository** - Engineering-focused repo breakdown

Configure the digest type in your `config.json` settings.

## 🔒 Security Features

- GitHub token stored as environment variable
- API rate limiting with automatic retries
- Input validation and error handling
- No sensitive data logged
- Token permissions validated before execution

## 📅 Daily Automation (macOS)

### LaunchAgent Setup

1. Add your GitHub token to your shell profile:
   ```bash
   echo 'export GITHUB_TOKEN=your_token_here' >> ~/.bashrc
   ```

2. Copy and configure the plist file:
   ```bash
   cp automation/com.gitdigest.daily.plist ~/Library/LaunchAgents/
   # Edit the file paths in the plist to match your GitDigest location
   nano ~/Library/LaunchAgents/com.gitdigest.daily.plist
   ```

3. Load the service:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.gitdigest.daily.plist
   ```

The digest will run daily at 9:00 AM and pull the GitHub token from your `~/.bashrc`.

## 🛠️ Troubleshooting

### Common Issues:

**"Invalid GitHub token"**
- Ensure token has `repo` scope
- Check token hasn't expired
- Verify token is set: `echo $GITHUB_TOKEN`

**"Rate limit exceeded"** 
- Tool automatically waits for rate limit reset
- Consider running during off-peak hours

**"No data collected"**
- Check team member usernames in config
- Verify repositories exist and are accessible
- Review date ranges in configuration

**"LaunchAgent not running"**
- Check if loaded: `launchctl list | grep gitdigest`
- View logs: `tail -f ~/Library/Logs/com.gitdigest.daily.log`
- Verify file paths in plist are correct

### Logs
Check `output/gitdigest.log` for detailed error information.

## 🔧 Advanced Usage

### Custom Configuration File:
```bash
python3 run_digest.py path/to/custom/config.json
```

### Data-Only Mode (Skip Digest):
```bash
python3 gitdigest.py
```

### Generate Digest from Existing Data:
```bash
python3 claude_analyzer.py output/vault-team-data-2025-01-15.json output/custom-digest.md
```

## 📈 Sample Output Structure

```json
{
  "generated_at": "2025-09-04T09:00:00Z",
  "team_members": ["Jingo88", "shane-melton", ...],
  "repositories": ["bitwarden/server", ...],
  "pull_requests": [
    {
      "repo": "bitwarden/server",
      "number": 123,
      "title": "Fix vault encryption bug",
      "author": "Jingo88",
      "status": "open",
      "team_involvement": "author",
      "days_since_activity": 1,
      "files_changed": 5,
      "comments": [...],
      "reviews": [...]
    }
  ],
  "summary_stats": {
    "total_active_prs": 15,
    "team_authored_prs": 8,
    "stale_prs": 3
  }
}
```

## 🤝 Support

For issues or feature requests, check the logs first, then review the configuration. Most issues are related to:

1. GitHub token permissions
2. Network connectivity
3. Repository access
4. Claude Code installation

## 📄 License

This tool is provided as-is for internal team use. Ensure compliance with your organization's security policies before use.