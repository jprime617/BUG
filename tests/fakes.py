"""Fake em memória do subconjunto do client supabase-py que `gamelib.db` e
`gamelib.settings_store` realmente usam. Fica no nível do query builder
(select/eq/ilike/order/maybe_single/execute, insert, upsert com
on_conflict) — não tenta replicar a semântica HTTP/PostgREST real, só o
suficiente pra exercitar a lógica real desses módulos sem rede.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class _FakeResult:
    def __init__(self, data: Any) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []
        self._order: tuple[str, bool] | None = None
        self._mode = "many"

    def select(self, *_args: Any, **_kwargs: Any) -> _FakeQuery:
        return self

    def eq(self, col: str, val: Any) -> _FakeQuery:
        self._filters.append((col, "eq", val))
        return self

    def ilike(self, col: str, pattern: str) -> _FakeQuery:
        self._filters.append((col, "ilike", pattern))
        return self

    def order(self, col: str, desc: bool = False) -> _FakeQuery:
        self._order = (col, desc)
        return self

    def maybe_single(self) -> _FakeQuery:
        self._mode = "maybe_single"
        return self

    def single(self) -> _FakeQuery:
        self._mode = "single"
        return self

    def _matches(self, row: dict) -> bool:
        for col, op, val in self._filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "ilike":
                needle = str(val).strip("%").lower()
                if needle not in str(row.get(col, "")).lower():
                    return False
        return True

    def execute(self) -> _FakeResult:
        rows = [r for r in self._rows if self._matches(r)]
        if self._order:
            col, desc = self._order
            rows = sorted(rows, key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if self._mode == "maybe_single":
            return _FakeResult(rows[0] if rows else None)
        if self._mode == "single":
            if not rows:
                raise RuntimeError("no rows found for .single()")
            return _FakeResult(rows[0])
        return _FakeResult(rows)


class _FakeMutation:
    def __init__(
        self,
        client: FakeSupabaseClient,
        table: str,
        payload: dict,
        *,
        on_conflict: str = "",
    ) -> None:
        self._client = client
        self._table = table
        self._payload = payload
        self._conflict_cols = [c.strip() for c in on_conflict.split(",") if c.strip()]

    def execute(self) -> _FakeResult:
        storage = self._client._data[self._table]
        if self._conflict_cols:
            existing = next(
                (
                    r
                    for r in storage
                    if all(r.get(c) == self._payload.get(c) for c in self._conflict_cols)
                ),
                None,
            )
            if existing is not None:
                existing.update(self._payload)
                return _FakeResult([existing])
        row = self._client._apply_defaults(self._table, self._payload)
        storage.append(row)
        return _FakeResult([row])


class _FakeTableBuilder:
    def __init__(self, client: FakeSupabaseClient, name: str) -> None:
        self._client = client
        self._name = name

    def select(self, *_args: Any, **_kwargs: Any) -> _FakeQuery:
        return _FakeQuery(self._client._data[self._name])

    def insert(self, payload: dict) -> _FakeMutation:
        return _FakeMutation(self._client, self._name, payload)

    def upsert(self, payload: dict, on_conflict: str = "") -> _FakeMutation:
        return _FakeMutation(self._client, self._name, payload, on_conflict=on_conflict)


class FakeSupabaseClient:
    """Substitui `supabase.Client` nos testes — ver `gamelib.db.connect`."""

    def __init__(self) -> None:
        self._data: dict[str, list[dict]] = {
            "games": [],
            "game_metadata": [],
            "sync_runs": [],
            "settings": [],
        }
        self._next_id = {"games": 1, "sync_runs": 1}

    def table(self, name: str) -> _FakeTableBuilder:
        return _FakeTableBuilder(self, name)

    def _apply_defaults(self, table: str, payload: dict) -> dict:
        now = datetime.now(UTC).isoformat()
        row = dict(payload)
        if table in self._next_id and "id" not in row:
            row["id"] = self._next_id[table]
            self._next_id[table] += 1
        if table == "games":
            row.setdefault("first_synced_at", now)
            row.setdefault("last_synced_at", now)
            row.setdefault("name_sort", (row.get("name") or "").lower())
        if table == "game_metadata":
            row.setdefault("fetched_at", now)
        if table == "settings":
            row.setdefault("updated_at", now)
        return row
