"""Importador manual da Nintendo (sem API disponível — ver `.claude/rules/`).

Formato esperado (cabeçalho obrigatório), exemplo em
`templates/nintendo_import_example.csv`:

    name,playtime_minutes,completion_status,added_at,cover_url

Só `name` é obrigatório; os demais podem ficar em branco.

Capa, em ordem de prioridade:
1. `cover_url` preenchida na linha do CSV — usa direto, sem busca nenhuma.
   Jeito de fechar os casos que a busca automática não resolve: abra a
   página do jogo em nintendo.com/us/store e cole a URL.
2. Busca pública da eShop americana (mesma usada pelo site oficial
   nintendo.com — chave de busca somente-leitura embutida no client deles,
   não precisa de credencial própria). Index legado, sem cobertura de
   lançamentos recentes/Switch 2.
3. RAWG (`RAWG_API_KEY`, opcional — ver `docs/CREDENTIALS.md`), só se
   configurada e a eShop não achou nada — cobre jogos recentes que a eShop
   não tem.

Em ambas as buscas automáticas (2 e 3), sem API de mapeamento nome→jogo
confiável, então só aceitamos o resultado com correspondência de nome com
confiança alta; senão fica sem capa (nunca mostra a capa de outro jogo por
engano — ver `.claude/rules/python-data-rules.md`).
"""

from __future__ import annotations

import csv
import difflib
import logging
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import httpx

from gamelib.collectors.base import CollectorError
from gamelib.config import Settings
from gamelib.models import COMPLETION_STATUSES, Game

log = logging.getLogger("gamelib.collectors.nintendo_csv")

REQUIRED_COLUMNS = {"name"}

ESHOP_SEARCH_URL = "https://U3B6GR4UA3-dsn.algolia.net/1/indexes/ncom_game_en_us/query"
ESHOP_SEARCH_HEADERS = {
    "Content-Type": "application/json",
    "X-Algolia-API-Key": "6efbfb0f8f80defc44895018caf77504",
    "X-Algolia-Application-Id": "U3B6GR4UA3",
}
RAWG_SEARCH_URL = "https://api.rawg.io/api/games"
COVER_MATCH_THRESHOLD = 0.85

# Ruído comum de plataforma/edição que aparece só de um lado (CSV do usuário
# vs. título oficial da loja) e não deveria pesar na comparação — removido
# simetricamente dos dois antes de comparar.
_NOISE_PATTERNS = (
    r"nintendo switch\s*2?\s*edition",
    r"for nintendo switch",
    r"\bthe game\b",
)


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def _normalize_title(name: str) -> str:
    name = re.sub(r"[™®]", "", name).lower()
    for pattern in _NOISE_PATTERNS:
        name = re.sub(pattern, "", name)
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


def _clean_query(name: str) -> str:
    # O ruído de plataforma/edição também atrapalha a busca em si (o Algolia
    # rankeia pior com "for Nintendo Switch" etc. no meio) — limpa antes de
    # buscar, não só na hora de comparar o resultado.
    name = re.sub(r"[™®]", "", name)
    for pattern in _NOISE_PATTERNS:
        name = re.sub(pattern, "", name, flags=re.I)
    return re.sub(r"\s+", " ", name).strip(" -")


def _best_match(target: str, candidates: list[tuple[str, str | None]]) -> str | None:
    best_url: str | None = None
    best_ratio = 0.0
    for title, url in candidates:
        if not url:
            continue
        ratio = difflib.SequenceMatcher(None, target, _normalize_title(title)).ratio()
        if ratio > best_ratio:
            best_ratio, best_url = ratio, url
    return best_url if best_ratio >= COVER_MATCH_THRESHOLD else None


def _fetch_cover_url_eshop(client: httpx.Client, name: str) -> str | None:
    query = _clean_query(name)
    body = {"params": urlencode({"hitsPerPage": 5, "page": 0, "query": query})}
    try:
        resp = client.post(ESHOP_SEARCH_URL, headers=ESHOP_SEARCH_HEADERS, json=body)
    except httpx.HTTPError as exc:
        log.debug("nintendo_csv: falha ao buscar capa (eShop) de %r: %s", name, exc)
        return None
    if resp.status_code != 200:
        log.debug("nintendo_csv: busca (eShop) de %r retornou HTTP %d", name, resp.status_code)
        return None

    hits = resp.json().get("hits", [])
    candidates = [(h.get("title") or "", h.get("horizontalHeaderImage")) for h in hits]
    return _best_match(_normalize_title(name), candidates)


def _fetch_cover_url_rawg(client: httpx.Client, name: str, api_key: str) -> str | None:
    query = _clean_query(name)
    try:
        resp = client.get(RAWG_SEARCH_URL, params={"key": api_key, "search": query, "page_size": 5})
    except httpx.HTTPError as exc:
        log.debug("nintendo_csv: falha ao buscar capa (RAWG) de %r: %s", name, exc)
        return None
    if resp.status_code != 200:
        log.debug("nintendo_csv: busca (RAWG) de %r retornou HTTP %d", name, resp.status_code)
        return None

    results = resp.json().get("results", [])
    candidates = [(r.get("name") or "", r.get("background_image")) for r in results]
    return _best_match(_normalize_title(name), candidates)


def _fetch_cover_url(client: httpx.Client, name: str, rawg_api_key: str | None) -> str | None:
    cover_url = _fetch_cover_url_eshop(client, name)
    if cover_url or not rawg_api_key:
        return cover_url
    return _fetch_cover_url_rawg(client, name, rawg_api_key)


def _parse_int(value: str, *, field: str, line: int) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise CollectorError(f"nintendo_csv linha {line}: '{field}' inválido: {value!r}") from exc


def _parse_date(value: str, *, line: int) -> date | None:
    value = value.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CollectorError(
            f"nintendo_csv linha {line}: 'added_at' deve ser AAAA-MM-DD, recebi {value!r}"
        ) from exc


def import_csv(path: Path, settings: Settings | None = None) -> list[Game]:
    rawg_api_key = settings.rawg_api_key if settings else None

    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise CollectorError(
                f"nintendo_csv: cabeçalho inválido, esperado ao menos {REQUIRED_COLUMNS}"
            )

        games: list[Game] = []
        with httpx.Client(timeout=10) as client:
            for line, row in enumerate(reader, start=2):
                name = (row.get("name") or "").strip()
                if not name:
                    raise CollectorError(f"nintendo_csv linha {line}: 'name' vazio")

                status = (row.get("completion_status") or "unknown").strip() or "unknown"
                if status not in COMPLETION_STATUSES:
                    raise CollectorError(
                        f"nintendo_csv linha {line}: 'completion_status' inválido: {status!r}"
                    )

                manual_cover_url = (row.get("cover_url") or "").strip()

                games.append(
                    Game(
                        platform="nintendo",
                        external_id=_slugify(name),
                        name=name,
                        cover_url=manual_cover_url or _fetch_cover_url(client, name, rawg_api_key),
                        playtime_minutes=_parse_int(
                            row.get("playtime_minutes") or "", field="playtime_minutes", line=line
                        ),
                        completion_status=status,  # type: ignore[arg-type]
                        added_at=_parse_date(row.get("added_at") or "", line=line),
                        raw=dict(row),
                    )
                )
        return games
