#!/bin/bash
# Daily GitDigest automation script
# This script ensures the digest runs reliably every day

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$SCRIPT_DIR/output/automation.log"
DATE=$(date '+%Y-%m-%d')

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to send notification (customize as needed)
notify() {
    local status=$1
    local message=$2
    log "$status: $message"
    
    # Uncomment and customize for your notification system:
    # echo "$message" | mail -s "GitDigest $status" your-email@company.com
    # curl -X POST -H 'Content-type: application/json' --data '{"text":"GitDigest '"$status"': '"$message"'"}' YOUR_SLACK_WEBHOOK_URL
}

log "Starting GitDigest automation for $DATE"

# Change to script directory
cd "$SCRIPT_DIR"

# Check if GitHub token is set
if [ -z "$GITHUB_TOKEN" ]; then
    notify "FAILED" "GITHUB_TOKEN environment variable not set"
    exit 1
fi

# Check if required files exist
if [ ! -f "run_digest.py" ]; then
    notify "FAILED" "run_digest.py not found in $SCRIPT_DIR"
    exit 1
fi

# Run the digest with timeout protection
log "Running GitDigest data collection and analysis..."

# Set a maximum runtime of 20 minutes (1200 seconds)
timeout 1200 python3 run_digest.py > "$SCRIPT_DIR/output/run-$DATE.log" 2>&1
RESULT=$?

if [ $RESULT -eq 0 ]; then
    # Success - check if files were created
    # Read filename templates from config.json
    DATA_TEMPLATE=$(python3 -c "import json; data=json.load(open('$SCRIPT_DIR/config.json')); print(data.get('output', {}).get('data_filename_template', 'team-data-{date}.json'))" 2>/dev/null || echo "team-data-{date}.json")
    DIGEST_TEMPLATE=$(python3 -c "import json; data=json.load(open('$SCRIPT_DIR/config.json')); print(data.get('output', {}).get('digest_filename_template', 'team-digest-{date}.md'))" 2>/dev/null || echo "team-digest-{date}.md")

    # Replace {date} placeholder with actual date
    DATA_FILE="$SCRIPT_DIR/output/${DATA_TEMPLATE//\{date\}/$DATE}"
    DIGEST_FILE="$SCRIPT_DIR/output/${DIGEST_TEMPLATE//\{date\}/$DATE}"
    
    if [ -f "$DATA_FILE" ] && [ -f "$DIGEST_FILE" ]; then
        # Count PRs found
        PR_COUNT=$(python3 -c "import json; data=json.load(open('$DATA_FILE')); print(data['summary_stats']['total_active_prs'])" 2>/dev/null || echo "unknown")
        notify "SUCCESS" "GitDigest completed successfully. Found $PR_COUNT active PRs. Files: $DATA_FILE, $DIGEST_FILE"
        
        # Optionally copy digest to a shared location
        # cp "$DIGEST_FILE" /shared/team-reports/
        
    else
        notify "PARTIAL" "GitDigest completed but output files missing. Check logs: $SCRIPT_DIR/output/run-$DATE.log"
        exit 1
    fi
    
elif [ $RESULT -eq 124 ]; then
    # Timeout
    notify "TIMEOUT" "GitDigest timed out after 20 minutes. Check for hanging processes."
    # Kill any remaining processes
    pkill -f "python3.*digest" || true
    exit 1
    
else
    # Other error
    notify "FAILED" "GitDigest failed with exit code $RESULT. Check logs: $SCRIPT_DIR/output/run-$DATE.log"
    exit 1
fi

log "GitDigest automation completed successfully"