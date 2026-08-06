"""Behavioral coverage for startup-only lazy imports."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    ("module_name", "deferred_name", "trigger"),
    [
        (
            "agent.model_metadata",
            "requests",
            "getattr(module, 'requests')",
        ),
        (
            "cron.jobs",
            "croniter",
            "assert module._ensure_croniter()",
        ),
        (
            "tools.browser_supervisor",
            "websockets",
            "import asyncio; supervisor = module.CDPSupervisor('test', 'ws://example.invalid'); "
            "supervisor._stop_requested = True; asyncio.run(supervisor._run())",
        ),
        (
            "tools.vision_tools",
            "agent.auxiliary_client",
            "module._load_auxiliary_client()",
        ),
    ],
)
def test_heavy_dependency_is_loaded_only_on_use(module_name, deferred_name, trigger):
    script = f"""
import importlib
import sys

module = importlib.import_module({module_name!r})
assert {deferred_name!r} not in sys.modules
{trigger}
assert {deferred_name!r} in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
