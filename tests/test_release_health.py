import os
import unittest
from unittest.mock import patch

from app.main import app


class ReleaseHealthTests(unittest.TestCase):
    def test_health_reports_launch_identity_instead_of_mutable_git_head(self):
        endpoint = next(route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/health")
        with patch.dict(os.environ, {"PRINTSMITH_RELEASE_REVISION": "verified-revision"}):
            self.assertEqual(endpoint(), {"status": "ok", "revision": "verified-revision"})
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(endpoint()["revision"], "development")
