"""Scaffold smoke tests: the app imports cleanly and exposes /health.

These run hermetically (no database) — importing ``main`` builds the app and
registers routes without triggering the startup DB check, which only fires when
the ASGI app is served.
"""

from main import app, health_check


def test_health_check_returns_ok():
    assert health_check() == {"status": "ok"}


def test_health_route_registered():
    paths = {route.path for route in app.routes}
    assert "/health" in paths
