"""Phase 4 test: async init_db must re-raise DB init failures (fail fast)."""
import pytest
import src.db.session as session_mod
from sqlalchemy.exc import OperationalError


@pytest.mark.asyncio
async def test_init_db_reraises_operational_error(monkeypatch):
    class BoomEngine:
        def begin(self):
            raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(session_mod, "engine", BoomEngine())
    with pytest.raises(OperationalError):
        await session_mod.init_db()
