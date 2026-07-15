# Tasks: Windows Server Watchdog

## Specification

- [x] T001 Document automatic startup, watchdog recovery, and safe-update behavior
- [x] T002 Add the Windows availability rule to `PROTECTED_RULES.md`

## Implementation

- [x] T003 Add one-time Scheduled Task registration to the PowerShell runner
- [x] T004 Configure startup/logon triggers and indefinite restart-on-failure
- [x] T005 Separate frequent server health checks from Git update checks
- [x] T006 Prepare updates before stopping the working server
- [x] T007 Adopt an existing process already listening on the configured port
- [x] T010 Route legacy manual launch/update entry points through the watchdog

## Verification and Documentation

- [x] T008 Update `WINDOWS_SERVER.md` with the one-time administrator workflow
- [x] T009 Perform static verification and document required Windows validation
