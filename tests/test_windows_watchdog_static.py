import unittest
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell.exe") or shutil.which("powershell")


class TestWindowsWatchdogStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = (ROOT / "run_server_auto_update.ps1").read_text()
        cls.manual_update = (ROOT / "update_now_and_restart.ps1").read_text()
        cls.batch_launcher = (ROOT / "setup_and_run.bat").read_text()

    def test_task_starts_automatically_and_restarts_without_time_limit(self):
        self.assertIn("New-ScheduledTaskTrigger -AtStartup", self.runner)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", self.runner)
        self.assertIn("-RestartCount 999", self.runner)
        self.assertIn("-RestartInterval (New-TimeSpan -Minutes 2)", self.runner)
        self.assertIn("-ExecutionTimeLimit ([TimeSpan]::Zero)", self.runner)
        self.assertIn("-MultipleInstances IgnoreNew", self.runner)

    def test_server_health_is_checked_independently_of_release_preparation(self):
        self.assertIn("[int]$HealthCheckIntervalSeconds = 10", self.runner)
        self.assertIn("Start-Sleep -Seconds $HealthCheckIntervalSeconds", self.runner)
        tick = self.runner.split("function Invoke-WatchdogTick", 1)[1].split(
            "function Restore-ServingRelease", 1
        )[0]
        self.assertLess(tick.index("Test-ServerRunning"), tick.index("Complete-ReleasePreparation"))
        preparation = self.runner.split("function Start-ReleasePreparation", 1)[1].split(
            "function Stop-ReleasePreparation", 1
        )[0]
        self.assertIn("Start-Process", preparation)
        self.assertIn("-PrepareReleaseMode", preparation)
        self.assertNotIn("-Wait", preparation)

    def test_candidate_is_isolated_and_checked_without_changing_running_checkout(self):
        prepare = self.runner.split("function Prepare-Release {", 1)[1].split(
            "function Start-ReleasePreparation", 1
        )[0]
        self.assertIn('"archive", "--format=zip"', prepare)
        self.assertIn('Join-Path $ReleasePath "venv', prepare)
        self.assertIn('Join-Path $ReleasePath "requirements.txt"', prepare)
        self.assertIn('Join-Path $ReleasePath "release_check.py"', prepare)
        self.assertNotIn("Stop-ReportServer", prepare)
        self.assertNotIn('"reset", "--hard"', self.runner)
        self.assertNotIn("--write-baseline", self.runner)
        self.assertLess(
            prepare.index('"release_check.py"'), prepare.index("return [pscustomobject]")
        )

    def test_new_release_reports_its_identity_and_rolls_back_when_unhealthy(self):
        switch = self.runner.split("function Invoke-ReleaseSwitch", 1)[1].split(
            "function Prepare-Release", 1
        )[0]
        self.assertLess(switch.index('"pending"'), switch.index("Stop-ReportServer"))
        self.assertIn("Wait-ReleaseHealth $Candidate", switch)
        self.assertIn("Start-ReportServer $OldRelease", switch)
        self.assertIn("Wait-ReleaseHealth $OldRelease", switch)
        self.assertIn("$script:BlockedRevision = $Candidate.revision", switch)
        self.assertIn("PRINTSMITH_RELEASE_REVISION", self.runner)
        self.assertIn('--app-dir "{0}"', self.runner)
        self.assertIn('$Health.revision -eq $Release.revision', self.runner)
        self.assertIn("Test-ProcessIdentity $ExistingProcess $Release", self.runner)

    def test_preparation_is_bounded_and_cancelled_on_watchdog_exit(self):
        self.assertIn("$script:PreparationStartedAt.AddMinutes(30)", self.runner)
        self.assertIn("taskkill.exe /PID $script:PreparationProcess.Id /T /F", self.runner)
        self.assertIn("finally {\n    Stop-ReleasePreparation", self.runner)

    @unittest.skipUnless(POWERSHELL, "PowerShell unavailable")
    def test_release_control_flow(self):
        subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tests/test_windows_release.ps1")],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_manual_entry_points_delegate_to_watchdog(self):
        self.assertIn(".server_update_requested", self.manual_update)
        self.assertNotIn("Stop-ScheduledTask", self.manual_update)
        self.assertIn("run_server_auto_update.ps1", self.batch_launcher)


if __name__ == "__main__":
    unittest.main()
