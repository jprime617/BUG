from __future__ import annotations

from pathlib import Path

import pytest

from gamelib.config import Settings
from gamelib.db import connect


@pytest.fixture
def db_conn(tmp_path: Path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        steam_api_key=None,
        steam_id64=None,
        psn_npsso=None,
        xbox_openxbl_key=None,
        legendary_bin="legendary",
        database_path=tmp_path / "test.db",
    )
