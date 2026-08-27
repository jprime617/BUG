"""Núcleo de agente com ferramentas registráveis, circuit breaker e logs por etapa.

Referência viva de `.claude/rules/python-data-rules.md`:
- Habilidades desacopladas em tools registráveis.
- Pipeline com try/except por etapa (circuit breaker) que loga EXATAMENTE onde falhou.
- Telemetria estruturada (nível, timestamp, etapa) em vez de `print()` solto.

Sem dependência externa: roda com `python tasks.py run-pipeline` (ou `make run-pipeline`).
O ponto de vetorização com Pandas está marcado abaixo.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("agent")

Tool = Callable[[Any], Any]


class PipelineError(RuntimeError):
    """Falha de etapa já contextualizada (qual step, qual tool)."""


@dataclass
class Step:
    """Uma etapa do pipeline: aplica a tool `tool` à saída da etapa anterior."""

    tool: str
    label: str = ""

    def __post_init__(self) -> None:
        self.label = self.label or self.tool


@dataclass
class AdvancedAgentCore:
    name: str
    max_retries: int = 3
    tools: dict[str, Tool] = field(default_factory=dict)

    def register_tool(self, name: str, func: Tool) -> "AdvancedAgentCore":
        """Acopla uma habilidade. Retorna self para encadear registros."""
        if name in self.tools:
            raise ValueError(f"Tool '{name}' já registrada em [{self.name}].")
        self.tools[name] = func
        log.info("[%s] tool '%s' acoplada.", self.name, name)
        return self

    def _run_step(self, step: Step, payload: Any) -> Any:
        """Executa uma etapa com retry + circuit breaker. Loga onde falha."""
        tool = self.tools.get(step.tool)
        if tool is None:
            raise PipelineError(f"tool '{step.tool}' não registrada (etapa '{step.label}').")

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = tool(payload)
                log.info("[%s] etapa '%s' OK (tentativa %d).", self.name, step.label, attempt)
                return result
            except Exception as exc:  # noqa: BLE001 - fronteira do circuit breaker
                last_exc = exc
                log.warning(
                    "[%s] etapa '%s' falhou (tentativa %d/%d): %s",
                    self.name, step.label, attempt, self.max_retries, exc,
                )
        # Circuit breaker: para o fluxo apontando exatamente a etapa que quebrou.
        raise PipelineError(
            f"etapa '{step.label}' (tool '{step.tool}') falhou após {self.max_retries} tentativas"
        ) from last_exc

    def execute_pipeline(self, steps: list[Step], initial_input: Any) -> dict[str, Any]:
        log.info("[%s] iniciando pipeline com %d etapa(s).", self.name, len(steps))
        payload = initial_input
        for i, step in enumerate(steps, start=1):
            log.info("[%s] > etapa %d/%d: %s", self.name, i, len(steps), step.label)
            try:
                payload = self._run_step(step, payload)
            except PipelineError as exc:
                log.error("[%s] pipeline abortado na etapa %d/%d: %s", self.name, i, len(steps), exc)
                return {"status": "FAILED", "failed_step": i, "error": str(exc)}
        log.info("[%s] pipeline concluído.", self.name)
        return {"status": "SUCCESS", "data": payload}


# --- Exemplo executável ------------------------------------------------------
def _load(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not raw:
        raise ValueError("entrada vazia")
    return raw


def _transform(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Vetorização: com Pandas seria `df["total"] = df["qtd"] * df["preco"]`.
    # Aqui, sem dependência, mantém-se a mesma ideia de operação em lote.
    return [{**r, "total": r["qtd"] * r["preco"]} for r in rows]


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"linhas": len(rows), "faturamento": sum(r["total"] for r in rows)}


if __name__ == "__main__":
    agent = (
        AdvancedAgentCore(name="DataPipelineAgent")
        .register_tool("load", _load)
        .register_tool("transform", _transform)
        .register_tool("summarize", _summarize)
    )
    pipeline = [Step("load"), Step("transform"), Step("summarize", label="agregar_faturamento")]
    sample = [{"qtd": 3, "preco": 10.0}, {"qtd": 1, "preco": 25.0}]
    print(json.dumps(agent.execute_pipeline(pipeline, sample), indent=2, ensure_ascii=False))
