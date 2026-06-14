"""Phase 4 test: init_db must re-raise DB init failures (fail fast)."""
import pytest
import src.db.session as session_mod
from sqlalchemy.exc import OperationalError


def test_init_db_reraises_operational_error(monkeypatch):
    def boom(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    # Force table creation to fail like an unreachable/uninitialized DB.
    monkeypatch.setattr(session_mod.Base.metadata, "create_all", boom)
    with pytest.raises(OperationalError):
        session_mod.init_db()
