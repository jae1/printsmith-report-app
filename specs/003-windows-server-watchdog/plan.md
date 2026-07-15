# Implementation Plan: Windows Server Watchdog

**Branch**: `003-windows-server-watchdog` | **Date**: 2026-07-15
**Spec**: `specs/003-windows-server-watchdog/spec.md`

## Summary

Extend `run_server_auto_update.ps1` into a self-registering Task Scheduler
watchdog. The scheduled task runs under the server operator's Windows account
so existing GitHub SSH credentials remain available, starts at boot/logon,
restarts on failure, and has no execution time limit. Separate 10-second process
health checks from the 10-minute update interval and prepare updates before
stopping the working server.

## Constitution Check

- [x] Protected report/accounting behavior is untouched
- [x] Runtime credentials remain outside source control
- [x] Thread/async guardrails remain intact
- [x] Windows operational behavior traces to a feature spec
- [x] SysOps role reviewed

## Files

```text
run_server_auto_update.ps1
update_now_and_restart.ps1
setup_and_run.bat
WINDOWS_SERVER.md
PROTECTED_RULES.md
specs/003-windows-server-watchdog/
```

## Verification

PowerShell is not installed in the development environment, so verification is
limited to source inspection, delimiter/structure checks, diff checks, and
documented Windows-side validation commands. The Windows server must perform the
final Scheduled Task and reboot validation.
