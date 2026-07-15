#!/usr/bin/env python
import argparse
import os
import sys

AGENT_MAPPING = {
    "coordinator": {
        "name": "Coordinator Agent",
        "file": ".agents/1_coordinator.md",
        "patterns": ["PROTECTED_RULES.md", "README.md", "tests/"]
    },
    "sql_logic": {
        "name": "SQL & Report Logic Agent",
        "file": ".agents/2_sql_report_logic.md",
        "patterns": ["report_service.py", "hide_service.py", "database.py", "check_db.py"]
    },
    "expense_parser": {
        "name": "Expense Parser & Sync Agent",
        "file": ".agents/3_expense_parser_sync.md",
        "patterns": ["expense_parser_service.py", "spending_service.py", "daily_spending.json", "processed_receipts.json"]
    },
    "web_ui": {
        "name": "Web UI & Experience Agent",
        "file": ".agents/4_web_ui.md",
        "patterns": ["templates/", "static/", "export_service.py"]
    },
    "sysops": {
        "name": "SysOps & Email Delivery Agent",
        "file": ".agents/5_sysops_email.md",
        "patterns": [
            "main.py",
            "email_service.py",
            "settings_service.py",
            "app_settings.json",
            "requirements.txt",
            "run_server_auto_update.ps1",
            "update_now_and_restart.ps1",
            "setup_and_run.bat",
            "WINDOWS_SERVER.md",
            "windows-server-watchdog",
        ]
    }
}

def print_agents():
    print("=== PrintSmith Report App - AI Agent Rosters ===")
    for key, info in AGENT_MAPPING.items():
        print(f"\n[{key.upper()}] - {info['name']}")
        print(f"  Profile Config: {info['file']}")
        print(f"  Monitored scopes: {', '.join(info['patterns'])}")

def recommend_agent(filepaths):
    print("=== File Path Analysis & Agent Routing ===")
    recommendations = {}
    
    for path in filepaths:
        matched = False
        for key, info in AGENT_MAPPING.items():
            for pattern in info['patterns']:
                if pattern in path:
                    recommendations.setdefault(key, []).append(path)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            recommendations.setdefault("coordinator", []).append(path)
            
    for agent_key, files in recommendations.items():
        agent_info = AGENT_MAPPING[agent_key]
        print(f"\n🤖 Recommended Agent: {agent_info['name']} (Key: {agent_key})")
        print(f"   Reason: Assigned to handle files:")
        for f in files:
            print(f"    - {f}")

def main():
    parser = argparse.ArgumentParser(description="PrintSmith Report App - Agent Router CLI")
    parser.add_argument("--list", action="store_true", help="List all available agents and their boundaries")
    parser.add_argument("--recommend", nargs="+", help="Recommend an agent based on one or more target file paths")
    parser.add_argument("--load", choices=AGENT_MAPPING.keys(), help="Load the instructions of a specific agent")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.list:
        print_agents()
    elif args.recommend:
        recommend_agent(args.recommend)
    elif args.load:
        agent_info = AGENT_MAPPING[args.load]
        profile_path = os.path.join(os.path.dirname(__file__), agent_info['file'])
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print(f"Error: Profile file not found at {profile_path}")

if __name__ == "__main__":
    main()
