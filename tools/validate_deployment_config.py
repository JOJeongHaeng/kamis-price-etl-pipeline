from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping while preserving GitHub Actions' `on` key."""
    with path.open(encoding="utf-8") as source:
        document = yaml.safe_load(source)
    if not isinstance(document, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    if True in document and "on" not in document:
        document["on"] = document.pop(True)
    return document


def validate_ci(config: dict[str, Any]) -> list[str]:
    """Return semantic violations of the SmartShopping CI contract."""
    violations: list[str] = []
    triggers = config.get("on", {})
    jobs = config.get("jobs", {})
    test_job = jobs.get("test", {}) if isinstance(jobs, dict) else {}
    steps = test_job.get("steps", []) if isinstance(test_job, dict) else []

    _expect(violations, _branches(triggers, "push") == ["main"], "push must target main")
    _expect(
        violations,
        _branches(triggers, "pull_request") == ["main"],
        "pull requests must target main",
    )
    _expect(
        violations,
        isinstance(triggers, dict) and "workflow_dispatch" in triggers,
        "workflow_dispatch must be enabled",
    )
    _expect(violations, test_job.get("runs-on") == "ubuntu-latest", "test job must use Ubuntu")
    _expect(violations, len(jobs) == 1, "workflow must define one job")

    uses = [step.get("uses", "") for step in steps if isinstance(step, dict)]
    _expect(violations, any(value.startswith("actions/checkout@") for value in uses), "checkout step is required")
    setup_steps = [
        step
        for step in steps
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/setup-python@")
    ]
    setup_options = setup_steps[0].get("with", {}) if setup_steps else {}
    _expect(
        violations,
        setup_options.get("python-version-file") == ".python-version",
        "setup-python must read .python-version",
    )
    _expect(violations, setup_options.get("cache") == "pip", "setup-python must cache pip")
    _expect(
        violations,
        setup_options.get("cache-dependency-path") == "requirements.txt",
        "pip cache must use requirements.txt",
    )

    commands = [step.get("run") for step in steps if isinstance(step, dict)]
    required_commands = (
        "python -m pip install -r requirements.txt",
        "PYTHONWARNINGS=error python -m unittest discover -s tests",
        "python -m compileall -q config.py etl tools web tests",
        "python tools/seed_demo_db.py",
    )
    for command in required_commands:
        _expect(violations, command in commands, f"missing CI command: {command}")
    if all(command in commands for command in required_commands):
        positions = [commands.index(command) for command in required_commands]
        _expect(violations, positions == sorted(positions), "CI commands must run in the required order")
    return violations


def _branches(triggers: object, event: str) -> object:
    if not isinstance(triggers, dict):
        return None
    settings = triggers.get(event, {})
    return settings.get("branches") if isinstance(settings, dict) else None


def _expect(violations: list[str], condition: bool, message: str) -> None:
    if not condition:
        violations.append(message)
