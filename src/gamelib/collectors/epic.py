"""Epic Games via `legendary` (CLI open source, engenharia reversa do protocolo
da Epic). O projeto não expõe biblioteca própria pra chamar; delegamos ao
binário já autenticado pelo usuário (`legendary auth`, feito manualmente e
uma única vez fora deste projeto — fluxo interativo, não automatizável aqui).

Sem playtime/conquistas: a Epic não expõe isso nem pro próprio launcher
oficial via API pública, e o `legendary list` também não traz esses dados.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess

from gamelib.collectors.base import CollectorError
from gamelib.config import Settings
from gamelib.models import Game

log = logging.getLogger("gamelib.collectors.epic")


class EpicCollector:
    platform = "epic"

    def is_configured(self, settings: Settings) -> bool:
        return shutil.which(settings.legendary_bin) is not None

    def fetch(self, settings: Settings) -> list[Game]:
        try:
            result = subprocess.run(
                [settings.legendary_bin, "list", "--json"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CollectorError(
                f"epic: falha ao executar '{settings.legendary_bin}': {exc}"
            ) from exc

        if result.returncode != 0:
            raise CollectorError(
                f"epic: 'legendary list --json' saiu com código {result.returncode}: "
                f"{result.stderr.strip()[:300]}"
            )

        try:
            entries = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise CollectorError(f"epic: saída de 'legendary list --json' inválida: {exc}") from exc

        return [
            self._to_game(entry)
            for entry in entries
            if entry.get("app_name") and self._is_game(entry)
        ]

    def _is_game(self, entry: dict) -> bool:
        # Ativos de Unreal Marketplace (plugins/projects) e servidores dedicados vêm
        # junto na entitlement list, mas não têm a categoria "games" da Epic.
        categories = {c.get("path") for c in (entry.get("metadata") or {}).get("categories", [])}
        return "games" in categories

    def _to_game(self, entry: dict) -> Game:
        return Game(
            platform="epic",
            external_id=entry["app_name"],
            name=entry.get("app_title") or entry["app_name"],
            cover_url=self._cover_url(entry),
            raw=entry,
        )

    def _cover_url(self, entry: dict) -> str | None:
        images = ((entry.get("metadata") or {}).get("keyImages")) or []
        by_type = {img.get("type"): img.get("url") for img in images if img.get("url")}
        return (
            by_type.get("DieselGameBoxTall")
            or by_type.get("DieselGameBox")
            or next(iter(by_type.values()), None)
        )
