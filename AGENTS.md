2025-10-26T06:30:26+00:00 — bf1ab3f73ccd5ace1efed4509bdfeedcfac81bf8

# 🎯 Brief (objectif alpha — révision finale)

* **Périmètre** : crypto-only. API FastAPI sécurisée, **SSE** stable (headers + heartbeat), **MCP serveur réel** (stdio), indicateurs (MA/EMA/RSI/MACD/BB), **levels** S/R, **patterns** (double top/bottom, triangle, canal), résumé IA **informatif** (jamais prescriptif).
* **Constats précis sur cette archive** :

  * **MCP** : **pas d’entrypoint serveur** (fichier `mcp_main.py` manquant) ; `mcp_server.py` encore partiellement “stub”.
  * **SSE** : route `stream` quasi OK, **headers SSE présents** ✅ ; pipeline metrics déjà émis ✅ ; heartbeat présent ✅.
  * **Schemas** : `schemas/*` contiennent encore des parties incomplètes (notamment **streaming**, **market**, **indicators**, **levels**, **patterns**, **finance**, **backtest**, **common**).
  * **Routes** : `levels.py` et `patterns.py` **incomplètes** (préfixe/tags/déps/params à finir).
  * **Config** : `config.py` tronqué (validators Pydantic v2 à finaliser), mais `settings = get_settings()` est déjà exposé.
  * **Provider CCXT** : `normalize_symbol` présent ✅ ; `get_ohlcv` (retries/tri/UTC secondes) correct ✅.
  * **Docker** : `docker/Dockerfile` **OK** (healthcheck script externe) ; **`docker/healthcheck.py`** à nettoyer (retirer l’ellipse et initialiser `connection`).
  * **CI** : workflow YAML coupé ; finir les jobs (lint/format/type/test/build + smoke MCP).
  * **Front** : plusieurs fichiers TS/TSX encore partiels (mais attention : les `...` de **spread** `...devices`, `...current` **ne sont pas** des TODO — ne pas toucher).
* **Cible** :

  1. **Ajouter** un **serveur MCP exécut-able** (`src/chart_mcp/mcp_main.py`) + dépendance.
  2. **Compléter** tous les **schemas Pydantic** (notamment `schemas/streaming.py`).
  3. **Finaliser** les **routes** `levels.py`, `patterns.py` (params, deps, retours).
  4. **Nettoyer** `docker/healthcheck.py`.
  5. **Terminer** la **CI** (jobs complets) + scripts `package.json` cassés.
  6. **Tests** verts (≥ **80%** cov), linters/typing OK, build Docker OK.

---

# ✅ To-do minutieuse — fichier par fichier (avec sous-étapes)

## 0) Remplacer la source de vérité

* [x] **`AGENTS.md`** — **ÉCRASER** le fichier et coller **uniquement** la présente checklist + brief + “tests & build”.

  * [x] En tête : **date** + **hash archive** `bf1ab3f…`.

---

## 1) MCP (exposition serveur réelle)

* [x] **`requirements.txt`** — **ajouter** la lib serveur MCP (ex. `fastmcp==<version>`).

* [x] **`src/chart_mcp/mcp_main.py`** — **NOUVEAU** (entrypoint stdio) :

  ```python
  from __future__ import annotations
  import asyncio
  # adapte à la lib retenue
  from fastmcp import MCPServer
  from chart_mcp import mcp_server as tools

  REGISTERED_TOOL_NAMES = (
      "get_crypto_data",
      "compute_indicator",
      "identify_support_resistance",
      "detect_chart_patterns",
      "generate_analysis_summary",
  )

  def register(server: MCPServer) -> None:
      server.tool("get_crypto_data")(tools.get_crypto_data)
      server.tool("compute_indicator")(tools.compute_indicator)
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

* [x] **`src/chart_mcp/mcp_server.py`** — **terminer les stubs** :

  * [x] Garantir que **tous** les outils **retournent du JSON pur** (listes/dicts), **jamais** de `DataFrame`.
  * [x] Implémenter :

    * [x] `get_crypto_data(symbol, timeframe, *, limit=500, start=None, end=None) -> List[Dict[str, int|float]]` → `_provider.get_ohlcv(...)` puis `frame.to_dict(orient="records")`.
    * [x] `compute_indicator(symbol, timeframe, indicator, params) -> List[Dict[str, int|float]]` → calcule via `_indicator_service`, `dropna()`, **aligne `ts`**, sérialise `{ts, ...}`.
    * [x] `identify_support_resistance(...) -> List[Dict[str, ...]]` → utilise `_levels_service.detect_levels(...)`, sérialise `price/strength/kind/ts_range`.
    * [x] `detect_chart_patterns(...) -> List[Dict[str, ...]]` → sérialise `name,score,start_ts,end_ts,points,confidence`.
    * [x] `generate_analysis_summary(...) -> Dict[str, ...]` → passer `levels/patterns/highlights` au `_analysis_service.summarize(...)`.

* [x] **`Makefile`** — **ajouter** :

  ```make
  mcp-run:
  python -m chart_mcp.mcp_main
  ```

* [x] **`.github/workflows/ci.yml`** — **ajouter un job `mcp-smoke`** :

  * [x] installe deps (dont MCP),
  * [x] `python - <<'PY'\nimport importlib; m=importlib.import_module("chart_mcp.mcp_main"); assert hasattr(m, "register")\nPY`.

---

## 2) API FastAPI & SSE

### `src/chart_mcp/app.py`

* [x] **Compléter** l’usine d’app :

  * [x] Monter **toutes** les routes : `health`, `market`, `finance` (flag), `indicators`, `levels`, `patterns`, `analysis`, `stream`.
  * [x] Middlewares : `CORSMiddleware` (depuis `settings.allowed_origins`), `GZipMiddleware`, logs (jamais logguer `Authorization`).
  * [x] Handlers d’erreurs : `ApiError`, `HTTPException`, `RequestValidationError`, catch-all.
  * [x] (Optionnel) `default_response_class=ORJSONResponse`.

### `src/chart_mcp/routes/levels.py`

* [x] **Compléter** le routeur :

  ```python
  router = APIRouter(
      prefix="/api/v1/levels",
      tags=["levels"],
      dependencies=[Depends(require_token), Depends(require_regular_user)],
  )
  ```
* [x] **Implémenter** la route (params & retour) :

  * [x] Params: `symbol: str`, `timeframe: str`, `limit: int = Query(500, ge=1, le=5000)`, `max_levels: int = Query(10, ge=1, le=100)`.
  * [x] Logique: `parse_timeframe`, `provider.get_ohlcv`, `service.detect_levels(..., max_levels=max_levels)`, map → `LevelsResponse`.
  * [x] **Retourner `symbol` normalisé** (via `normalize_symbol`).

### `src/chart_mcp/routes/patterns.py`

* [x] **Compléter** le routeur :

  ```python
  router = APIRouter(
      prefix="/api/v1/patterns",
      tags=["patterns"],
      dependencies=[Depends(require_token), Depends(require_regular_user)],
  )
  ```
* [x] **Implémenter** la route : params `symbol/timeframe/limit`, `parse_timeframe`, `provider.get_ohlcv`, `service.detect(frame)`, sérialise vers `PatternsResponse` (+ `normalize_symbol`).

### `src/chart_mcp/routes/stream.py`

* [x] ✅ **Headers SSE** déjà posés.
* [x] **Conserver/valider** : garde-fou `asyncio.CancelledError` → fermeture propre (`streamer.stop()`), limites (`limit <= 5000`, ≤ 10 indicateurs), transformation `indicators` → `indicator_specs`.

---

## 3) Schemas Pydantic (à compléter)

> **Important** : ne pas confondre `Field(..., ...)` (normal) et des placeholders. Ici il faut **terminer les modèles**, contraintes et unions discriminées.

* [x] **`src/chart_mcp/schemas/streaming.py`** — **écrire entièrement** l’union discriminée :

  * [x] `EventType = Literal["tool","token","result_partial","result_final","metric","error","done"]`.
  * [x] Modèles :

    * `ToolEventDetails(tool:str, name:str|None, latest:Dict[str,float]|None)`.
    * `TokenPayload(text:str, min_length=1)`.
    * `LevelPreview(kind:str, strength:float>=0)`.
    * `ResultPartialDetails(levels: List[LevelPreview]=[], progress: float|None)`.
    * `LevelDetail(LevelPreview + ts_range)` ; `PatternDetail(name,score,start_ts,end_ts,points: List[tuple[int,float]], confidence: float)` ;
    * `ResultFinalDetails(summary:str min_length=1, levels: List[LevelDetail], patterns: List[PatternDetail])`.
    * `MetricDetails(step:str min_length=1, ms:float>=0)`.
    * `ErrorDetails(code:str, message:str)` ; `DoneDetails(status: Literal["ok","error"], code: str|None = None)`.
  * [x] Enveloppes `ToolStreamPayload`, `TokenStreamPayload`, `ResultPartialStreamPayload`, `ResultFinalStreamPayload`, `MetricStreamPayload`, `ErrorStreamPayload`, `DoneStreamPayload` avec `type` discriminant.
  * [x] `StreamPayload = Union[...]` ; `StreamEvent` qui accepte n’importe lequel.
  * [x] **Valider** les tests (`tests/unit/schemas/test_streaming.py`) : token vide → `ValidationError`, `DonePayload` refuse status inconnu, etc.

* [x] **`src/chart_mcp/schemas/market.py`** — compléter :

  * [x] `OhlcvRow(ts:int, o:float, h:float, l:float, c:float, v:float)`.
  * [x] `MarketDataResponse(symbol:str uppercased, timeframe:str, source:str, rows: List[OhlcvRow], fetched_at: datetime)`.
  * [x] `@validator/field_validator("symbol")` pour uppercaser.
  * [x] `OhlcvQuery(symbol:str, timeframe:str, limit:int, range:DatetimeRange|None)`.

* [x] **`src/chart_mcp/schemas/indicators.py`** — compléter :

  * [x] `IndicatorRequest(indicator: Literal["ma","ema","rsi","macd","bbands"], params: Dict[str, int|float]|None)`.
  * [x] `IndicatorPoint(ts:int, **values)` (ex : `ema`, `rsi`, `macd`, `bb_upper/lower/middle`).
  * [x] `IndicatorResponse(points: List[IndicatorPoint])`.

* [x] **`src/chart_mcp/schemas/levels.py`** — compléter :

  * [x] `Level(price:float, strength:float, kind: Literal["support","resistance"], ts_range: LevelRange(start_ts:int, end_ts:int))`.
  * [x] `LevelsResponse(symbol,timeframe,levels: List[Level])`.

* [x] **`src/chart_mcp/schemas/patterns.py`** — compléter :

  * [x] `PatternPoint(ts:int, price:float)` ;
  * [x] `Pattern(name:str, score:float, start_ts:int, end_ts:int, points: List[PatternPoint], confidence: float)`.
  * [x] `PatternsResponse(symbol,timeframe,patterns: List[Pattern])`.

* [x] **`src/chart_mcp/schemas/finance.py`**, **`backtest.py`**, **`common.py`** — compléter champs (CAGR, Sharpe, profit_factor, trades, equity_curve…), `model_config={"populate_by_name":True}`.

---

## 4) Config / Utils / Docker

### `src/chart_mcp/config.py`

* [x] **Terminer** la classe `Settings` (Pydantic v2) :

  * [x] Attributs déjà présents (`api_token`, `exchange`, `allowed_origins`, `llm_provider`, `llm_model`, `stream_heartbeat_ms`, `log_level`, `rate_limit_per_minute` optionnel, `feature_finance`, `playwright_mode`).
  * [x] **`@field_validator("allowed_origins", mode="before")`** : split chaîne → liste.
  * [x] `model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "validate_by_name": True}`.
  * [x] **Garder** `get_settings()` + **alias** `settings = get_settings()`.

### `src/chart_mcp/utils/errors.py`

* [x] **Compléter** les classes : `ApiError`, `BadRequest`, `Unauthorized`, `Forbidden`, `TooManyRequests`, `UpstreamError`.
* [x] **Handlers** : `api_error_handler`, `http_exception_handler`, `request_validation_exception_handler`, `unexpected_exception_handler` (payload `{"error":{code,message}, "details":..., "trace_id":...}`).

### `src/chart_mcp/utils/sse.py`

* [x] **Vérifier** : `format_sse(event, payload)` (NDJSON), `heartbeat_sender`, `SSEStreamer` (`start/stop/publish/stream`).
* [x] **Rien à changer** si tests passent ; sinon, s’assurer que `: ping\n\n` est envoyé au rythme `STREAM_HEARTBEAT_MS`.

### `docker/healthcheck.py`

* [x] **Retirer** l’ellipse et **initialiser** `connection = None` avant le `try` :

  ```python
  def main() -> int:
      connection = None
      try:
          connection = http.client.HTTPConnection("localhost", 8000, timeout=3)
          connection.request("GET", "/health")
          return 0 if connection.getresponse().status == 200 else 1
      except Exception:
          return 1
      finally:
          with suppress(Exception):
              if connection is not None:
                  connection.close()
  ```

---

## 5) Provider / Services

### `src/chart_mcp/services/data_providers/ccxt_provider.py`

* [x] ✅ **Conserver** `KNOWN_QUOTES` et `normalize_symbol` (déjà ok).
* [x] ✅ **Conserver** `get_ohlcv` (retries 429, secondes, tri, `UpstreamError` si vide).
* [x] (Optionnel) exposer `source` (exchange id) côté routes.

### `src/chart_mcp/services/streaming.py`

* [x] ✅ **Garder** l’émission `metric` à chaque étape (`data/indicators/levels/patterns/summary`).
* [x] ✅ Sur exception : publier `error` puis `done`, puis `stop()`.
* [x] **S’assurer** que les `token` ne sont **jamais vides** (le schéma `TokenPayload(text,min_length=1)` le garantira).

### `src/chart_mcp/services/indicators.py`, `levels.py`, `patterns.py`, `analysis_llm.py`

* [x] **Vérifier** que les sorties collent aux **schemas finalisés** (noms de champs/types).
* [x] `analysis_llm` : texte ≤ **400** caractères ; **jamais** “acheter/vendre/buy/sell”.

---

## 6) Frontend (compléter les parties minimales — ne pas toucher aux spreads `...` valides)

> ⚠️ Les `...` dans `...devices["Desktop Chrome"]`, `[...current, nextMessage]`, spreads d’objets, etc., **sont normaux**. **NE PAS** les confondre avec des TODO.

* [x] **`components/messages.tsx`** — compléter rendus/fallback :

  * [x] Interface `ChatMessage` ({ role: "user"|"assistant", text: string, artifacts?: ChatArtifactBase[] }).
  * [x] Pour artefacts inconnus : afficher `data-testid="artifact-fallback"`.
  * [x] Conserver les imports des artefacts finance ; si payload manquant → fallback.

* [x] **`components/finance/backtest-report-artifact.tsx`** — compléter interfaces & rendu :

  * [x] `BacktestMetrics`, `EquityPoint`, `BacktestTrade`, `BacktestReportArtifactData`.
  * [x] Propriétés `BacktestReportArtifactProps { artifact: BacktestReportArtifactData }`.
  * [x] Rendu simple : titre, métriques formatées, mini-table trades (ou “aucun trade”).

* [x] **`components/finance/finance-chart-artifact.tsx`** — compléter :

  * [x] Types `OhlcvRow`, `OverlaySeriesModel`, `ChartArtifactResponse`.
  * [x] Rendu minimal (pas d’obligation de lib chart pour l’alpha : liste ou placeholder ok si tests n’exigent pas l’UI réelle).
  * [x] Exposer `data-testid` utilisés dans les tests.

* [x] **`tests/pages/chat.ts`**, **`tests/e2e/harness.tsx`**, **`tests/e2e/finance-fixtures.ts`** — **supprimer** les vrais TODO :

  * [x] Remplacer les `...` de **placeholders** (pas les spreads TS) par des implémentations minimales compatibles avec les specs existantes (sélecteurs, harness, stubs fetch si nécessaires), ou marquer `test.skip` si non critique en alpha.

* [x] **`playwright.config.ts`** — **ne rien changer** (le `...devices` est un spread **valide**).

* [x] **`package.json`** — corriger **scripts cassés** :

  ```json
  {
    "scripts": {
      "clean": "python -m chart_mcp.cli.cleanup",
      "build": "python -m compileall src",
      "test": "pytest -q",
      "lint": "ruff check . && black --check src tests && isort --check-only src tests && mypy src",
      "lint:fix": "ruff check --fix . && black src tests && isort src tests"
    }
  }
  ```

---

## 7) CI

* [x] **`.github/workflows/ci.yml`** — **terminer** les jobs :

  * **lint** : checkout, setup-python (3.11, 3.12), cache pip, `ruff`, `black --check`, `isort --check-only`.
  * **typecheck** : `mypy src`.
  * **test** : `pytest --cov=src --cov-report=xml`. Upload artifact `coverage.xml`.
  * **mcp-smoke** : voir § MCP.
  * **docker** : build image, `HEALTHCHECK` OK (utilise `docker/healthcheck.py`).

---

# 🧪 Tests & Build — exigences fermes

* **Couverture** : `pytest --cov=src --cov-report=xml` **≥ 80 %**.
* **Qualité** : `ruff` / `black` / `isort` **sans erreur** ; `mypy src` **0 erreur**.
* **Sécu** : toutes les routes (sauf `/health`) exigent `Authorization: Bearer <token>`.
* **SSE** : headers (`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`) ; heartbeat `: ping`; événements `metric` présents.
* **Neutralité** : aucun terme prescriptif (“acheter/vendre/buy/sell”).
* **Docker** : image slim, user non-root, `HEALTHCHECK` via `docker/healthcheck.py`.
* **Node** : `pnpm@8`, Node ≥ 20 pour les tests front.

---

## 📎 Extraits prêts-à-coller (patchs clés)

**Headers SSE (déjà ok — pour mémoire)**

```python
headers = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
return StreamingResponse(iterator, media_type="text/event-stream", headers=headers)
```

**Normalisation symbole (déjà ok — pour mémoire)**

```python
KNOWN_QUOTES = ("USDT","USD","USDC","BTC","ETH","EUR","GBP")
def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if "/" in s: return s
    for q in KNOWN_QUOTES:
        if s.endswith(q) and len(s) > len(q):
            return f"{s[:-len(q)]}/{q}"
    raise BadRequest("Unsupported symbol format")
```

**Healthcheck Docker (nettoyage)**

```python
def main() -> int:
    connection = None
    try:
        connection = http.client.HTTPConnection("localhost", 8000, timeout=3)
        connection.request("GET", "/health")
        return 0 if connection.getresponse().status == 200 else 1
    except Exception:
        return 1
    finally:
        with suppress(Exception):
            if connection is not None:
                connection.close()
```

**Entrée MCP exécutable**

```python
# src/chart_mcp/mcp_main.py
from fastmcp import MCPServer
from chart_mcp import mcp_server as tools
# ... REGISTERED_TOOL_NAMES, register(), main() comme indiqué plus haut
```

---

## ✅ Plan d’exécution immédiat (ordre recommandé)

1. **Ajouter** `mcp_main.py` + dépendance MCP ; corriger `package.json` (scripts).
2. **Compléter** `schemas/streaming.py` puis **routes `levels`/`patterns`** (aligner avec schemas).
3. **Nettoyer** `docker/healthcheck.py`.
4. **Terminer** `mcp_server.py` (retours JSON) et **CI** (`ci.yml` complet + job mcp-smoke).
5. **Compléter** le **front minimal** (artefacts/fallbacks) pour éteindre les tests front sensibles.
6. **Exécuter** : `ruff check .` → `black --check`/`isort` → `mypy src` → `pytest -q` → build Docker.
7. Itérer jusqu’à **tout vert** (cov ≥ 80 %).

---

si tu suis cette liste **point par point** (et seulement celle-ci), on verrouille l’alpha : **MCP serveur réel**, **SSE robuste**, **schemas figés**, **CI verte** et **intégration front minimale** prête à brancher sur le SDK Vercel.

---

## Historique

- 2025-10-26T06:30:26+00:00 — gpt-5-codex : MCP stdio opérationnel (adaptateur FastMCP) et outils JSON finalisés.
- 2025-10-26T06:30:26+00:00 — gpt-5-codex : Schémas & routes (market/indicators/streaming) harmonisés, config et healthcheck complétés.
- 2025-10-26T06:30:26+00:00 — gpt-5-codex : CI mise à jour (lint/type/test/docker/mcp-smoke) et QA locale (`ruff`, `black --check`, `isort --check-only`, `mypy`, `pytest --cov`).
- 2025-10-26T06:39:56+00:00 — gpt-5-codex : Durci `utils.errors` (imports/JSON handlers) + ajouté tests unitaires dédiés, ajusté isort (`known_third_party`) et confirmé front/harness conformes ; QA locale `ruff`/`black --check`/`isort --check-only`/`mypy`/`pytest --cov`.
- 2025-10-26T06:47:13+00:00 — gpt-5-codex : Exposé la source CCXT dans les réponses levels/patterns (`source`), aligné le paramètre `max` et étendu les tests d'intégration ; QA complète `ruff`/`black --check`/`isort --check-only`/`mypy`/`pytest --cov`.
- 2025-10-26T07:02:00+00:00 — gpt-5-codex : Harmonisé les invocations Ruff (`ruff check`) dans le workflow CI, le Makefile et `package.json` pour éviter l'échec "unrecognized subcommand".
