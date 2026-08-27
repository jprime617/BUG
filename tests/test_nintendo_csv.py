from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from gamelib.collectors.base import CollectorError
from gamelib.collectors.nintendo_csv import import_csv
from gamelib.config import Settings


def _write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "nintendo.csv"
    path.write_text(content, encoding="utf-8")
    return path


def _hit(title: str, image: str = "https://assets.nintendo.com/cover.png") -> dict:
    return {"title": title, "horizontalHeaderImage": image}


def _settings(rawg_api_key: str | None = None) -> Settings:
    return Settings(
        steam_api_key=None,
        steam_id64=None,
        psn_npsso=None,
        xbox_openxbl_key=None,
        legendary_bin="legendary",
        database_path="/tmp/unused.db",  # type: ignore[arg-type]
        rawg_api_key=rawg_api_key,
    )


def _patch_search(
    monkeypatch,
    eshop_hits_by_query: dict[str, list[dict]] | None = None,
    rawg_results_by_query: dict[str, list[dict]] | None = None,
    rawg_calls: list[str] | None = None,
) -> None:
    import json
    from urllib.parse import parse_qs

    eshop_hits_by_query = eshop_hits_by_query or {}
    rawg_results_by_query = rawg_results_by_query or {}
    real_client_cls = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if "algolia" in request.url.host:
            params = parse_qs(json.loads(request.content)["params"])
            query = params.get("query", [""])[0]
            return httpx.Response(200, json={"hits": eshop_hits_by_query.get(query, [])})

        assert "rawg.io" in request.url.host
        if rawg_calls is not None:
            rawg_calls.append(str(request.url))
        query = request.url.params.get("search", "")
        return httpx.Response(200, json={"results": rawg_results_by_query.get(query, [])})

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


def _patch_eshop_search(monkeypatch, hits_by_query: dict[str, list[dict]]) -> None:
    _patch_search(monkeypatch, eshop_hits_by_query=hits_by_query)


def test_import_csv_le_linhas_validas(monkeypatch, tmp_path: Path):
    _patch_eshop_search(
        monkeypatch,
        {
            "Zelda": [_hit("Zelda", "https://assets.nintendo.com/zelda.png")],
            "Metroid": [_hit("Metroid", "https://assets.nintendo.com/metroid.png")],
        },
    )
    path = _write_csv(
        tmp_path,
        "name,playtime_minutes,completion_status,added_at\n"
        "Zelda,4200,playing,2023-05-12\n"
        "Metroid,,not_started,\n",
    )

    games = import_csv(path)

    assert [g.name for g in games] == ["Zelda", "Metroid"]
    assert games[0].playtime_minutes == 4200
    assert games[0].added_at.isoformat() == "2023-05-12"
    assert games[0].cover_url == "https://assets.nintendo.com/zelda.png"
    assert games[1].playtime_minutes is None
    assert games[0].platform == "nintendo"
    assert games[0].external_id == "zelda"


def test_import_csv_falha_com_status_invalido_e_aponta_a_linha(monkeypatch, tmp_path: Path):
    _patch_eshop_search(monkeypatch, {})
    path = _write_csv(
        tmp_path,
        "name,playtime_minutes,completion_status,added_at\nMario,10,jogando_muito,\n",
    )

    with pytest.raises(CollectorError, match="linha 2"):
        import_csv(path)


def test_import_csv_fica_sem_capa_quando_correspondencia_e_fraca(monkeypatch, tmp_path: Path):
    _patch_eshop_search(
        monkeypatch,
        {"Persona 3 Reload": [_hit("Bayonetta 3", "https://assets.nintendo.com/bayo.png")]},
    )
    path = _write_csv(tmp_path, "name\nPersona 3 Reload\n")

    games = import_csv(path)

    assert games[0].cover_url is None


def test_import_csv_nao_confunde_jogos_da_mesma_franquia(monkeypatch, tmp_path: Path):
    # "Tears of the Kingdom" é bem parecido com "Breath of the Wild" em texto
    # cru, mas são jogos diferentes — o limiar tem que rejeitar isso.
    _patch_eshop_search(
        monkeypatch,
        {
            "The Legend of Zelda: Tears of the Kingdom": [
                _hit("The Legend of Zelda: Breath of the Wild")
            ]
        },
    )
    path = _write_csv(tmp_path, "name\nThe Legend of Zelda: Tears of the Kingdom\n")

    games = import_csv(path)

    assert games[0].cover_url is None


def test_import_csv_usa_cover_url_manual_sem_buscar(monkeypatch, tmp_path: Path):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"hits": []})

    real_client_cls = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *a, **k: real_client_cls(*a, transport=httpx.MockTransport(handler), **k),
    )
    path = _write_csv(
        tmp_path,
        "name,cover_url\n"
        "Persona 3 Reload,https://www.nintendo.com/us/store/products/persona-3-reload-switch-2/cover.png\n",
    )

    games = import_csv(path)

    assert (
        games[0].cover_url
        == "https://www.nintendo.com/us/store/products/persona-3-reload-switch-2/cover.png"
    )
    assert calls == []


def test_import_csv_cover_url_manual_vazia_cai_na_busca_automatica(monkeypatch, tmp_path: Path):
    _patch_eshop_search(
        monkeypatch, {"Zelda": [_hit("Zelda", "https://assets.nintendo.com/zelda.png")]}
    )
    path = _write_csv(tmp_path, "name,cover_url\nZelda,\n")

    games = import_csv(path)

    assert games[0].cover_url == "https://assets.nintendo.com/zelda.png"


def test_import_csv_usa_rawg_quando_eshop_nao_acha_e_rawg_configurada(monkeypatch, tmp_path: Path):
    rawg_calls: list[str] = []
    _patch_search(
        monkeypatch,
        eshop_hits_by_query={},
        rawg_results_by_query={
            "Persona 3 Reload": [
                {"name": "Persona 3 Reload", "background_image": "https://rawg.io/p3r.jpg"}
            ]
        },
        rawg_calls=rawg_calls,
    )
    path = _write_csv(tmp_path, "name\nPersona 3 Reload\n")

    games = import_csv(path, _settings(rawg_api_key="RAWG_KEY"))

    assert games[0].cover_url == "https://rawg.io/p3r.jpg"
    assert len(rawg_calls) == 1


def test_import_csv_nao_chama_rawg_quando_eshop_ja_achou(monkeypatch, tmp_path: Path):
    rawg_calls: list[str] = []
    _patch_search(
        monkeypatch,
        eshop_hits_by_query={"Zelda": [_hit("Zelda", "https://assets.nintendo.com/zelda.png")]},
        rawg_calls=rawg_calls,
    )
    path = _write_csv(tmp_path, "name\nZelda\n")

    games = import_csv(path, _settings(rawg_api_key="RAWG_KEY"))

    assert games[0].cover_url == "https://assets.nintendo.com/zelda.png"
    assert rawg_calls == []


def test_import_csv_sem_rawg_key_nao_tenta_rawg(monkeypatch, tmp_path: Path):
    rawg_calls: list[str] = []
    _patch_search(
        monkeypatch,
        eshop_hits_by_query={},
        rawg_results_by_query={
            "Persona 3 Reload": [
                {"name": "Persona 3 Reload", "background_image": "https://rawg.io/p3r.jpg"}
            ]
        },
        rawg_calls=rawg_calls,
    )
    path = _write_csv(tmp_path, "name\nPersona 3 Reload\n")

    games = import_csv(path)  # sem settings -> sem rawg_api_key

    assert games[0].cover_url is None
    assert rawg_calls == []


def test_import_csv_fica_sem_capa_quando_busca_falha(monkeypatch, tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    real_client_cls = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *a, **k: real_client_cls(*a, transport=httpx.MockTransport(handler), **k),
    )
    path = _write_csv(tmp_path, "name\nCastlevania\n")

    games = import_csv(path)

    assert games[0].cover_url is None
