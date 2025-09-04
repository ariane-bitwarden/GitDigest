#!/usr/bin/env python3
"""
Test script to verify GitDigest setup
"""

import os
import sys
import json
from pathlib import Path

def test_imports():
    """Test that all modules can be imported"""
    try:
        import requests
        print("✅ requests library available")
    except ImportError:
        print("❌ requests library not found - run: pip install requests")
        return False
    
    try:
        from gitdigest import GitDigestCollector, Config
        print("✅ gitdigest module imports successfully")
    except ImportError as e:
        print(f"❌ gitdigest module import failed: {e}")
        return False
    
    try:
        from claude_analyzer import ClaudeAnalyzer
        print("✅ claude_analyzer module imports successfully")
    except ImportError as e:
        print(f"❌ claude_analyzer module import failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration file"""
    config_file = Path(__file__).parent / "config.json"
    
    if not config_file.exists():
        print("❌ config.json not found")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        required_keys = ["team_members", "repositories", "settings", "output", "github"]
        for key in required_keys:
            if key not in config:
                print(f"❌ Missing key in config.json: {key}")
                return False
        
        print(f"✅ config.json is valid")
        print(f"   - {len(config['team_members'])} team members")
        print(f"   - {len(config['repositories'])} repositories")
        
    except json.JSONDecodeError as e:
        print(f"❌ config.json is invalid JSON: {e}")
        return False
    
    return True

def test_github_token():
    """Test GitHub token"""
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("   Set it with: export GITHUB_TOKEN=your_token_here")
        return False
    
    if len(token) < 20:
        print("⚠️  GITHUB_TOKEN seems too short - verify it's correct")
        return False
    
    print("✅ GITHUB_TOKEN is set")
    return True

def test_claude_code():
    """Test Claude Code CLI"""
    import subprocess
    
    try:
        result = subprocess.run(['claude', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Claude Code CLI is available")
            return True
        else:
            print("⚠️  Claude Code CLI found but returned error")
            return False
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️  Claude Code CLI not found - digest generation will be skipped")
        print("   Install from: https://docs.anthropic.com/en/docs/claude-code")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing GitDigest setup...\n")
    
    tests = [
        ("Python imports", test_imports),
        ("Configuration file", test_config),
        ("GitHub token", test_github_token),
        ("Claude Code CLI", test_claude_code),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        results.append(test_func())
    
    print("\n" + "="*50)
    print("🎯 Test Summary:")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} tests passed! GitDigest is ready to use.")
        print("\n🚀 Next steps:")
        print("1. Run: python3 run_digest.py")
        print("2. Check output/ directory for results")
    else:
        print(f"⚠️  {passed}/{total} tests passed. Please fix the issues above.")
        
        if not results[2]:  # GitHub token test failed
            print("\n⚠️  Critical: GitHub token is required for GitDigest to work")
        
    print("\n📚 For help, see README.md")

if __name__ == "__main__":
    main()