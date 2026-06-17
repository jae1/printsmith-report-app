# Agent Role System for PrintSmith Report App

Welcome! This directory defines the specialized agent system for maintaining the PrintSmith Report App. 
When an AI assistant (like Gemini or Antigravity) starts working on this project, it must read the configuration here to adopt the correct role.

## Active Agents

Select the agent profile corresponding to your current task:

1. **Coordinator Agent** (Guardrails & Verification)
   - [Coordinator Profile](file:///Users/onp/printsmith-report-app/.agents/1_coordinator.md)
   - Scope: [GEMINI.md](file:///Users/onp/printsmith-report-app/GEMINI.md), `tests/`
2. **SQL & Report Logic Agent** (Core Database Query Expert)
   - [SQL & Report Logic Profile](file:///Users/onp/printsmith-report-app/.agents/2_sql_report_logic.md)
   - Scope: [app/services/report_service.py](file:///Users/onp/printsmith-report-app/app/services/report_service.py), [app/services/hide_service.py](file:///Users/onp/printsmith-report-app/app/services/hide_service.py), [app/db/database.py](file:///Users/onp/printsmith-report-app/app/db/database.py)
3. **Expense Parser & Sync Agent** (Email & Expense Expert)
   - [Expense Parser Profile](file:///Users/onp/printsmith-report-app/.agents/3_expense_parser_sync.md)
   - Scope: [app/services/expense_parser_service.py](file:///Users/onp/printsmith-report-app/app/services/expense_parser_service.py), [app/services/spending_service.py](file:///Users/onp/printsmith-report-app/app/services/spending_service.py)
4. **Web UI & Experience Agent** (Frontend & Interaction Expert)
   - [Web UI Profile](file:///Users/onp/printsmith-report-app/.agents/4_web_ui.md)
   - Scope: `app/templates/`, [app/services/export_service.py](file:///Users/onp/printsmith-report-app/app/services/export_service.py)
5. **SysOps & Email Delivery Agent** (Automation & Deployment Expert)
   - [SysOps Profile](file:///Users/onp/printsmith-report-app/.agents/5_sysops_email.md)
   - Scope: [app/main.py](file:///Users/onp/printsmith-report-app/app/main.py), [app/services/email_service.py](file:///Users/onp/printsmith-report-app/app/services/email_service.py), [app/services/settings_service.py](file:///Users/onp/printsmith-report-app/app/services/settings_service.py)

---

## How to use the CLI Tool
You can run the interactive CLI tool to get prompt templates or check file ownership:
```bash
python agent_selector.py --help
```
