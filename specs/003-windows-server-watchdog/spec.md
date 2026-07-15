# Feature Specification: Windows Server Watchdog

**Feature Branch**: `003-windows-server-watchdog`
**Created**: 2026-07-15
**Status**: Complete
**Input**: The Windows deployment must start automatically after reboot and
recover when either the report server or its update runner stops unexpectedly.

## User Scenarios & Testing

### User Story 1 - Automatic Startup and Recovery (Priority: P1)

As the server operator, I need a one-time PowerShell setup to register the app
with Windows Task Scheduler so the server starts after reboot and is restarted
when it crashes without requiring an open desktop window.

**Independent Test**: Inspect the registered task and verify it has startup and
logon triggers, no execution time limit, and repeated restart-on-failure policy.

**Acceptance Scenarios**:

1. **Given** the task is not installed, **When** an administrator runs the
   PowerShell runner, **Then** it prompts once for the Windows account credential,
   registers the task, starts it, and exits the temporary console runner.
2. **Given** Windows restarts, **When** Task Scheduler starts, **Then** the update
   runner starts the report server without an interactive PowerShell window.
3. **Given** the report server exits unexpectedly, **When** the watchdog checks
   process health, **Then** the server restarts within approximately 10 seconds.
4. **Given** the watchdog itself exits, **When** Task Scheduler detects failure,
   **Then** Windows restarts it repeatedly without a finite execution timeout.

### User Story 2 - Updates Do Not Cause Avoidable Downtime (Priority: P1)

As the server operator, I need transient GitHub or dependency failures to leave
the currently working server running rather than stopping it first.

**Independent Test**: Review the update sequence and verify fetch, sync, and
dependency preparation occur before the running server is stopped.

**Acceptance Scenarios**:

1. **Given** GitHub is temporarily unavailable, **When** an update check fails,
   **Then** the failure is logged and the existing server continues running.
2. **Given** an update and dependency installation succeed, **When** preparation
   finishes, **Then** the server restarts onto the new revision.
3. **Given** a server already owns the configured port after watchdog recovery,
   **When** the watchdog starts, **Then** it adopts and monitors that process
   instead of starting a duplicate.

## Requirements

- **FR-001**: The runner MUST be able to register itself as a Windows Scheduled
  Task using the current Windows user and stored Task Scheduler credentials.
- **FR-002**: Registration MUST require an elevated one-time setup and MUST NOT
  store Windows credentials, GitHub keys, or application secrets in repository
  files.
- **FR-003**: The task MUST trigger at Windows startup and user logon, start when
  available, run without a time limit, ignore duplicate starts, and restart on
  failure every minute for a large retry count.
- **FR-004**: The watchdog MUST check server process health more frequently than
  it checks for Git updates.
- **FR-005**: A failed update check or dependency installation MUST NOT stop a
  currently running server.
- **FR-006**: Runtime JSON and other ignored operational state MUST remain
  untouched by repository synchronization.

## Success Criteria

- **SC-001**: One administrator-run command installs and starts the scheduled
  watchdog.
- **SC-002**: Server process recovery occurs within 15 seconds of an unexpected
  exit while the watchdog is running.
- **SC-003**: Task Scheduler retries a failed watchdog for at least 24 hours.
- **SC-004**: Static verification finds startup/logon triggers, restart policy,
  zero execution time limit, duplicate suppression, and update-before-stop order.
