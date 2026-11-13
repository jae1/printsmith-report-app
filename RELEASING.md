# Regression checks and releases

Every accounting fix must include a regression that fails before the fix. Keep
the earlier cases when adding a new case; changing expected values requires an
explanation in the active feature spec. A green test run is necessary, but a
review of changed report amounts is also required.

## Development checks

Run the deterministic suite without a database or mailbox:

```sh
python -m unittest discover -s tests -v
```

The eight existing live payment tests are explicitly skipped in this mode.
The synthetic relational fixtures exercise the production report SQL and
aggregation, including estimates sharing invoice numbers, prior deposits,
partial/final payments, linked and multi-method batches, deposit returns,
classification, subsidiary exclusions, and date-scoped hiding. The SQLite
adapter translates syntax only; live PostgreSQL remains a separate check.

Run the live payment checks with read-only database access:

```powershell
$env:PRINTSMITH_LIVE_TESTS = "1"
$env:PGOPTIONS = "-c default_transaction_read_only=on -c statement_timeout=30000"
$env:PGCONNECT_TIMEOUT = "10"
python -m unittest discover -s tests -p test_batch_payment.py -v
```

`release_check.py` sets these variables automatically for its live subprocess.
Missing tests, skipped live tests, query failures, or failed assertions block a
release. No release check sends email or synchronizes receipts.

## CI and repository settings

`.github/workflows/regression-tests.yml` runs offline checks on pushes and pull
requests. It needs no production database or secrets. PowerShell control-flow
tests use mocked processes and HTTP responses; they do not operate the server.

After publishing the workflow, a repository administrator must require its
`Offline accounting and release regressions` check on `main`, require pull
requests with code-owner review, and disallow bypasses for normal updates.
`.github/CODEOWNERS` assigns accounting and release safeguards to the repository
owner. Preserve any other existing
required checks. The account used for this implementation has push access but
not administrator access, so remote branch protection cannot be enabled here.
The server-side release gate still independently checks every candidate.

## Baseline review and first migration

The approved `.release-baseline.json` is local runtime state. It contains only
invoice numbers, amounts, methods, and transaction types for the historical
dates listed in `release_check.py`; customer names are omitted. Mutable current
queues and lifetime balances are not compared as historical cash figures.

1. Prepare and review the code and its tests. Confirm accounting corrections
   against the active spec and independent payment evidence.
2. From the original server runtime directory, use the reviewed candidate's
   Python environment and script to capture the baseline:

   ```powershell
   & "C:\path\to\reviewed-candidate\venv\Scripts\python.exe" `
       "C:\path\to\reviewed-candidate\release_check.py" `
       --baseline "C:\path\to\server\.release-baseline.json" --write-baseline
   ```

   Both test suites must pass before capture. Review the resulting values;
   baseline capture is not independent proof that an accounting result is right.
   It never authorizes a protected-rule change.
3. Install/restart the reviewed watchdog only after dependencies, regressions,
   and baseline review have succeeded. A previously running watchdog does not
   acquire the new checks merely because a newer script exists on disk. Plan
   this first controller migration as a maintenance operation; do not let the
   old updater deploy the migration before preparation is complete. Update only
   the reviewed watchdog script in the original directory while a legacy app
   still relies on that directory; preserve its application code and environment
   for recovery. Do not reset that checkout to a different app revision.
4. Check `/api/health`, the release manifest, and the watchdog log. A successful
   isolated release records its actual launched commit and previous release.

A missing baseline blocks new releases. An already running legacy server is
kept online when its process identity can be verified; it is labelled
`legacy-unverified`, never attributed to the checkout's current Git HEAD. A
fresh installation with no baseline and no previous server waits for approval.

## Routine updates and intentional differences

The watchdog fetches the remote branch and prepares an isolated source copy and
virtual environment under `.releases/`. Preparation runs separately while the
foreground watchdog monitors and restarts the current release. The candidate
must pass offline tests, all live payment regressions, and the approved
accounting comparison before the current app is stopped.

If a comparison differs, `.release-baseline.json.candidate.json` and
`.release-baseline.json.diff.txt` describe the candidate. Read the preparation
log under `.releases/` for the candidate path. Investigate each difference. An
intentional correction needs its regression and spec updated; an unexpected
difference needs a code/data explanation. Do not copy a candidate over the
baseline merely to unblock deployment.

After review, explicitly run the candidate's `release_check.py --write-baseline`
as above, then request another check:

```powershell
.\update_now_and_restart.ps1
```

Runtime JSON stays in the original server directory. Each release keeps its own
code and dependencies. A failed startup or wrong `/api/health` revision restores
the previous launch descriptor. Failed validation never automatically approves
its candidate or updates the accounting baseline.

## Version verification and rollback

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Get-Content .server-release.json -Raw
Get-Content server_auto_update.log -Tail 50
```

The health `revision` must equal the manifest revision. It is set when the app
starts and is not inferred from mutable checkout files.

Request the previous verified release:

```powershell
.\run_server_auto_update.ps1 -Rollback
```

The running watchdog consumes the request. It verifies the restored app's
identity and prevents the rejected release from immediately replacing it.
An explicit update request or a newer commit allows another attempt. Rollback
does not revert local spending, settings, or hidden-invoice data. Do not delete
the active or previous release directory or edit the manifest by hand.

## Updating the watchdog itself

Application releases do not replace the running PowerShell controller. Once
both the active and previous manifest descriptors point to isolated `.releases/`
directories, the original execution-only checkout can be synchronized to the
accepted revision. If the previous release is still `legacy-unverified` and
points to the original directory, keep that application's code/environment
untouched; wait for another verified isolated release or explicitly preserve
the legacy rollback copy first. Restart the scheduled watchdog during maintenance so it loads
the reviewed controller code and restores the recorded release. Do not reset the
original checkout while the legacy app is still serving from it. Task Scheduler
may restart its child process during controller maintenance; perform the Windows
availability and reboot checks after a controller change.

## Limits

CI is offline; only the server-side gate validates live PrintSmith semantics.
Historical data/configuration edits can legitimately change a baseline and need
review. Fixed regression dates should be extended as new failure shapes are
found. Mocked PowerShell tests do not replace Windows Scheduled Task, reboot,
process ownership, and real failure-recovery verification.
