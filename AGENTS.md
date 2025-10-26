2025-10-26T09:45:27+00:00 — df8507e36ed459d108d91aa93a4656d3f5fa8f49

# 🎯 Brief (objectif alpha — état actuel vs cible)

* **Périmètre alpha** (crypto-only) couvert : API FastAPI sécurisée (guards OK), indicateurs, levels, patterns, route d’**analyse** end-to-end, **SSE** avec pipeline/metrics/tokens, services (provider CCXT, indicators, levels, patterns, LLM stub).
* **Reste à faire/corriger (bloquants)** :

  1. **Serveur MCP exécutable absent** (`mcp_main.py`) alors que le README revendique MCP.
  2. **Dépendance MCP** absente (`requirements.txt`).
  3. **SSE headers** non posés sur `/stream/analysis` (pas bloquant pour les tests, mais requis côté prod/Nginx).
  4. **Docker HEALTHCHECK** invalide (`python -m http.client GET …`).
  5. **Script `clean` de `package.json` corrompu** (ellipse dans `sys.path.insert`).
  6. (Amélioration robuste prod) **Normalisation symbole** côté provider avant `fetch_ohlcv` (`BTCUSDT` → `BTC/USDT`) pour éviter les erreurs d’exchange.
  7. (Qualité) Ajouter **smoke tests MCP** et un test d’entête SSE.

**Important** : les `...` que tu vois dans le code **Pydantic/TS** (ex. `Field(...)`, `Query(...)`, spreads `...devices["Desktop Chrome"]`, `super(...args)`) **ne sont pas** des TODO — **ne pas** les modifier.

---

# ✅ To-do à cocher — **fichier par fichier** (avec sous-étapes)

## 0) Remplacer la source de vérité

* [x] **`AGENTS.md`** — **ÉCRASER** avec ce document (ajoute en tête la **date** et le **SHA-1** ci-dessus).

---

## 1) MCP (outillage + binaire serveur)

* [x] **`requirements.txt`** — ajouter et épingler la lib serveur MCP (ex. `fastmcp==0.0.9` ; adapte si autre SDK retenu).

* [x] **`src/chart_mcp/mcp_main.py`** — **NOUVEAU** : entrypoint MCP (stdio) + enregistrement des tools :

  ```python
  from __future__ import annotations
  import asyncio
  from typing import Iterable, Dict, Any
  from fastmcp import MCPServer  # adapte si SDK différent
  from chart_mcp import mcp_server as tools
  import pandas as pd

  REGISTERED_TOOL_NAMES = (
      "get_crypto_data",
      "compute_indicator",
      "identify_support_resistance",
      "detect_chart_patterns",
      "generate_analysis_summary",
  )

  def _df_records(df: pd.DataFrame) -> list[dict[str, Any]]:
      return df.reset_index(drop=True).to_dict(orient="records")

  def register(server: MCPServer) -> None:
      server.tool("get_crypto_data")(lambda symbol, timeframe, limit=500, start=None, end=None: _df_records(
          tools.get_crypto_data(symbol, timeframe, limit=limit, start=start, end=end)
      ))
      server.tool("compute_indicator")(lambda symbol, timeframe, indicator, params=None: _df_records(
          tools.compute_indicator(symbol, timeframe, indicator, params or {})
      ))
      server.tool("identify_support_resistance")(tools.identify_support_resistance)
      server.tool("detect_chart_patterns")(tools.detect_chart_patterns)
      server.tool("generate_analysis_summary")(tools.generate_analysis_summary)

  async def main() -> None:
      server = MCPServer()
      register(server)
      await server.serve_stdio()

  if __name__ == "__main__":
      asyncio.run(main())
  ```

  *Raison* : conserver les fonctions internes en DataFrame (tests actuels), mais **sérialiser en JSON** au moment d’exposer MCP.

* [x] **CI** (`.github/workflows/ci.yml`) — ajouter un **job léger `mcp-smoke`** (Py 3.11) :

  * [x] `pip install -r requirements.txt`
  * [x] `python - <<'PY'\nimport importlib; m=importlib.import_module("chart_mcp.mcp_main"); assert hasattr(m, "register")\nPY`

* [x] **`README.md`** — compléter la section **MCP** :

  * [x] Installation (dépendance), commande de lancement `python -m chart_mcp.mcp_main`.
  * [x] Liste des tools enregistrés (noms ci-dessus) et exemples d’appels/contrats (JSON).

---

## 2) API & streaming

### `src/chart_mcp/routes/stream.py`

* [x] **Ajouter les headers SSE** à la réponse (compat. Nginx/proxy) :

  ```python
  headers = {
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
  }
  return StreamingResponse(iterator, media_type="text/event-stream", headers=headers)
  ```
* [x] Conserver validations existantes (borne `limit` ≤ 5000, ≤ 10 indicateurs).
* [x] (Facultatif) Documenter dans `README.md` la **grille d’événements** : `tool_start|tool_end|metric|token|result_partial|result_final|error|done` + heartbeat `: ping`.

---

## 3) Provider marché (robustesse prod)

### `src/chart_mcp/services/data_providers/ccxt_provider.py`

* [x] **Normaliser le symbole** avant `fetch_ohlcv` (ne change pas le `symbol` retourné par l’API) :

  ```python
  KNOWN_QUOTES = ("USDT","USD","USDC","BTC","ETH","EUR","GBP")
  def _normalize_symbol(symbol: str) -> str:
      s = symbol.strip().upper()
      if "/" in s: return s
      for q in KNOWN_QUOTES:
          if s.endswith(q) and len(s) > len(q):
              return f"{s[:-len(q)]}/{q}"
      # fallback : renvoyer s (pour tests) ou lever BadRequest en prod stricte
      return s
  # dans get_ohlcv(...):
  market = _normalize_symbol(symbol)
  raw = self.client.fetch_ohlcv(market, ccxt_timeframe(timeframe), since=None, limit=limit or None)
  ```
* [x] **Ne touche pas** aux DataFrames (colonnes `["ts","o","h","l","c","v"]`, ts en **secondes**, tri croissant) — les tests les valident déjà.

---

## 4) Docker & scripts

### `docker/Dockerfile`

* [x] **Corriger le HEALTHCHECK** (la commande actuelle est invalide) :

  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
    python - <<'PY' || exit 1
  import sys, http.client
  try:
      c = http.client.HTTPConnection("localhost", 8000, timeout=3)
      c.request("GET", "/health")
      r = c.getresponse()
      sys.exit(0 if r.status == 200 else 1)
  except Exception:
      sys.exit(1)
  PY
  ```

### `package.json`

* [x] **Réparer** le script `clean` (supprimer l’ellipse tronquée) :

  ```json
  {
    "scripts": {
      "clean": "python -m chart_mcp.cli.cleanup",
      "build": "python -m compileall src",
      "test": "pytest -q"
    }
  }
  ```

### `Makefile`

* [x] **Ajouter** utilitaires DX :

  ```make
  format-check:
  black --check src tests
  isort --check-only src tests

  lint-fix:
  ruff --fix .
  black src tests
  isort src tests

  typecheck-strict:
  mypy src

  mcp-run:
  python -m chart_mcp.mcp_main
  ```

---

## 5) Tests à ajouter (courts mais essentiels)

* [x] **MCP runtime** — `tests/unit/mcp/test_server_runtime.py` :

  ```python
  import importlib
  def test_tools_registered():
      m = importlib.import_module("chart_mcp.mcp_main")
      names = []
      class Dummy:
          def tool(self, name):
              def deco(fn): names.append(name); return fn
              return deco
      s = Dummy(); m.register(s)
      for n in m.REGISTERED_TOOL_NAMES:
          assert n in names
  ```
* [x] **SSE headers (integration)** — `tests/integration/test_stream_headers.py` :

  ```python
  def test_stream_headers(client):
      with client.stream("GET", "/stream/analysis", params={"symbol":"BTCUSDT","timeframe":"1h","limit":200}) as r:
          assert r.status_code == 200
          assert r.headers["content-type"].startswith("text/event-stream")
          assert r.headers.get("cache-control") == "no-cache"
          assert r.headers.get("connection") == "keep-alive"
          assert r.headers.get("x-accel-buffering") == "no"
  ```

*(Les tests existants couvrent déjà provider, streaming, levels/patterns, guards, finance, etc.)*

---

## 6) Docs

### `README.md`

* [x] **Aligner** avec l’implémentation réelle :

  * [x] **MCP** : comment lancer (`python -m chart_mcp.mcp_main`) + liste des tools + exemple JSON.
  * [x] **SSE** : expliquer les **headers** requis et les **événements** (incl. `metric` et heartbeat).
  * [x] **Normalisation interne** du symbole par le provider (l’API accepte `BTCUSDT` **ou** `BTC/USDT`).

### `CONTRIBUTING.md`

* [x] Référencer `.env.example` et les scripts Make (`format-check`, `typecheck-strict`, `mcp-run`).

---

# 🧪 Exigences tests & build (à respecter strictement)

* **Qualité** : `ruff`, `black`, `isort` **propres** ; `mypy src` **0 erreur**.
* **Couverture** : `pytest --cov=src --cov-report=xml` **≥ 80 %**.
* **Sécurité** : toutes les routes hors `/health` exigent `Authorization: Bearer`, plus `X-User-Type: regular`.
* **SSE** : `text/event-stream` + headers ci-dessus ; heartbeat `: ping`; événements `metric` présents.
* **Neutralité** (texte) : aucun vocabulaire prescriptif (“acheter/vendre/buy/sell”).
* **Docker** : image slim, user non-root, **HEALTHCHECK** corrigé.
* **Node/Playwright** : Node ≥ 20, `pnpm@8`, e2e stables (harness conservé, spreads `...` **à laisser**).

---

## 📎 Patches prêts à coller

**SSE headers (`src/chart_mcp/routes/stream.py`)**

```python
return StreamingResponse(iterator, media_type="text/event-stream", headers={
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
})
```

**HEALTHCHECK Docker (`docker/Dockerfile`)**

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  python - <<'PY' || exit 1
import sys, http.client
try:
    c = http.client.HTTPConnection("localhost", 8000, timeout=3)
    c.request("GET", "/health")
    r = c.getresponse()
    sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
```

**`package.json` (script `clean`)**

```json
"clean": "python -m chart_mcp.cli.cleanup"
```

**Entrée MCP (`src/chart_mcp/mcp_main.py`)** — cf. bloc au §1.

---

### ✅ Checklist finale (ordre d’exécution recommandé)

1. Ajouter **`mcp_main.py`** + **dépendance MCP** ; ajouter **job `mcp-smoke`**.
2. Poser **headers SSE** sur `/stream/analysis`.
3. Corriger **HEALTHCHECK** Docker.
4. Réparer **script `clean`** dans `package.json`.
5. (Prod) Normaliser le **symbole** dans le provider avant `fetch_ohlcv`.
6. Ajouter **tests** MCP + headers SSE.
7. Mettre à jour la **doc** (`README.md`, `CONTRIBUTING.md`).
8. Lancer **CI locale** : `make format-check && make typecheck-strict && pytest -q` puis build Docker.

— Si tu coches tout ci-dessus, l’alpha est **cohérente et exécutable** : API + SSE **robustes**, **serveur MCP** opérationnel (stdio), docs à jour, CI **verte**.

---
## Historique

- 2025-10-26T09:50:55+00:00 — gpt-5-codex : Aligné `mcp_main.py` (sérialisation JSON + wrapper FastMCP), renforcé les tests MCP, corrigé le HEALTHCHECK Docker et documenté les raccourcis Make dans `CONTRIBUTING.md`. QA locale : `ruff`, `black --check`, `isort --check-only`, `mypy src`, `pytest --cov`.
- 2025-10-26T10:07:45+00:00 — gpt-5-codex : Rétabli la compatibilité MCP via une sous-classe `FastMCP`, sécurisé `_df_records` (DataFrame & séquences), restauré la validation `limit <= 5000` côté SSE, assoupli `normalize_symbol` (fallback), ajusté les tests correspondants et relancé `ruff`, `black --check`, `isort --check-only`, `mypy src`, `pytest --cov`.
