from __future__ import annotations

from gamelib import db
from gamelib.collectors.base import CollectorError
from gamelib.models import Game
from gamelib.sync import run_sync, run_sync_iter


class _FakeOk:
    platform = "steam"

    def is_configured(self, settings) -> bool:
        return True

    def fetch(self, settings) -> list[Game]:
        return [Game(platform="steam", external_id="1", name="Portal")]


class _FakeBroken:
    platform = "psn"

    def is_configured(self, settings) -> bool:
        return True

    def fetch(self, settings) -> list[Game]:
        raise CollectorError("psn: token expirado")


class _FakeUnconfigured:
    platform = "xbox"

    def is_configured(self, settings) -> bool:
        return False

    def fetch(self, settings) -> list[Game]:
        raise AssertionError("não deveria ser chamado se não configurado")


USER_ID = "user-a"


def test_run_sync_isola_falha_de_uma_plataforma_das_demais(settings, db_conn):
    report = run_sync(
        USER_ID,
        settings=settings,
        collectors={"steam": _FakeOk(), "psn": _FakeBroken(), "xbox": _FakeUnconfigured()},
        client=db_conn,
    )

    by_platform = {r.platform: r for r in report.results}
    assert by_platform["steam"].status == "success"
    assert by_platform["steam"].games_found == 1
    assert by_platform["psn"].status == "failed"
    assert "token expirado" in by_platform["psn"].error
    assert by_platform["xbox"].status == "skipped"
    assert report.ok is False

    assert [r["name"] for r in db.list_games(db_conn, USER_ID)] == ["Portal"]

    sync_runs = db_conn.table("sync_runs").select("*").execute().data
    assert {(r["platform"], r["status"]) for r in sync_runs} == {
        ("steam", "success"),
        ("psn", "failed"),
    }


def test_run_sync_com_todas_plataformas_ok_reporta_sucesso(settings, db_conn):
    report = run_sync(USER_ID, settings=settings, collectors={"steam": _FakeOk()}, client=db_conn)

    assert report.ok is True
    assert report.results[0].status == "success"


class _FakeStatusVariants:
    platform = "steam"

    def is_configured(self, settings) -> bool:
        return True

    def fetch(self, settings) -> list[Game]:
        return [
            Game(
                platform="steam",
                external_id="completo",
                name="A",
                playtime_minutes=500,
                achievements_unlocked=10,
                achievements_total=10,
            ),
            Game(platform="steam", external_id="jogando", name="B", playtime_minutes=120),
            Game(platform="steam", external_id="nao_iniciado", name="C", playtime_minutes=0),
            Game(platform="steam", external_id="sem_dado", name="D", playtime_minutes=None),
        ]


def test_run_sync_infere_completion_status_a_partir_de_playtime_e_achievements(settings, db_conn):
    run_sync(
        USER_ID, settings=settings, collectors={"steam": _FakeStatusVariants()}, client=db_conn
    )

    by_id = {r["external_id"]: r["completion_status"] for r in db.list_games(db_conn, USER_ID)}
    assert by_id == {
        "completo": "completed",
        "jogando": "playing",
        "nao_iniciado": "not_started",
        "sem_dado": "unknown",
    }


def test_run_sync_iter_emite_targets_primeiro_depois_um_platform_done_por_plataforma(
    settings, db_conn
):
    events = list(
        run_sync_iter(
            USER_ID,
            settings=settings,
            collectors={"steam": _FakeOk(), "psn": _FakeBroken(), "xbox": _FakeUnconfigured()},
            client=db_conn,
        )
    )

    assert events[0].type == "targets"
    assert events[0].targets == ["steam", "psn", "xbox"]

    done_events = events[1:]
    assert [e.type for e in done_events] == ["platform_done"] * 3
    assert [e.platform for e in done_events] == ["steam", "psn", "xbox"]
    assert [e.index for e in done_events] == [1, 2, 3]
    assert [e.total for e in done_events] == [3, 3, 3]
    assert [e.result.status for e in done_events] == ["success", "failed", "skipped"]
