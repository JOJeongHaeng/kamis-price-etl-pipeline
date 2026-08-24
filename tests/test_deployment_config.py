from pathlib import Path
import unittest

from tools.validate_deployment_config import load_yaml, validate_ci


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigTests(unittest.TestCase):
    def test_ci_workflow_matches_required_execution_contract(self):
        workflow = load_yaml(PROJECT_ROOT / ".github" / "workflows" / "test.yml")

        violations = validate_ci(workflow)

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
