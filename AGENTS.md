2025-10-25T11:33:39Z — d28da297d8228675a9a6467306c2a91a580e4bdc

# 🎯 Brief à l’agent (objectifs fin d’alpha)

* **Périmètre** : crypto-only, API HTTP sécurisée + **SSE** fiable, **tools MCP** réellement **exposés par un serveur MCP** exécutable, indicateurs (MA/EMA/RSI/MACD/BB), supports/résistances, patterns simples (double top/bottom, triangle, canal), **analyse IA pédagogique** (jamais prescriptive).
* **Constats sur la branche fournie** : plusieurs modules contiennent des **sections tronquées / `...`** (donc code non exécutable), **pas d’entrypoint MCP**, **headers SSE** non posés, **HEALTHCHECK Docker** invalide, **contrats Pydantic** incomplets.
* **Cible** :

  1. **Remplacer tous les `...`** par des implémentations **complètes et testées**.
  2. Ajouter un **serveur MCP exécutable** (entrypoint + dépendance).
  3. Ajouter **en-têtes SSE** + **événements `metric`** (durées par étape) dans le flux.
  4. **Normaliser les symboles** (`BTCUSDT` et `BTC/USDT`) côté provider CCXT.
  5. Corriger le **HEALTHCHECK Docker**.
  6. Compléter/ajouter les **tests** (MCP runtime, SSE headers/metrics, normalisation symboles) pour **≥ 80 %** de couverture.
* **Invariants** : 0 erreur lint/type, Docker slim non-root, **aucun conseil d’investissement**.

---

# ✅ Liste de tâches à cocher — fichier par fichier

## Racine / Documentation / DX

* [x] **`AGENTS.md`** — **Écraser** le fichier et coller **cette** checklist (source de vérité).

  * [x] Supprimer l’historique/anciennes consignes.
  * [x] Ajouter en tête **date** + **commit hash** courant.

* [x] **`README.md`** — **Mettre à jour** usage et exemples.

  * [x] Expliquer que l’API **accepte** `BTCUSDT` **et** `BTC/USDT` ; le provider **normalise** en `BASE/QUOTE`.
  * [x] Ajouter un exemple complet `POST /api/v1/indicators/compute` (body + réponse).
  * [x] Ajouter des exemples `GET /api/v1/levels` (`?max=`) et `GET /api/v1/patterns`.
  * [x] **SSE** : documenter **headers** côté serveur (`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`), le **format NDJSON** (`event:` + `data:`), et une trace d’événements attendus (`tool_start`, `result_partial`, `metric`, `token`, `result_final`, `done`).
  * [x] Ajouter une section **“Serveur MCP”** : comment l’installer (**dépendance MCP**), **le lancer** (`make mcp-run`), et **noms des tools** exposés.

* [x] **`CONTRIBUTING.md`** — Vérifier la section env et **référencer** `.env.example` (déjà présent).

* [x] **`Makefile`** — Vérifier que toutes les recettes ont des **TABs** (pas d’espaces).

  * [x] Ajouter :

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

## Dépendances / CI / Docker

* [x] **`requirements.txt`** — **Ajouter** la lib serveur MCP (par ex. `fastmcp` – version épinglée) pour pouvoir lancer un **vrai** serveur MCP.

* [x] **`.github/workflows/ci.yml`** — **Renforcer** la CI :

  * [x] Ajouter un step `format-check` (black/isort en mode check) en plus de `ruff`.
  * [x] Conserver `--cov=src --cov-report=xml` et publier `coverage.xml`.
  * [x] **Nouveau job** léger `mcp-smoke` (Py 3.11) : installe deps + MCP, **importe** `chart_mcp.mcp_main:register` et vérifie l’enregistrement des tools (sans lancer un vrai serveur réseau).
  * [x] S’assurer que l’intégration démarre/arrête proprement l’API FastAPI (pidfile) comme déjà esquissé.

* [x] **`docker/Dockerfile`** — **Corriger le HEALTHCHECK** (la commande actuelle `python -m http.client GET ...` est invalide) :

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

## Application FastAPI (sections tronquées à compléter)

* [x] **`src/chart_mcp/app.py`** — **Compléter** la factory (sections `...`) :

  * [x] Imports de routes (`analysis, finance, health, indicators, levels, market, stream`).
  * [x] Monter **toutes** les routes.
  * [x] Middlewares : `CORSMiddleware` (depuis `settings.allowed_origins`), `GZipMiddleware`, middleware logging (ne **jamais** logguer `Authorization`).
  * [x] Handlers d’erreurs : `ApiError`, `HTTPException`, catch-all, `RequestValidationError`.
  * [x] (Optionnel) `ORJSONResponse` en réponse par défaut.

* [x] **`src/chart_mcp/routes/stream.py`** — **Compléter** puis **poser les en-têtes SSE** :

  * [x] Compléter les imports/params (sections `...`).
  * [x] Nettoyage des indicateurs (`indicators` query) → `indicator_specs`.
  * [x] **Headers** :

    ```python
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(iterator, media_type="text/event-stream", headers=headers)
    ```
  * [x] Gérer proprement `asyncio.CancelledError` (fermeture et `streamer.stop()`).

* [x] **`src/chart_mcp/routes/levels.py`** — **Compléter** :

  * [x] Imports et `router = APIRouter(..., tags=["levels"], dependencies=[Depends(require_token), Depends(require_regular_user)])`.
  * [x] Param `max: int = Query(10, ge=1, le=100)` et troncature au top-N par `strength`.
  * [x] Conversion `LevelRange` correcte.

* [x] **`src/chart_mcp/routes/patterns.py`** — **Compléter** :

  * [x] Imports, `tags=["patterns"]`, dépendances.
  * [x] Mapping `PatternResult` → `Pattern`/`PatternPoint` complet.

* [x] **`src/chart_mcp/routes/analysis.py`** — **Compléter** orchestration (imports manquants, tuple de services, `get_services`, route `POST /api/v1/analysis/summary`) :

  * [x] Construction `IndicatorSnapshot`/`RequestedIndicator`.
  * [x] Contrôle de **taille** série minimale (fenêtres requises) → 400 si insuffisant.
  * [x] `include_levels`/`include_patterns` respectés.

## Schémas / Types (sections tronquées à compléter)

* [x] **`src/chart_mcp/schemas/market.py`** — **Compléter** `MarketDataRequest` (symbol min/max, timeframe via validator), `MarketDataResponse` (alias `o/h/l/c/v`, `populate_by_name=True`).

* [x] **`src/chart_mcp/schemas/indicators.py`** — **Compléter** requêtes (`indicator` ∈ {"ma","ema","rsi","macd","bbands"}, `params`), réponses (séries `{ts, ...}`).

* [x] **`src/chart_mcp/schemas/levels.py`** — **Compléter** `Level`, `LevelRange`, `LevelsResponse`, validators.

* [x] **`src/chart_mcp/schemas/patterns.py`** — **Compléter** `Pattern`, `PatternPoint`, `PatternsResponse`.

* [x] **`src/chart_mcp/schemas/streaming.py`** — **Remplacer les placeholders** :

  * [x] Définir unions discriminées par `type` avec `Literal[...]`.
  * [x] Modèles : `ToolEventDetails`, `TokenPayload`, `ResultPartialDetails` (avec `LevelPreview`), `LevelDetail`, `PatternDetail`, `ResultFinalDetails`, `ErrorDetails`, `DoneDetails`, et enveloppes `*StreamPayload`.
  * [x] `StreamEvent` = Union des enveloppes, discriminateur `type`.
  * [x] **Validation stricte** : `TokenPayload.text` non vide, `ResultFinalDetails.summary` non vide.

* [x] **`src/chart_mcp/schemas/finance.py` / `backtest.py` / `common.py`** — **Compléter** les champs tronqués (cagr, sharpe, profit_factor, etc.), metadata Pydantic v2 (`model_config`), validators.

## Services / Providers

* [x] **`src/chart_mcp/services/data_providers/ccxt_provider.py`** — **Compléter** les sections `...` et **ajouter la normalisation du symbole** :

  ```python
  from chart_mcp.utils.errors import BadRequest
  KNOWN_QUOTES = ("USDT","USD","USDC","BTC","ETH","EUR","GBP")

  def normalize_symbol(symbol: str) -> str:
      s = symbol.strip().upper()
      if "/" in s:
          return s
      for q in KNOWN_QUOTES:
          if s.endswith(q) and len(s) > len(q):
              return f"{s[:-len(q)]}/{q}"
      raise BadRequest("Unsupported symbol format")
  ```

  * [x] Appeler `normalize_symbol(symbol)` **avant** `client.fetch_ohlcv`.
  * [x] Mapper timeframe (`ccxt_timeframe`), horodatage **UTC (seconds)**, tri par `ts`.
  * [x] Gérer rate-limit/retry minimal (sleep/backoff) et remonter `UpstreamError` contextuel.

* [x] **`src/chart_mcp/services/indicators.py`** — **Compléter** :

  * [x] Implémenter **MA/EMA** (window), **RSI** (Wilder, window), **MACD** (fast/slow/signal), **Bollinger** (window/stddev).
  * [x] Gestion `NaN` (warmup) cohérente ; sortie DataFrame alignée sur l’index OHLCV.

* [x] **`src/chart_mcp/services/levels.py`** — **Compléter** :

  * [x] Détection `find_peaks` (hauts) et creux ; regroupement par **proximité de prix** (binning), score `strength`, `ts_range`.
  * [x] Paramètre `max_levels: int = 10` ; troncature au top-N.

* [x] **`src/chart_mcp/services/patterns.py`** — **Compléter** :

  * [x] `double top/bottom` (deux sommets/fonds proches + creux/pic central).
  * [x] `triangle` (régressions sur segments convergents).
  * [x] `canal` (lignes quasi-parallèles ; RMSE faible).
  * [x] `confidence` bornée `[0.3, 0.8]` selon symétrie/durée/RMSE.

* [x] **`src/chart_mcp/services/analysis_llm.py`** — **Conserver** le stub heuristique :

  * [x] Résumé **court** (≤ 400 car.) à partir des points saillants (EMA/RSI/MACD/BB + niveaux + patterns).
  * [x] **Jamais** de langage prescriptif (interdire “acheter/vendre/buy/sell”).
  * [x] Retourner un `disclaimer` constant.

* [x] **`src/chart_mcp/services/streaming.py`** — **Compléter toutes les lignes tronquées** et **émettre les événements `metric`** :

  * [x] Mesurer et publier `metric` **après chaque étape** (`data`, `indicators`, `levels`, `patterns`, `summary`) :

    ```python
    import time
    t0 = time.perf_counter();  # fetch data
    ...
    await streamer.publish("metric", {"step":"data","ms":(time.perf_counter()-t0)*1000.0})
    ```
  * [x] En cas d’exception : publier `error` puis `done`, puis `stop()`.
  * [x] Découper le `summary` en phrases et émettre des `token` non vides.

## Utils / Middlewares

* [x] **`src/chart_mcp/utils/timeframes.py`** — **Vérifier** parse/validate et mapping CCXT (toutes TF utilisées en tests).
* [x] **`src/chart_mcp/utils/sse.py`** — **Confirmer** générateur NDJSON + heartbeat (`STREAM_HEARTBEAT_MS`).
* [x] **`src/chart_mcp/utils/errors.py`** — **Uniformiser** les retours JSON (`code`, `message`, `details`, `trace_id`).
* [x] **`src/chart_mcp/utils/logging.py`** — Middleware trace id + durée (**ne pas logguer** de secrets).
* [x] **`src/chart_mcp/utils/ratelimit.py`** — Si placeholders présents, finaliser un **bucket mémoire par token** (ou IP en dev), exposer `X-RateLimit-Remaining` (tests présents).

## MCP (outils + serveur exécutable)

* [x] **`src/chart_mcp/mcp_server.py`** — **Remplacer les `...`** et garantir **sorties JSON** (pas de `DataFrame` vers MCP) :

  * [x] `get_crypto_data` → `frame.to_dict(orient="records")`.
  * [x] `compute_indicator` → `dropna()`, aligner `ts`, retourner `[{ts, ...}]`.
  * [x] `identify_support_resistance` / `detect_chart_patterns` → structures JSON pures.
  * [x] `generate_analysis_summary` → texte + objets.

* [x] **`src/chart_mcp/mcp_main.py`** — **NOUVEAU** : entrypoint serveur MCP

  ```python
  from __future__ import annotations
  import asyncio
  from fastmcp import MCPServer            # adapte au lib choisi
  from chart_mcp import mcp_server as tools

  def register(server: MCPServer)->None:
      server.tool("get_crypto_data")(tools.get_crypto_data)
      server.tool("compute_indicator")(tools.compute_indicator)
      server.tool("identify_support_resistance")(tools.identify_support_resistance)
      server.tool("detect_chart_patterns")(tools.detect_chart_patterns)
      server.tool("generate_analysis_summary")(tools.generate_analysis_summary)

  async def main()->None:
      server = MCPServer()
      register(server)
      await server.serve_stdio()           # ou TCP/WS selon la lib

  if __name__ == "__main__":
      asyncio.run(main())
  ```

---

# 🧪 Tests à **ajouter** / **compléter**

> Objectif : **≥ 80 %** de couverture ; tests verts sur Python 3.11/3.12 ; vérifs SSE/MCP ajoutées.

* [x] **Normalisation symbole** — `tests/unit/services/test_ccxt_provider.py` (ou `test_symbol_normalization.py`)

  * [x] `BTCUSDT` → `BTC/USDT`.
  * [x] `BTC/USDT` inchangé.
  * [x] `FOOBAR` → `BadRequest`.

* [x] **Provider CCXT** — compléter validations :

  * [x] Colonnes `["ts","o","h","l","c","v"]`, `ts` **seconds**, tri par `ts`.
  * [x] Cas **vide** → `UpstreamError`.

* [x] **Indicators** — compléter (BB, MA/EMA, MACD, RSI) pour couvrir **warmup** (`NaN`) et **paramètres** (`window/stddev`).

* [x] **Levels** — `tests/unit/levels/test_support_resistance.py`

  * [x] Tri par `strength` décroissant ; **troncature** avec `max_levels`.

* [x] **Patterns** — tests (channel/triangle/double) : vérifier **confidence** ∈ [0.3, 0.8] selon l’ajustement.

* [x] **Analysis stub** — `tests/unit/services/test_analysis_llm_stub.py`

  * [x] Longueur `summary` ≤ 400 ; **interdiction** de `acheter|vendre|buy|sell`.

* [x] **Routes intégration** — compléter les tests tronqués (sections `...`) :

  * [x] `market` / `indicators` / `levels` / `patterns` / `analysis` : **200**/401/4xx cohérents, payloads exacts.
  * [x] `levels` : couvrir `?max=5`.
  * [x] **SSE** — `tests/integration/test_stream_sse.py` : séquence `tool_start` → `result_partial` → `token` → `result_final` → `done`.
  * [x] **SSE headers** — **nouveau** `tests/integration/test_stream_headers.py` : vérifier headers (`no-cache`, `keep-alive`, `X-Accel-Buffering: no`) et présence **d’au moins un** `event: metric`.

* [x] **MCP runtime (smoke)** — **nouveau** `tests/unit/mcp/test_server_runtime.py`

  ```python
  import importlib
  def test_tools_registered():
      m = importlib.import_module("chart_mcp.mcp_main")
      class Dummy:
          def __init__(self): self.names=[]
          def tool(self, name):
              def deco(fn): self.names.append(name); return fn
              return deco
      server = Dummy()
      m.register(server)
      for name in ["get_crypto_data","compute_indicator","identify_support_resistance","detect_chart_patterns","generate_analysis_summary"]:
          assert name in server.names
  ```

---

# 📎 Patches prêts-à-coller (extraits clés)

**Headers SSE (route)**

```python
# src/chart_mcp/routes/stream.py
headers = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
return StreamingResponse(iterator, media_type="text/event-stream", headers=headers)
```

**Événements metrics (streaming)**

```python
# src/chart_mcp/services/streaming.py
import time
t0 = time.perf_counter();  # fetch data
...
await streamer.publish("metric", {"step":"data","ms":(time.perf_counter()-t0)*1000.0})
# idem pour "indicators", "levels", "patterns", "summary"
```

**Normalisation symbole (provider)**

```python
# src/chart_mcp/services/data_providers/ccxt_provider.py
KNOWN_QUOTES = ("USDT","USD","USDC","BTC","ETH","EUR","GBP")
def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if "/" in s: return s
    for q in KNOWN_QUOTES:
        if s.endswith(q) and len(s) > len(q):
            return f"{s[:-len(q)]}/{q}"
    raise BadRequest("Unsupported symbol format")

# Dans get_ohlcv(...):
symbol = normalize_symbol(symbol)
```

**MCP JSON (pas de DataFrame)**

```python
# src/chart_mcp/mcp_server.py
def get_crypto_data(...)-> list[dict]:
    frame = _provider.get_ohlcv(...)
    return frame.to_dict(orient="records")
```

**Entrée MCP exécutable**

```python
# src/chart_mcp/mcp_main.py
from fastmcp import MCPServer
from chart_mcp import mcp_server as tools
def register(server: MCPServer)->None:
    server.tool("get_crypto_data")(tools.get_crypto_data)
    server.tool("compute_indicator")(tools.compute_indicator)
    server.tool("identify_support_resistance")(tools.identify_support_resistance)
    server.tool("detect_chart_patterns")(tools.detect_chart_patterns)
    server.tool("generate_analysis_summary")(tools.generate_analysis_summary)
```

**Docker HEALTHCHECK (fix)**

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

---

# 🏁 Tests & build — rappels fermes

* **Couverture** : `pytest --cov=src --cov-report=xml` **≥ 80 %** (ajouter les nouveaux tests jusqu’à l’atteindre).
* **Qualité** : `ruff` / `black` / `isort` **sans erreur** ; `mypy src` **strict** (0 erreur).
* **Sécurité** : toutes les routes hors `/health` exigent `Authorization: Bearer` ; **ne jamais** logguer les secrets.
* **Docker** : image slim, user non-root, **HEALTHCHECK** corrigé, port 8000, `CMD uvicorn`.
* **SSE** : headers présents, heartbeat régulier (env `STREAM_HEARTBEAT_MS`), flux contenant `metric`.
* **Neutralité** : **aucun** texte prescriptif (acheter/vendre).

---

si tu coches **tout** ci-dessus (et **remplaces chaque `...` par du code réel**), on verrouille une **alpha exploitable et propre** : API + SSE en prod, **serveur MCP opérationnel**, outputs **JSON stables**, tests **verts** et CI **solide**. Ensuite seulement, on pourra attaquer les “nice-to-have” (orjson global, métriques Prometheus, cache OHLCV, etc.).

---

Historique récent:
- 2025-10-25T11:20:02Z : Remplacement complet d'`AGENTS.md` par la nouvelle checklist fournie et ajout de la date/hash courants.
- 2025-10-25T11:25:03Z : Vérification docs (README, CONTRIBUTING), normalisation Makefile (tabs + cibles), contrôle dépendances/CI, et mise à jour du HEALTHCHECK Docker.
- 2025-10-25T11:33:39Z : Ajout du garde-fou 400 points sur `/analysis`, extension du jeu OHLCV test, nouveau test d'échec historique insuffisant et validation globale des cases de la checklist.
- 2025-10-25T12:18:21Z : Ajout d'un test unitaire garantissant l'émission des métriques `metric` à chaque étape du pipeline SSE.
- 2025-10-25T12:45:07Z : Uniformisation des symboles dans le flux SSE (`BTC/USDT`) et ajout d'un test async vérifiant l'événement `tool_start` normalisé.
- 2025-10-25T13:20:00Z : Documentation SSE alignée sur la normalisation `BASE/QUOTE` et test unitaire couvrant la propagation des erreurs d'indicateur dans le pipeline streaming.
- 2025-10-25T13:48:35Z : Correction des avertissements Ruff D202 en supprimant les lignes vides après docstrings dans les tests streaming ; vérifications `ruff` et `pytest` effectuées.
