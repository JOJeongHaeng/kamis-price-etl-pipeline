from pathlib import Path
import unittest

from tools.smoke_test_deployment import smoke_test_deployment


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DeploymentSmokeTests(unittest.TestCase):
    def test_seeded_uvicorn_process_serves_public_routes(self):
        responses = smoke_test_deployment(PROJECT_ROOT)

        self.assertEqual(
            responses["/health"],
            {"status": "ok", "database": "ready"},
        )
        self.assertEqual(responses["/api/prices"]["total"], 6)
        self.assertEqual(responses["/"]["status"], 200)
        self.assertEqual(responses["/docs"]["status"], 200)


if __name__ == "__main__":
    unittest.main()
