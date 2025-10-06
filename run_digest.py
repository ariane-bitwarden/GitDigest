#!/usr/bin/env python3
"""
Main runner script with configuration file support
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Import our modules
from gitdigest import GitDigestCollector, Config
from claude_analyzer import ClaudeAnalyzer


def main():
    """Main entry point with configuration file support"""
    # Parse command line arguments
    config_file = None
    if len(sys.argv) > 1:
        config_file = Path(sys.argv[1])
    
    # Load configuration
    config = Config.from_file(config_file)
    
    if not config.github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("Please set your GitHub token: export GITHUB_TOKEN=your_token_here")
        sys.exit(1)
    
    # Create output directory
    config.output_dir.mkdir(exist_ok=True)
    
    # Setup logging - reset log file on each run
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(config.output_dir / "gitdigest.log", mode='w'),  # 'w' mode overwrites
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    try:
        print("🚀 Starting GitDigest data collection...")
        
        # Collect data
        collector = GitDigestCollector(config)
        data = collector.collect_all_data()
        
        # Save data with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d")
        data_filename = config.data_filename_template.format(date=timestamp)
        digest_filename = config.digest_filename_template.format(date=timestamp)
        
        data_file = config.output_dir / data_filename
        digest_file = config.output_dir / digest_filename
        
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Data collection complete: {data_file}")
        print(f"📊 Found {data['summary_stats']['total_active_prs']} relevant PRs")
        
        # Generate digest using appropriate generator based on config
        digest_type = config.digest_type
        print(f"📝 Generating {digest_type} digest...")
        
        if digest_type == "engineer":
            digest_generator = Path(__file__).parent / "engineer_digest.py"
        else:  # default to manager
            digest_generator = Path(__file__).parent / "manager_digest.py"
        
        import subprocess
        try:
            result = subprocess.run([
                sys.executable, str(digest_generator),
                str(data_file), str(digest_file)
            ], capture_output=True, text=True, timeout=60)  # 60 second timeout for digest generation
        except subprocess.TimeoutExpired:
            print("❌ Digest generation timed out")
            result = None
        
        digest_generated = False
        if result and result.returncode == 0:
            print(f"✅ Digest generated: {digest_file}")
            digest_generated = True
            
            # Add Claude analysis for both digest types
            print("🤖 Adding Claude analysis...")
            try:
                analyzer = ClaudeAnalyzer(data_file, digest_file, digest_type)
                success = analyzer.generate_digest()
                
                if success:
                    print("✅ Claude analysis added")
                else:
                    print("⚠️ Claude analysis failed, continuing without it")
                    
            except Exception as e:
                print(f"⚠️ Claude analysis error: {e}")
        else:
            error_msg = result.stderr if result else "Process timed out"
            print(f"❌ Digest generation failed: {error_msg}")
        
        if digest_generated:
            print("\n🎯 Daily digest is ready!")
            
            # Show quick stats
            stats = data['summary_stats']
            print(f"\n📈 Quick Stats:")
            print(f"  • Total active PRs: {stats['total_active_prs']}")
            print(f"  • Team authored: {stats['team_authored_prs']}")
            print(f"  • Team reviewed: {stats['team_reviewed_prs']}")
            print(f"  • Stale PRs (>7 days): {stats['stale_prs']}")
            print(f"  • Open PRs: {stats['open_prs']}")
            print(f"  • Recently merged: {stats['merged_prs']}")
        else:
            print("⚠️  All digest generation methods failed")
            print(f"📄 Raw data available at: {data_file}")
    
    except Exception as e:
        logging.error(f"GitDigest failed: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()