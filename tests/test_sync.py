from __future__ import annotations

from gamelib import db
from gamelib.collectors.base import CollectorError
from gamelib.models import Game
from gamelib.sync import run_sync


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


def test_run_sync_isola_falha_de_uma_plataforma_das_demais(settings):
    report = run_sync(
        settings=settings,
        collectors={"steam": _FakeOk(), "psn": _FakeBroken(), "xbox": _FakeUnconfigured()},
    )

    by_platform = {r.platform: r for r in report.results}
    assert by_platform["steam"].status == "success"
    assert by_platform["steam"].games_found == 1
    assert by_platform["psn"].status == "failed"
    assert "token expirado" in by_platform["psn"].error
    assert by_platform["xbox"].status == "skipped"
    assert report.ok is False

    conn = db.connect(settings.database_path)
    assert [r["name"] for r in db.list_games(conn)] == ["Portal"]

    sync_runs = conn.execute("SELECT platform, status FROM sync_runs").fetchall()
    assert {(r["platform"], r["status"]) for r in sync_runs} == {
        ("steam", "success"),
        ("psn", "failed"),
    }


def test_run_sync_com_todas_plataformas_ok_reporta_sucesso(settings):
    report = run_sync(settings=settings, collectors={"steam": _FakeOk()})

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


class _FakeNintendo:
    platform = "nintendo"

    def is_configured(self, settings) -> bool:
        return True

    def fetch(self, settings) -> list[Game]:
        return [
            Game(
                platform="nintendo",
                external_id="zelda",
                name="Zelda",
                playtime_minutes=4200,
                completion_status="abandoned",
            )
        ]


def test_run_sync_infere_completion_status_a_partir_de_playtime_e_achievements(settings):
    run_sync(settings=settings, collectors={"steam": _FakeStatusVariants()})

    conn = db.connect(settings.database_path)
    by_id = {r["external_id"]: r["completion_status"] for r in db.list_games(conn)}
    assert by_id == {
        "completo": "completed",
        "jogando": "playing",
        "nao_iniciado": "not_started",
        "sem_dado": "unknown",
    }


def test_run_sync_nao_sobrescreve_completion_status_manual_do_nintendo(settings):
    run_sync(settings=settings, collectors={"nintendo": _FakeNintendo()})

    conn = db.connect(settings.database_path)
    row = db.list_games(conn)[0]
    assert row["completion_status"] == "abandoned"
