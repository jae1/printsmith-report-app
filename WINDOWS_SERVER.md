# Windows Server Operation

The Windows server is an execution-only machine. Development happens elsewhere.
The watchdog fetches `origin/main`, prepares isolated releases, and switches only
after regression and accounting checks pass. Runtime JSON stays in the original
directory. See [RELEASING.md](RELEASING.md) for baseline approval, migration,
version verification, and rollback.

## One-Time Automatic Setup

1. Sign in using the Windows account that already has GitHub access for this
   repository.
2. Right-click **Windows PowerShell** and choose **Run as administrator**.
3. Change to the repository folder.
4. Run:

```powershell
.\run_server_auto_update.ps1
```

5. Enter that Windows account's password when prompted. Windows Task Scheduler
   stores the credential; the script does not save it in the repository.

The setup creates and starts a task named `PrintSmith Report Server Watchdog`.
The temporary administrator window can close after setup finishes.

If the Windows password changes or the task needs to be rebuilt, run:

```powershell
.\run_server_auto_update.ps1 -ReinstallScheduledTask
```

## Always-On Behavior

The scheduled watchdog:

- Starts at Windows startup and user logon
- Runs whether or not a desktop window remains open
- Has no execution time limit
- Is restarted by Task Scheduler every two minutes if the watchdog fails
- Checks the report server every 10 seconds and restarts it after a crash
- Adopts an existing server already listening on port `8000`
- Verifies the process identity before adopting it; unrelated listeners are
  reported as port conflicts and are never stopped
- Checks `origin/main` every 10 minutes
- Keeps the working server online and monitored while isolated source,
  dependencies, tests, and accounting comparison are prepared
- Restarts onto an update only after preparation succeeds, verifies its health
  and revision, and restores the previous release if validation fails
- Retries failed updates after two minutes
- Writes watchdog activity to `server_auto_update.log`

To use different intervals during initial installation:

```powershell
.\run_server_auto_update.ps1 -CheckIntervalSeconds 300 -HealthCheckIntervalSeconds 10
```

## Check for an Update Immediately

After the watchdog is installed, run:

```powershell
.\update_now_and_restart.ps1
```

This signals the running watchdog to check immediately. The existing report
server remains online while the watchdog checks and prepares the update.

## Verify It on Windows

```powershell
Get-ScheduledTask -TaskName "PrintSmith Report Server Watchdog"
Get-ScheduledTaskInfo -TaskName "PrintSmith Report Server Watchdog"
Get-Content .\server_auto_update.log -Tail 50
```

The task state should be `Running`. After a controlled reboot, confirm that
`http://localhost:8000` loads without manually opening PowerShell.

## Important Notes

- The scheduled Windows account must have working GitHub SSH access without an
  interactive passphrase prompt. Test with `git fetch origin main` while signed
  in as that account.
- Local code changes are not deployed; application releases use the fetched
  remote revision. Controller updates require the maintenance steps in
  `RELEASING.md`.
- `app_settings.json`, `daily_spending.json`, `hidden_invoices.json`, logs, and
  other ignored runtime files are not overwritten by `git reset --hard`.
- Do not run a second copy of the server manually; the watchdog owns port `8000`.
- Keep `.release-baseline.json`, `.server-release.json`, and `.releases/` local
  and untracked. A new deployment without an approved baseline is blocked.
