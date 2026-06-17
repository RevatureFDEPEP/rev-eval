"""Service-root pytest hooks.

The ``--integration`` gate lives here (a rootdir conftest, required for
``pytest_addoption``); the hermetic unit fixtures stay in ``tests/conftest.py``.

Everything under ``tests/integration/`` is auto-marked ``integration`` by path
and *skipped* unless ``--integration`` is passed. So a plain ``pytest`` run (the
unit CI step and the Dockerfile ``test`` stage, where no real database exists)
leaves the cross-schema suite visible-but-skipped instead of erroring.
"""

import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run tests/integration/ against a real Postgres whose schema was "
        "migrated by test-management-service (docker compose up -d --wait "
        "postgres test-management-service)",
    )


def pytest_collection_modifyitems(config, items):
    run_integration = config.getoption("--integration")
    skip_integration = pytest.mark.skip(
        reason="needs a test-management-migrated Postgres — pass --integration "
        "(see tests/integration/conftest.py)"
    )
    for item in items:
        path = str(item.fspath).replace(os.sep, "/")
        if "tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
            if not run_integration:
                item.add_marker(skip_integration)
