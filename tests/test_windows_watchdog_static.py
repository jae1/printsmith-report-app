import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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

    def test_server_health_is_checked_independently_of_update_interval(self):
        self.assertIn("[int]$HealthCheckIntervalSeconds = 10", self.runner)
        self.assertIn("if (-not (Test-ServerRunning))", self.runner)
        self.assertIn("Start-Sleep -Seconds $HealthCheckIntervalSeconds", self.runner)

    def test_update_preparation_happens_before_server_stop(self):
        update_section = self.runner.split(
            "function Update-RepositoryIfAvailable", maxsplit=1
        )[1]
        self.assertLess(
            update_section.index("Install-Dependencies"),
            update_section.index("Stop-ReportServer"),
        )
        self.assertIn("keeping the current server online", self.runner)

    def test_manual_entry_points_delegate_to_watchdog(self):
        self.assertIn(".server_update_requested", self.manual_update)
        self.assertNotIn("Stop-ScheduledTask", self.manual_update)
        self.assertIn("run_server_auto_update.ps1", self.batch_launcher)


if __name__ == "__main__":
    unittest.main()
