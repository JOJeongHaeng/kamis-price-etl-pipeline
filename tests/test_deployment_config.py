from pathlib import Path
import unittest

from tools.validate_deployment_config import load_yaml, validate_ci, validate_render


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigTests(unittest.TestCase):
    def test_ci_workflow_matches_required_execution_contract(self):
        workflow = load_yaml(PROJECT_ROOT / ".github" / "workflows" / "test.yml")

        violations = validate_ci(workflow)

        self.assertEqual(violations, [])

    def test_render_blueprint_matches_runtime_contract(self):
        blueprint = load_yaml(PROJECT_ROOT / "render.yaml")
        python_version = (PROJECT_ROOT / ".python-version").read_text(
            encoding="utf-8"
        ).strip()

        violations = validate_render(blueprint, python_version)

        self.assertEqual(violations, [])

    def test_render_syncs_kamis_to_shared_sqlite_before_startup(self):
        blueprint = load_yaml(PROJECT_ROOT / "render.yaml")
        service = blueprint["services"][0]
        environment = {
            variable["key"]: variable
            for variable in service.get("envVars", [])
        }

        self.assertEqual(
            service["startCommand"],
            "python main.py && uvicorn web.app:app --host 0.0.0.0 --port $PORT",
        )
        self.assertEqual(environment["DB_DRIVER"]["value"], "sqlite")
        self.assertIs(environment["KAMIS_SERVICE_KEY"]["sync"], False)
        self.assertNotIn("value", environment["KAMIS_SERVICE_KEY"])


if __name__ == "__main__":
    unittest.main()
