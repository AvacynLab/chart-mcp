2025-10-25T08:45:50Z — 769b62394552a6693cf9b3fa76327a9e862c810b

# 🎯 Brief à l’agent (objectifs fin d’alpha)

* **Périmètre** : crypto-only, API HTTP sécurisée + **SSE** en production, **tools MCP exposés par un vrai serveur MCP**, indicateurs (MA/EMA/RSI/MACD/BB), supports/résistances, patterns simples (double top/bottom, triangle, canal), **analyse IA pédagogique** (jamais prescriptive).
* **Correctifs prioritaires** :

  1. Remplacer **tous les `...`** laissés dans le code par des implémentations **fonctionnelles et testées**.
  2. Ajouter un **serveur MCP exécutable** (entrypoint + dépendance).
  3. Ajouter les **en-têtes SSE** côté serveur et les **événements `metric`** (mesures per-étape) dans le flux.
  4. **Normaliser les symboles** (accepter `BTCUSDT` et `BTC/USDT`, conversion vers `BASE/QUOTE`).
  5. Fixer le **HEALTHCHECK Docker**.
  6. Ajouter **`.env.example`** et **Makefile avec TABs**.
  7. Compléter/ajouter les **tests** (MCP runtime, SSE headers/metrics, normalisation symboles) pour **≥ 80 %** de couverture.
* **Invariants** : 0 erreur lint/type, Docker slim non-root, **pas de conseil d’investissement**.

---

# ✅ Liste de tâches à cocher — **fichier par fichier** (supprime les anciennes tâches et garde uniquement celles-ci)

## Racine / Documentation / DX

* [x] **`AGENTS.md`** — **ÉCRASER** le contenu actuel et coller **cette** liste (source de vérité).

  * [x] Supprimer l’historique/anciennes consignes.
  * [x] Ajouter en tête : **date** + **commit hash** courant.

* [x] **`README.md`** — **Mettre à jour** usage et exemples.

  * [x] Dans tous les exemples, préciser que l’API **accepte** `BTCUSDT` **et** `BTC/USDT` ; noter que le provider **normalise** en `BASE/QUOTE`.
  * [x] Ajouter un exemple complet `POST /api/v1/indicators/compute` (body + réponse).
  * [x] Ajouter des exemples `GET /api/v1/levels` et `GET /api/v1/patterns` (avec query `timeframe`, `max` pour levels).
  * [x] **SSE** : documenter **headers** côté serveur (`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`), le **format NDJSON** (`event:` + `data:`), et une trace d’événements attendus (`tool_start`, `result_partial`, `metric`, `token`, `result_final`, `done`).
  * [x] Ajouter une section **“Serveur MCP”** : comment l’installer (**nouvelle dépendance**), **le lancer** (`make mcp-run`) et **noms de tools** exposés.

* [x] **`CONTRIBUTING.md`** — Vérifier la section env et **référencer** `.env.example`.

* [x] **`.env.example`** — **Créer** le fichier :

  ```dotenv
  API_TOKEN=changeme_dev_token
  EXCHANGE=binance
  ALLOWED_ORIGINS=http://localhost:3000
  LLM_PROVIDER=stub
  LLM_MODEL=heuristic-v1
  STREAM_HEARTBEAT_MS=5000
  LOG_LEVEL=INFO
  # Optionnel si tu ajoutes un rate-limit :
  RATE_LIMIT_PER_MINUTE=60
  ```

* [x] **`Makefile`** — **Remettre des TABs** devant les commandes (Make exige des TABs, pas des espaces).

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

* [x] **`requirements.txt`** — **Ajouter** la dépendance serveur MCP (p.ex. `fastmcp` — épingle une version stable) pour pouvoir lancer un **vrai** serveur MCP.

* [x] **`.github/workflows/ci.yml`** — **Renforcer** la CI :

  * [x] Ajouter un step `format-check` (black/isort en mode check) en plus de `ruff`.
  * [x] Conserver `--cov=src --cov-report=xml` et publier `coverage.xml`.
  * [x] **Nouveau job** léger `mcp-smoke` (3.11) : installe deps + MCP, **importe** `chart_mcp.mcp_main:register` et vérifie l’enregistrement des tools (sans lancer un vrai serveur réseau).
  * [x] (Optionnel) ajouter un lint Docker (hadolint).

* [x] **`docker/Dockerfile`** — **Corriger le HEALTHCHECK** (la commande actuelle n’est pas valide) :

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

## App FastAPI / Routes / SSE

* [x] **Remplacer tous les `...` dans le code** par une implémentation **complète** (voir liste des fichiers touchés plus bas).

* [x] **`src/chart_mcp/app.py`** — Terminer la **factory** :

  * [x] Construire `allowed_origins = settings.allowed_origins` ; monter `CORSMiddleware` et `GZipMiddleware`.
  * [x] Monter **toutes** les routes (`health`, `market`, `indicators`, `levels`, `patterns`, `analysis`, `stream`).
  * [x] Ajouter les handlers d’erreurs (`ApiError`, `HTTPException`, exceptions génériques) et le middleware logging.
  * [x] (Optionnel) définir `ORJSONResponse` comme classe de réponse par défaut.

* [x] **`src/chart_mcp/routes/stream.py`** — **Ajouter les en-têtes SSE** et robustesse :

  ```python
  headers = {
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
  }
  return StreamingResponse(iterator, media_type="text/event-stream", headers=headers)
  ```

  * [x] Gérer proprement `asyncio.CancelledError` (fermeture du flux et `streamer.stop()`).

* [x] **`src/chart_mcp/routes/market.py` / `indicators.py` / `levels.py` / `patterns.py` / `analysis.py`** — **Compléter** le code manquant (remplacer `...`) et :

  * [x] S’assurer que **toutes** les routes sont protégées par `Depends(require_token)` (sauf `/health`).
  * [x] **Accepter** `BTCUSDT` et `BTC/USDT` (voir normalisation symbole ci-dessous).
  * [x] **`levels`** : ajouter un paramètre `max` (ex. `?max=10`) et tronquer la liste renvoyée.

## Services / Providers / Symboles / SSE Metrics

* [x] **`src/chart_mcp/services/data_providers/ccxt_provider.py`** — **Ajouter la normalisation des symboles** (et remplacer les `...`) :

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

  * [x] Appeler `normalize_symbol(symbol)` **avant** `client.fetch_ohlcv(...)`.
  * [x] Compléter les parties ellipsées : mapping timeframe (`ccxt_timeframe`), **retry/backoff**, tri/UTC, validations.

* [x] **`src/chart_mcp/services/indicators.py`** — **Compléter** le code (retirer les `...`) :

  * [x] Implémenter **RSI** complet (Wilder), **MACD** (fast/slow/signal), **Bollinger** (window/stddev), gérer warmup `NaN`.
  * [x] Service `IndicatorService.compute(frame, indicator, params)` pour MA/EMA/RSI/MACD/BB.
  * [x] Garder les signatures stables pour les tests.

* [x] **`src/chart_mcp/services/levels.py`** — **Compléter** :

  * [x] Détection des pics `find_peaks` (hauts) et **troughs** (bas) ; **regroupement** par proximité de prix, calcul `strength`, `ts_range`.
  * [x] **Paramètre** `max_levels: int = 10` dans le service et route.

* [x] **`src/chart_mcp/services/patterns.py`** — **Compléter** :

  * [x] `double top/bottom` (deux sommets/fonds proches + creux/pic central),
  * [x] `triangle` (obliques convergentes),
  * [x] `canal` (bandes parallèles).
  * [x] **Confidence** bornée (p.ex. 0.3–0.8) en fonction de la qualité d’ajustement (durée/symétrie/RMSE).

* [x] **`src/chart_mcp/services/analysis_llm.py`** — **Conserver** le stub heuristique :

  * [x] Résumé court (≤ 400 car.) à partir des **points saillants** (MA/EMA/RSI/MACD/BB + proximité niveaux + présence patterns).
  * [x] **Jamais** de langage prescriptif (interdire ces mots : acheter/vendre/buy/sell).
  * [x] Retourner aussi un `disclaimer` constant.

* [x] **`src/chart_mcp/services/streaming.py`** — **Émettre les événements `metric`** et retirer les `...` :

  * [x] Mesurer et publier `metric` **après chaque étape** (data, indicators, levels, patterns, summary) :

    ```python
    import time
    t0 = time.perf_counter(); ... ; await streamer.publish("metric", {"step":"data","ms":(time.perf_counter()-t0)*1000.0})
    ```
  * [x] Sur exception : publier `error` puis `done`, puis `stop()` (ne pas bloquer le client).

* [x] **`src/chart_mcp/utils/*`** — **Compléter** là où il reste des `...` :

  * [x] `timeframes.py` (parse/validate TF + mapping CCXT),
  * [x] `sse.py` (streamer NDJSON + heartbeat à partir de `STREAM_HEARTBEAT_MS`),
  * [x] `errors.py` (erreurs JSON normalisées),
  * [x] `logging.py` (middleware trace id, pas de logs de secrets).

## Schémas / App / MCP

* [x] **`src/chart_mcp/schemas/*.py`** — **Remplacer les `...`** et figer les sorties :

  * [x] `market.py` (`OhlcvRow`, `MarketDataResponse` complets),
  * [x] `indicators.py`, `levels.py`, `patterns.py`, `analysis.py` : champs **exacts** attendus par les tests (types numériques, `@validator` pour uppercasing du symbole si besoin).
  * [x] `streaming.py` — remplacer le **pattern regex** par un **type fort** :

    ```python
    from typing import Literal
    EventType = Literal["tool_start","tool_end","tool_log","token","result_partial","result_final","metric","error","done"]

    class StreamEvent(BaseModel):
        type: EventType
        payload: Dict[str, Any] = Field(default_factory=dict)
    ```

* [x] **`src/chart_mcp/app.py`** — **Finir** le wiring (voir plus haut) ; veiller à **ne pas logguer** `Authorization`.

## MCP : exposition réelle des tools

* [x] **`src/chart_mcp/mcp_server.py`** — **Garder** les fonctions métier, **mais** :

  * [x] **Ne renvoie pas** de `pandas.DataFrame` aux clients MCP. **Sérialise en JSON** (listes de dicts) :

    ```python
    def get_crypto_data(...)-> list[dict]:
        frame = _provider.get_ohlcv(...)
        return frame.to_dict(orient="records")
    ```

    Idem pour `compute_indicator` (aligner `ts` et valeurs, `dropna()`), `identify_support_resistance`, `detect_chart_patterns`, `generate_analysis_summary` (déjà JSON-like).
* [x] **`src/chart_mcp/mcp_main.py`** — **NOUVEAU** : entrypoint serveur MCP

  ```python
  from __future__ import annotations
  import asyncio
  from fastmcp import MCPServer           # adapte à la lib retenue
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
      await server.serve_stdio()          # ou TCP/WS selon la lib

  if __name__ == "__main__":
      asyncio.run(main())
  ```

---

# 🧪 Tests à **ajouter** / **compléter**

> Objectif : **≥ 80 %** de couverture, tests verts sur Python 3.11/3.12, et vérifs SSE/MCP nouvelles.

* [x] **Normalisation symbole** — `tests/unit/services/test_symbol_normalization.py` (nouveau)

  * [x] `BTCUSDT` → `BTC/USDT`.
  * [x] `BTC/USDT` → inchangé.
  * [x] `FOOBAR` → `BadRequest`.

* [x] **Provider CCXT** — `tests/unit/services/test_ccxt_provider.py` (compléter les `...`)

  * [x] Vérifier les colonnes `["ts","o","h","l","c","v"]`, tri par `ts`, `ts` en **secondes**.
  * [x] Cas **vide** → `UpstreamError`.

* [x] **Indicators** — compléter les tests existants (BB, MA/EMA, MACD, RSI) pour couvrir **warmup** (`NaN`) et **paramètres** (`window/stddev`).

* [x] **Levels** — `tests/unit/levels/test_support_resistance.py` (compléter)

  * [x] Tri par `strength` décroissant ; **troncature** avec `max_levels`.

* [x] **Patterns** — tests existants (channel/triangle/double) : compléter si nécessaire pour vérifier **confidence** ∈ [0.3,0.8].

* [x] **Analysis stub** — `tests/unit/services/test_analysis_llm_stub.py` (compléter)

  * [x] Longueur `summary` ≤ 400 ; **interdiction** de `acheter|vendre|buy|sell`.

* [x] **Routes intégration** — compléter `tests/integration/*.py` (les `...`) :

  * [x] `market_routes.py` / `indicators_routes.py` / `levels_routes.py` / `patterns_routes.py` / `analysis_routes.py` : **200**/401/4xx cohérents, payloads exacts.
  * [x] `test_levels_routes.py` : couvrir `?max=5`.
  * [x] **SSE** — `test_stream_sse.py` : garder la séquence `tool_start` → `result_final` → `done`.
  * [x] **SSE headers** — **NOUVEAU** `tests/integration/test_stream_headers.py` : vérifier headers (`no-cache`, `keep-alive`, `X-Accel-Buffering: no`) et présence **d’au moins un** `event: metric`.

* [x] **MCP runtime (smoke)** — `tests/unit/mcp/test_server_runtime.py` (nouveau)

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

**SSE headers (route)**

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
# ...
await streamer.publish("metric", {"step": "data", "ms": (time.perf_counter() - t0) * 1000.0})
# répéter pour "indicators", "levels", "patterns", "summary"
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
from fastmcp import FastMCP

class MCPServer:
    def __init__(self, name: str | None = None, instructions: str | None = None) -> None:
        self._inner = FastMCP(name=name, instructions=instructions)

    def tool(self, name: str):
        return self._inner.tool(name)

    async def serve_stdio(self) -> None:
        await self._inner.run_stdio_async(show_banner=False)


from chart_mcp import mcp_server as tools


def register(server: MCPServer) -> None:
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

# 🏁 Ce que tu dois **impérativement** respecter (tests & build)

* **Couverture** : `pytest --cov=src --cov-report=xml` **≥ 80 %** (ajoute les nouveaux tests jusqu’à l’atteindre).
* **Qualité** : `ruff`/`black`/`isort` sans erreur ; `mypy src` strict (0 erreur).
* **Sécurité** : toutes les routes hors `/health` exigent `Authorization: Bearer` ; ne pas logguer les secrets.
* **Docker** : image slim, user non-root, HEALTHCHECK corrigé, port 8000, `CMD uvicorn`.
* **SSE** : headers présents, heartbeat régulier (env `STREAM_HEARTBEAT_MS`).
* **Neutralité** : **aucun** texte prescriptif (acheter/vendre).

---

Si tu coches **tous** ces points (et **remplaces chaque `...` par du code réel**), on verrouille une **alpha exploitable et propre** : API + SSE en prod, **serveur MCP opérationnel**, outputs **JSON stables**, tests **verts** et CI **solide**. Ensuite seulement, on pourra ouvrir la porte aux features “plus” (rate-limit global, orjson par défaut, métriques Prometheus, etc.).

---

Historique récent:
- 2025-10-25T07:15:19Z : Réinitialisation d'`AGENTS.md` avec la nouvelle checklist, renforcement du streamer SSE (gardes sur le heartbeat + commentaires) dans `src/chart_mcp/utils/sse.py` et exécution de `pytest tests/integration/test_stream_headers.py`.
- 2025-10-25T07:19:43Z : Création de `.env.example`, vérification des TABs du `Makefile`, validation de `fastmcp` dans `requirements.txt`, mise à jour du `docker/Dockerfile` (HEALTHCHECK inline + commentaires) et exécution de `pytest tests/integration/test_stream_headers.py`.
- 2025-10-25T07:24:08Z : Mise à jour détaillée de `README.md` (exemples symboles compact/normalisés, SSE headers/metric, section MCP) et ajustement des coches dans `AGENTS.md`.
- 2025-10-25T07:28:26Z : Documentation environnement enrichie dans `CONTRIBUTING.md`, CI ajustée (`lint` avec étape `format-check` nommée, job `mcp-smoke` réduit au registre) et exécution de `pytest tests/unit/services/test_symbol_normalization.py`.
- 2025-10-25T07:36:41Z : Renforcement des tests unitaires (provider CCXT, niveaux, patterns, MCP runtime), ajout du stub `fastmcp` pour la fumée et exécution de `pytest tests/unit`.
- 2025-10-25T08:21:04Z : Finalisation du schéma marché (`src/chart_mcp/schemas/market.py`), mise à jour de la checklist associée et exécution de `pytest tests/integration/test_market_routes.py`.
- 2025-10-25T08:26:54Z : Refonte de `src/chart_mcp/mcp_main.py` selon l'interface `MCPServer`, mise à jour du stub `fastmcp/__init__.pyi`, alignement du test fumée MCP et exécution de `pytest tests/unit/mcp/test_server_runtime.py`.
- 2025-10-25T08:33:43Z : Refactorisation du stub d'analyse LLM (retour structuré + neutralisation lexicale), adaptation du streaming SSE/MCP pour consommer le nouveau format, nettoyage des utilitaires SSE/erreurs et exécution de `pytest tests/unit/services/test_analysis_llm_stub.py tests/integration/test_analysis_routes.py tests/unit/mcp/test_server_runtime.py`.
- 2025-10-25T08:45:50Z : Normalisation complète des schémas indicateurs/niveaux/patterns/analyse (validators, symboles `BASE/QUOTE`), mise à jour des routes d'analyse/indicateurs pour propager les métadonnées structurées, enrichissement du service MACD (warmup NaN) et extension des tests indicateurs (MA/EMA/RSI/MACD/BB) + `pytest tests/unit/indicators -q` puis `pytest tests/integration/test_indicators_routes.py -q`.
- 2025-10-25T09:02:56Z : Couverture des routes d'intégration (401/400) pour indicateurs/niveaux/patterns/analyse, validation de l'ordre SSE `tool_start`→`result_final`→`done`, et ajout des assertions d'erreur normalisées + `pytest tests/integration/test_indicators_routes.py tests/integration/test_levels_routes.py tests/integration/test_patterns_routes.py tests/integration/test_analysis_routes.py tests/integration/test_stream_sse.py`.
- 2025-10-25T09:29:40Z : Durcissement de la factory FastAPI (origines strictes), gestion de `CancelledError` côté `/stream/analysis`, wrapper `StreamingService` exposant `stop` et test d'annulation dédié + `pytest tests/unit/services/test_streaming_service.py tests/integration/test_stream_sse.py`.
- 2025-10-25T09:47:12Z : Adaptation de `mcp_main` pour envelopper `fastmcp.FastMCP`, fin des ellipses fonctionnelles, renforcement du stub `fastmcp` pour les tests (capture des enregistrements et des appels stdio) et ajout d'un test vérifiant `show_banner=False` + `pytest tests/unit/mcp/test_server_runtime.py`.
