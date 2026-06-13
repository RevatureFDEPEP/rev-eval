"""Service-root pytest hooks (W3-F5).

Only the integration gate lives here; the hermetic unit fixtures stay in
``tests/conftest.py``. ``pytest_addoption`` must be declared in a rootdir
conftest (this file), not a subdirectory one, so the ``--integration`` flag is
registered before collection.

Everything under ``tests/integration/`` is auto-marked ``integration`` by path
and *skipped* unless ``--integration`` is passed. So a plain ``pytest`` run
(the unit CI step and the Dockerfile ``test`` stage, where no databases exist)
leaves the integration suite visible-but-skipped instead of erroring on a
missing Postgres/Mongo.
"""

import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run tests/integration/ against real Postgres + Mongo + "
        "question-management-service (docker compose up -d --wait "
        "postgres mongo question-management-service)",
    )


def pytest_collection_modifyitems(config, items):
    run_integration = config.getoption("--integration")
    skip_integration = pytest.mark.skip(
        reason="needs real containers — pass --integration "
        "(see tests/integration/conftest.py for the compose command)"
    )
    for item in items:
        path = str(item.fspath).replace(os.sep, "/")
        if "tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
            if not run_integration:
                item.add_marker(skip_integration)
