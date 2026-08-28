(() => {
  // Delegado em document.body (não no botão direto) pra sobreviver ao swap
  // final de #stats via htmx.ajax — mesmo padrão de game-modal.js.
  document.body.addEventListener("click", (event) => {
    const btn = event.target.closest("#sync-btn");
    if (!btn || btn.disabled) return;
    startSync(btn);
  });

  function startSync(btn) {
    const stats = document.getElementById("stats");
    const rally = stats.querySelector("#sync-rally");
    const status = stats.querySelector("#sync-rally-status");
    const label = btn.querySelector(".sync-btn__label");
    if (!rally || !label) return;

    const stamps = Array.from(rally.querySelectorAll(".sync-rally__stamp"));
    const segments = Array.from(rally.querySelectorAll(".sync-rally__segment"));
    const count = rally.querySelector(".sync-rally__count");

    stamps.forEach((stamp) => {
      stamp.dataset.status = "pending";
      stamp.removeAttribute("title");
      stamp.querySelector(".sync-rally__sublabel").textContent = "";
    });
    segments.forEach((seg) => seg.classList.remove("is-filled"));
    if (count) count.textContent = "";

    btn.disabled = true;
    btn.classList.add("is-syncing");
    rally.hidden = false;

    const source = new EventSource("/sync/stream");

    source.addEventListener("targets", (event) => {
      const data = JSON.parse(event.data);
      if (data.targets.length > 0) {
        setStampStatus(stamps, data.targets[0], "syncing");
        label.textContent = `Sincronizando ${platformLabel(stamps, data.targets[0])}…`;
      }
      announce(status, `Sincronização iniciada: ${data.targets.length} plataforma(s).`);
    });

    source.addEventListener("platform_done", (event) => {
      const data = JSON.parse(event.data);
      applyResult(stamps, data);
      if (data.index <= segments.length) {
        segments[data.index - 1].classList.add("is-filled");
      }
      if (count) {
        const pct = Math.round((data.index / data.total) * 100);
        count.textContent = `${data.index}/${data.total} · ${pct}%`;
      }

      const nextPlatform = data.index < data.total ? stamps[data.index]?.dataset.platform : null;
      if (nextPlatform) {
        setStampStatus(stamps, nextPlatform, "syncing");
        label.textContent = `Sincronizando ${platformLabel(stamps, nextPlatform)}…`;
      }
      announce(status, describeResult(stamps, data));
    });

    source.addEventListener("complete", () => {
      source.close();
      finishSync(btn, label);
    });

    source.onerror = () => {
      source.close();
      finishSync(btn, label);
    };
  }

  function finishSync(btn, label) {
    label.textContent = "Sincronizado";
    window.setTimeout(() => {
      htmx.ajax("GET", "/partials/stats", { target: "#stats", swap: "outerHTML" }).then(() => {
        document.body.dispatchEvent(new CustomEvent("sync-done"));
      });
    }, 450);
  }

  function setStampStatus(stamps, platform, statusValue) {
    const stamp = stamps.find((s) => s.dataset.platform === platform);
    if (stamp) stamp.dataset.status = statusValue;
  }

  function applyResult(stamps, data) {
    const stamp = stamps.find((s) => s.dataset.platform === data.platform);
    if (!stamp) return;
    stamp.dataset.status = data.status;
    const sublabel = stamp.querySelector(".sync-rally__sublabel");
    if (data.status === "success") {
      const n = data.games_found ?? 0;
      sublabel.textContent = n === 1 ? "1 jogo" : `${n} jogos`;
    } else if (data.status === "skipped") {
      sublabel.textContent = "sem chave";
    } else {
      sublabel.textContent = "falhou";
      if (data.error) stamp.title = data.error;
    }
  }

  function describeResult(stamps, data) {
    const name = platformLabel(stamps, data.platform);
    if (data.status === "success") {
      const n = data.games_found ?? 0;
      return `${name}: ${n} jogo(s) sincronizado(s).`;
    }
    if (data.status === "skipped") return `${name}: sem credenciais configuradas.`;
    return `${name}: falhou — ${data.error || "erro desconhecido"}.`;
  }

  function platformLabel(stamps, platform) {
    const stamp = stamps.find((s) => s.dataset.platform === platform);
    return stamp ? stamp.dataset.label : platform;
  }

  function announce(el, text) {
    if (el) el.textContent = text;
  }
})();
