#!/bin/bash
# GitDigest Setup Script

set -e

echo "🚀 Setting up GitDigest..."

# Check if we're in the right directory
if [[ ! -f "gitdigest.py" ]]; then
    echo "❌ Please run this script from the GitDigest directory"
    exit 1
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is available
if ! python3 -m pip --version &> /dev/null; then
    echo "❌ pip is required but not available"
    exit 1
fi

# Install requirements
echo "📦 Installing Python requirements..."
python3 -m pip install -r requirements.txt

# Check for Claude Code
if ! command -v claude &> /dev/null; then
    echo "⚠️  Claude Code CLI not found"
    echo "Please install Claude Code from: https://docs.anthropic.com/en/docs/claude-code"
    echo "GitDigest will still collect data, but won't generate digests automatically"
else
    echo "✅ Claude Code CLI found"
fi

# Check for GitHub token
if [[ -z "${GITHUB_TOKEN}" ]]; then
    echo "⚠️  GITHUB_TOKEN environment variable not set"
    echo "Please set your GitHub token:"
    echo "  export GITHUB_TOKEN=your_token_here"
    echo "Or add it to your shell profile (.bashrc, .zshrc, etc.)"
else
    echo "✅ GitHub token found"
fi

# Create output directory
mkdir -p output

# Make scripts executable
chmod +x gitdigest.py
chmod +x run_digest.py
chmod +x claude_analyzer.py

echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Set your GitHub token: export GITHUB_TOKEN=your_token_here"
echo "2. Run a test: python3 run_digest.py"
echo "3. Set up daily automation (see automation/ directory)"

# Create automation directory and scripts
mkdir -p automation

# Create cron example
cat > automation/cron_example.txt << 'EOF'
# Example cron job to run GitDigest daily at 9 AM
# Edit with: crontab -e
# Add this line:

0 9 * * * cd /path/to/GitDigest && /usr/bin/python3 run_digest.py >> output/cron.log 2>&1

# To see current cron jobs: crontab -l
# To remove all cron jobs: crontab -r
EOF

# Create systemd service example (Linux)
cat > automation/gitdigest.service << 'EOF'
[Unit]
Description=GitDigest daily report
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/GitDigest
Environment=GITHUB_TOKEN=your_token_here
ExecStart=/usr/bin/python3 run_digest.py
StandardOutput=append:/path/to/GitDigest/output/service.log
StandardError=append:/path/to/GitDigest/output/service.log

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer (Linux)
cat > automation/gitdigest.timer << 'EOF'
[Unit]
Description=Run GitDigest daily
Requires=gitdigest.service

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF

# Create Windows Task Scheduler XML
cat > automation/windows_task.xml << 'EOF'
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>2025-01-01T00:00:00</Date>
    <Author>GitDigest</Author>
    <Description>Daily GitDigest report generation</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2025-01-01T09:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>python3</Command>
      <Arguments>run_digest.py</Arguments>
      <WorkingDirectory>C:\path\to\GitDigest</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
EOF

# Create macOS LaunchAgent plist
cat > automation/com.gitdigest.daily.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gitdigest.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/GitDigest/run_digest.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/GitDigest</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>GITHUB_TOKEN</key>
        <string>your_token_here</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/path/to/GitDigest/output/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/GitDigest/output/launchd.log</string>
</dict>
</plist>
EOF

echo "📁 Automation examples created in automation/ directory"
echo "📝 See README.md for detailed setup instructions"