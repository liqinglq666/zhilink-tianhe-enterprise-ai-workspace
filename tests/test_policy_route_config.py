from __future__ import annotations

import os
import subprocess
import sys


def _import_policy_routes(generation: str, search: str) -> tuple[int, int]:
    env = os.environ.copy()
    env["MAX_CONCURRENT_GENERATIONS_PER_CLIENT"] = generation
    env["MAX_CONCURRENT_POLICY_SEARCHES_PER_CLIENT"] = search
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import backend.policy_official_routes as routes; "
                "print(routes.MAX_POLICY_CONCURRENCY, routes.MAX_POLICY_SEARCH_CONCURRENCY)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    generation_value, search_value = completed.stdout.strip().split()
    return int(generation_value), int(search_value)


def test_policy_route_concurrency_config_falls_back_on_malformed_values() -> None:
    assert _import_policy_routes("not-a-number", " ") == (1, 1)


def test_policy_route_concurrency_config_preserves_valid_positive_values() -> None:
    assert _import_policy_routes("3", "4") == (3, 4)
