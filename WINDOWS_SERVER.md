# Windows Server Operation

The Windows server is an execution-only machine. Development happens elsewhere,
and this machine should force-sync to `origin/main`.

## Automatic Updates

Run this from PowerShell in the repository folder:

```powershell
.\run_server_auto_update.ps1
```

Default behavior:

- Starts the app on `0.0.0.0:8000`
- Checks `origin/main` every 10 minutes
- If a new commit exists, stops the server, runs `git reset --hard origin/main`,
  installs dependencies, and starts the server again
- Writes logs to `server_auto_update.log`

To use a different interval:

```powershell
.\run_server_auto_update.ps1 -CheckIntervalSeconds 300
```

## Manual Immediate Update

When you do not want to wait for the next automatic check, run:

```powershell
.\update_now_and_restart.ps1
```

This stops anything listening on port `8000`, force-syncs to `origin/main`,
installs dependencies, and starts the server.

## Notes

- Any local code changes on the Windows server will be overwritten.
- Local runtime JSON files such as `app_settings.json`, `daily_spending.json`,
  and `hidden_invoices.json` are ignored by git and are not overwritten by
  `git reset --hard`.
- Keep the PowerShell window open while the server is running, unless this is
  later registered as a Windows Scheduled Task or service.
