from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


PUBLIC_PATHS = ("/health", "/", "/api/prices", "/docs")


def smoke_test_deployment(project_root: Path) -> dict[str, dict[str, Any]]:
    """Seed a temporary database and probe a real Uvicorn process."""
    with tempfile.TemporaryDirectory(prefix="smartshopping-smoke-") as temp_dir:
        environment = {
            **os.environ,
            "SQLITE_PATH": str(Path(temp_dir) / "smartshopping.db"),
        }
        subprocess.run(
            [sys.executable, "tools/seed_demo_db.py"],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        port = _available_port()
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "web.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=project_root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            base_url = f"http://127.0.0.1:{port}"
            _wait_until_ready(process, base_url)
            responses: dict[str, dict[str, Any]] = {}
            for path in PUBLIC_PATHS:
                with urlopen(f"{base_url}{path}", timeout=2) as response:
                    body = response.read()
                    if path in ("/health", "/api/prices"):
                        responses[path] = json.loads(body)
                    else:
                        responses[path] = {"status": response.status}
            return responses
        finally:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)


def _available_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def _wait_until_ready(
    process: subprocess.Popen[str],
    base_url: str,
    timeout: float = 10,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Uvicorn exited with {process.returncode}: {stdout}{stderr}"
            )
        try:
            with urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except URLError:
            time.sleep(0.1)
    raise TimeoutError(f"Uvicorn did not become ready at {base_url}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(smoke_test_deployment(root), ensure_ascii=False))
