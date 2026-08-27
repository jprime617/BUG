from __future__ import annotations

import pytest
from tests.fakes import FakeSupabaseClient

from gamelib.config import Settings


@pytest.fixture
def db_conn():
    return FakeSupabaseClient()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        steam_api_key=None,
        steam_id64=None,
        psn_npsso=None,
        xbox_openxbl_key=None,
        legendary_bin="legendary",
    )
