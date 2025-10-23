Remet à zero le fichier AGENTS.md et importe la liste des taches fournit ci dessous ainsi que les informations (au mot près) dans le fichier. Une fois effectué, commence l'implementation, et prend ton temps. 

----------
Voici ta **liste de tâches à cocher**, pensée **pour un agent IA** chargé de finaliser l’alpha de `chart-mcp`. Le dépôt est **vide à date** (aucun fichier) — je définis donc une arborescence minimale, puis je te donne les objectifs, les correctifs/ajouts attendus, les tâches **fichier par fichier**, et les exigences **tests & build**. ([GitHub][1])

---

## 🎯 Brief à l’agent (objectifs et contraintes à respecter)

1. **Objectif fonctionnel (alpha, crypto-only)**

* Tu dois livrer un **serveur MCP** (Python) qui expose des **tools** pour :
  a) récupérer OHLCV de n’importe quel asset **crypto** et **timeframe** au choix,
  b) **calculer** des **indicateurs** paramétrables (MA/EMA/RSI/MACD/Bollinger au minimum),
  c) **détecter** des **supports/résistances** basiques,
  d) **reconnaître** quelques **figures chartistes** (double top/bottom, triangle, canal) en version simple,
  e) produire une **synthèse IA** courte et pédagogique de l’analyse (sans “prendre position”).
* Tu dois exposer une **API HTTP** publique sécurisée (token) **+ un flux de streaming** (SSE) permettant d’afficher **en temps réel** :

  * le **texte IA** en streaming,
  * et/ou des **étapes/outils** (logs d’outils + résultats partiels) pour affichage dans un front type `vercel/ai-chatbot`.

2. **Choix techniques imposés (pour l’alpha)**

* **Python** (plus rapide à itérer pour TA/figures) : FastAPI, uvicorn, SSE (Server-Sent Events), `pydantic` pour schémas, `pandas`/`numpy`/`ta` (ou `TA-Lib`) pour indicateurs, `scipy` pour pics (supports/résistances), **CCXT** pour data marchés (Binance & co).
* **MCP** : définir les **tools** (couches “service” réutilisées par API et MCP).
* **Sécurité** : auth par **API token** (Bearer), **CORS** configuré.
* **Extensibilité** : couches “provider” (data), “service” (TA/patterns/levels), “tools” (MCP), “routes” (API). Pas d’hardcode crypto partout : passer par interfaces.
* **Streaming** : SSE pour texte IA **et** événements outils (NDJSON).
* **Observabilité** : logs structurés (JSON), métriques simples (temps de calcul indicateurs, latence IO).

3. **Tests & build à respecter**

* **Tests unitaires** (services, parsers, validateurs), **tests d’intégration** (routes/API, SSE), **snapshot tests** pour payloads JSON.
* **Seuil couverture** : 80 % (rapports `coverage.xml`).
* **Linters/formatters** : `ruff`, `black`, `isort`; **typing** : `mypy` strict sur `src/`.
* **CI GitHub Actions** : lint + type-check + tests + build (Docker) sur push/PR main.
* **Docker** : image slim, non-root, multi-stage, healthcheck.
* **Docs** : README (usage/API/auth/stream), CONTRIBUTING, .env.example.
* **Pas de prise de position** : la synthèse IA explique, **n’ordonne pas** (pas de “achète/vends”).

---

## 📁 Arborescence proposée (alpha)

```
chart-mcp/
  README.md
  LICENSE
  CONTRIBUTING.md
  .gitignore
  .editorconfig
  pyproject.toml
  uv.lock                      # si uv/poetry ; sinon requirements.txt
  requirements.txt             # si pip
  .env.example
  docker/
    Dockerfile
    docker-compose.dev.yml
  .github/workflows/ci.yml
  src/chart_mcp/
    __init__.py
    config.py
    app.py                     # FastAPI app + mounting routes + SSE
    mcp_server.py              # enregistrement des tools (MCP)
    schemas/
      common.py
      market.py
      indicators.py
      patterns.py
      levels.py
      analysis.py
      streaming.py
    routes/
      health.py
      auth.py
      market.py
      indicators.py
      patterns.py
      levels.py
      analysis.py
      stream.py
    services/
      data_providers/
        base.py
        ccxt_provider.py
      indicators.py
      patterns.py
      levels.py
      analysis_llm.py
      streaming.py
    utils/
      sse.py
      logging.py
      timeframes.py
      errors.py
  tests/
    conftest.py
    unit/
      test_timeframes.py
      indicators/
        test_ma_ema.py
        test_rsi.py
        test_macd.py
        test_bbands.py
      patterns/
        test_double_top_bottom.py
        test_triangle.py
        test_channel.py
      levels/
        test_support_resistance.py
      services/
        test_ccxt_provider.py
        test_analysis_llm_stub.py
    integration/
      test_market_routes.py
      test_indicators_routes.py
      test_patterns_routes.py
      test_levels_routes.py
      test_analysis_routes.py
      test_stream_sse.py
    snapshots/
      indicators_payload.json
      analysis_summary.json
```

---

## ✅ Liste de tâches à cocher — **générales** (avant le fichier-par-fichier)

* [x] **Initialiser** le dépôt avec l’arborescence ci-dessus (fichiers vides où nécessaire) et un **README minimal** (lancer le serveur, appel d’un endpoint, exemple SSE).
* [x] **Choisir le gestionnaire** : `uv` (recommandé) **ou** `pip/venv` **ou** `poetry`.

  * [x] Si `uv`/`poetry` : générer `pyproject.toml` + lock ; sinon `requirements.txt`.
* [x] **Ajouter dépendances** : `fastapi`, `uvicorn[standard]`, `pydantic`, `pandas`, `numpy`, `ccxt`, `ta` (ou `TA-Lib` si dispo), `scipy`, `httpx`, `python-dotenv`, `orjson`, `ujson`, `sse-starlette` (ou SSE natif), `loguru` (ou std logging), `mypy`, `ruff`, `black`, `isort`, `pytest`, `pytest-asyncio`, `pytest-cov`, `freezegun`.
* [x] **Configurer linters/formatters** dans `pyproject.toml` (ruff + black + isort, règles strictes).
* [x] **Configurer mypy** (strict sur `src/chart_mcp` ; `disallow_any_generics = True`; `warn_return_any = True`).
* [x] **Configurer CI** GitHub Actions (`.github/workflows/ci.yml`) : setup Python, cache deps, `ruff`, `mypy`, `pytest -q --cov`, build Docker.
* [x] **Configurer Docker** multi-stage, non-root, slim, `HEALTHCHECK` GET `/health`.
* [x] **.env.example** : `API_TOKEN=...`, `EXCHANGE=binance`, `LLM_PROVIDER=stub`, `LOG_LEVEL=INFO`, throttle limites, CORS origins.
* [x] **Politique d’erreurs** : JSON d’erreur uniforme (`code`, `message`, `details`, `trace_id`), mapping exceptions/HTTP.

---

## 🧩 Tâches **fichier par fichier** (avec sous-étapes)

### `README.md`

* [x] **But** : expliquer **ce qu’est** l’alpha, **comment lancer**, **comment appeler** l’API et **consommer** le **SSE**.
* [x] **Inclure** : exemple curl `GET /api/v1/market/ohlcv?symbol=BTCUSDT&tf=1h&limit=500`, exemple SSE `GET /stream/analysis?...`, exemple de **payload** (voir `schemas`), mention **limites alpha** (crypto only, pas de conseil).

### `pyproject.toml` / `requirements.txt`

* [x] **Lister** toutes les deps (voir section générales).
* [x] **Configurer** :

  * [x] `tool.black` (line-length 100),
  * [x] `tool.isort` (profile black),
  * [x] `tool.ruff` (pydocstyle, flake8-bugbear, flake8-simplify; exclude tests snapshots),
  * [x] `tool.mypy` (strict),
  * [x] `tool.pytest.ini_options` (markers, asyncio).

### `docker/Dockerfile`

* [x] Multi-stage : builder (avec deps), puis runner (slim).
* [x] User non-root, `WORKDIR /app`, copier `src/`, `pyproject.toml`/`requirements.txt`.
* [x] `CMD ["uvicorn", "chart_mcp.app:app", "--host", "0.0.0.0", "--port", "8000"]`
* [x] `HEALTHCHECK` sur `/health`.

### `.github/workflows/ci.yml`

* [x] Jobs : `lint`, `typecheck`, `test`, `build`.
* [x] Artifacts : `coverage.xml`.
* [x] Matrices Python (3.11/3.12).
* [x] Cache pip/uv.

### `src/chart_mcp/config.py`

* [x] Charger `.env`; valider via `pydantic` : `API_TOKEN`, `EXCHANGE`, `ALLOWED_ORIGINS`, `LLM_PROVIDER`, `LLM_MODEL`, `STREAM_HEARTBEAT_MS`.
* [x] Exposer `settings`.

### `src/chart_mcp/utils/logging.py`

* [x] Logger JSON (trace_id par requête).
* [x] Intercepteurs FastAPI pour corréler logs <-> requêtes.

### `src/chart_mcp/utils/errors.py`

* [x] Exceptions custom (`BadRequest`, `Unauthorized`, `UpstreamError`).
* [x] Handlers FastAPI (retour JSON uniforme).

### `src/chart_mcp/utils/sse.py`

* [x] Générateur SSE **compatible Vercel SDK** : `event: <name>\ndata: <ndjson>\n\n`
* [x] **NDJSON** standardisé : `{"type":"token|tool|metric|done","payload":{...}}`
* [x] **Heartbeat** (comment `: ping`) toutes X secondes.

### `src/chart_mcp/utils/timeframes.py`

* [x] Parser/valideur **timeframe** (`1m`,`5m`,`15m`,`1h`,`4h`,`1d`,`1w`) -> seconds.
* [x] Mapping CCXT (granularité supportée par exchange).

### `src/chart_mcp/app.py`

* [x] **Créer** app FastAPI ; **monter** routes `/api/v1/...` + `/stream/...` + `/health`.
* [x] **CORS** : depuis front (wildcard en dev).
* [x] **Auth** Bearer middleware (valide `API_TOKEN`).
* [x] **Compression** GZip.
* [x] **Erreur** handlers (utils.errors).
* [x] **OpenAPI** tags & examples (bonus).

### `src/chart_mcp/routes/health.py`

* [x] `GET /health` : `{status:"ok",version, uptime, exchange}`.

### `src/chart_mcp/routes/auth.py`

* [x] Déco `requires_auth` (ou middleware global) : valide token.
* [x] Réponses 401 uniformisées.

### `src/chart_mcp/schemas/common.py`

* [x] `Symbol`, `Timeframe`, `DatetimeRange`, `ApiError`, `Paged`.

### `src/chart_mcp/schemas/market.py`

* [x] Requêtes : `symbol`, `timeframe`, `limit`, `start`, `end`.
* [x] Réponse : `OHLCV[]` (ts, open, high, low, close, volume, source).

### `src/chart_mcp/routes/market.py`

* [x] `GET /api/v1/market/ohlcv`

  * [x] Valider params (timeframe, date range, limit max).
  * [x] Appeler provider (ccxt).
  * [x] Retourner OHLCV normalisé.
* [x] **Erreurs** upstream -> `UpstreamError`.

### `src/chart_mcp/services/data_providers/base.py`

* [x] Interface : `get_ohlcv(symbol, timeframe, limit|start/end) -> pd.DataFrame[ts, o,h,l,c,v]`.

### `src/chart_mcp/services/data_providers/ccxt_provider.py`

* [x] Implémenter via **CCXT** : gestion rate limits, retry/backoff.
* [x] Normaliser colonnes, timezone UTC.
* [x] Map symbole user (`BTCUSDT`) -> exchange si besoin.

### `src/chart_mcp/schemas/indicators.py`

* [x] Entrée : `symbol`, `timeframe`, `indicator` (`"ema"|"ma"|"rsi"|"macd"|"bbands"`), `params` dict.
* [x] Sortie : tableau `[{ts, value(s)}]` + métadonnées (window, source).

### `src/chart_mcp/services/indicators.py`

* [x] **Implémenter** :

  * [x] **MA/EMA** (window param),
  * [x] **RSI** (window),
  * [x] **MACD** (fast/slow/signal),
  * [x] **Bollinger** (window, stddev).
* [x] Entrée: DataFrame OHLCV ; Sortie: DataFrame indicateur(s).
* [x] **Edge-cases** : NaN warmup, taille min série, timezones.

### `src/chart_mcp/routes/indicators.py`

* [x] `POST /api/v1/indicators/compute`

  * [x] Body: `schemas.indicators.Request`.
  * [x] Fetch OHLCV si non fourni.
  * [x] Appel `services.indicators`.
  * [x] Retour JSON compact (ORJSON).

### `src/chart_mcp/schemas/levels.py`

* [x] Sortie : `levels: [{price, strength, kind: "support|resistance", ts_range}]`.

### `src/chart_mcp/services/levels.py`

* [x] Détection **supports/résistances** via pics (scipy.signal.find_peaks) + **regroupement** par proximité en prix (binning) + score de **fréquence**/**proximité**.
* [x] Paramètres (sensibilité/écart relatif).
* [x] Retour niveaux triés (top N).

### `src/chart_mcp/routes/levels.py`

* [x] `GET /api/v1/levels?symbol=&timeframe=` -> appelle service + renvoie top N niveaux.

### `src/chart_mcp/schemas/patterns.py`

* [x] Sortie : `patterns: [{name, score, start_ts, end_ts, points: [{ts, price}], confidence}]`.

### `src/chart_mcp/services/patterns.py`

* [x] Détection **simple** :

  * [x] **Double top/bottom** : deux sommets/fonds de hauteur proche, creux/pic central.
  * [x] **Triangle** : obliques convergentes (régression linéaire segments).
  * [x] **Canal** : deux lignes parallèles englobant prix (écart min).
* [x] Métriques de **score** (symétrie, distance, durées).
* [x] *(Optionnel)* intégrer lib tierce si fiable ; sinon algo maison minimal.

### `src/chart_mcp/routes/patterns.py`

* [x] `GET /api/v1/patterns?symbol=&timeframe=` -> renvoie patterns triés par score.

### `src/chart_mcp/schemas/analysis.py`

* [x] Entrée : `symbol`, `timeframe`, `indicators: [{name, params}]` (facultatif), `include_levels`, `include_patterns`.
* [x] Sortie :

  * [x] `indicators` (valeurs clés), `levels` (top N), `patterns` (top M),
  * [x] `summary` (texte IA),
  * [x] `disclaimer` (pas de conseil), `limits`.

### `src/chart_mcp/services/analysis_llm.py`

* [x] **Phase alpha** : **stub** (règle heuristique) générant un **texte** structuré (concis, pédagogique, neutre) à partir des données (trend MA/EMA, RSI >70/<30, MACD cross, proximité niveau, présence pattern).
* [x] **Hook futur** : provider LLM réel (OpenAI/Anthropic) **en streaming** (chunk tokens).
* [x] **Filtrage** : **jamais** “acheter/vendre” ; utiliser tournures informatives.

### `src/chart_mcp/routes/analysis.py`

* [x] `POST /api/v1/analysis/summary`

  * [x] Orchestrer : fetch OHLCV -> compute indicateurs -> levels -> patterns -> summary stub.
  * [x] Réponse **non-stream** (JSON complet).

### `src/chart_mcp/schemas/streaming.py`

* [x] Types d’événements SSE :

  * [x] `tool_start`, `tool_end`, `tool_log`,
  * [x] `token` (texte IA chunk),
  * [x] `result_partial`, `result_final`,
  * [x] `metric`, `error`, `done`.
* [x] Structures NDJSON pour front.

### `src/chart_mcp/services/streaming.py`

* [x] Orchestration **streaming** : exécuter pipeline **par étapes** et émettre NDJSON via générateur (util. `utils.sse`).
* [x] Réguler fréquence d’emit pour ne pas saturer le client.

### `src/chart_mcp/routes/stream.py`

* [x] `GET /stream/analysis?symbol=&timeframe=&indicators=...`

  * [x] **SSE** : émettre `tool_*` lors des appels, envoyer `result_partial` (indicateurs, niveaux) puis `token` (texte IA), enfin `result_final` + `done`.
  * [x] Headers SSE adaptés (`text/event-stream`, `cache-control: no-cache`).
  * [x] Auth token.

### `src/chart_mcp/mcp_server.py`

* [x] **Déclarer tools MCP** qui **réutilisent** `services/*` (pas de duplication) :

  * [x] `get_crypto_data(symbol, timeframe, start, end)` -> DF OHLCV.
  * [x] `compute_indicator(symbol, timeframe, indicator, params)` -> séries.
  * [x] `identify_support_resistance(symbol, timeframe)` -> niveaux.
  * [x] `detect_chart_patterns(symbol, timeframe)` -> patterns.
  * [x] `generate_analysis_summary(symbol, timeframe, indicators, include_levels, include_patterns)` -> texte.
* [x] **Docstrings** clairs (pour discovery côté client).
* [x] *(Optionnel)* point d’entrée binaire `python -m chart_mcp.mcp_server`.

---

## 🧪 Tests (exigences détaillées)

### `tests/conftest.py`

* [x] **App de test** (FastAPI) + **client** http (httpx/AsyncClient).
* [x] Fixtures : **fake CCXT provider** (OHLCV déterministes), **fake analysis_llm** (stub).
* [x] **Env** : API token test, exchange = “stub”.

### Unitaires — `tests/unit/*`

* [x] **timeframes** : parsing + roundtrips + invalid.
* [x] **indicators** :

  * [x] MA/EMA : valeurs connues (séries courtes et longues, warmup).
  * [x] RSI : cas limites (flat, volatilité).
  * [x] MACD : structure colonnes (macd, signal, hist).
  * [x] Bollinger : bandes sup/inf cohérentes.
* [x] **levels** :

  * [x] pics correctement identifiés sur séries synthétiques ; regroupement en niveaux ; tri par “strength”.
* [x] **patterns** :

  * [x] jeux de données synthétiques pour double top/bottom, triangle, canal ; vérifier scores et bornes ts.
* [x] **providers** :

  * [x] ccxt_provider : normalisation colonnes, timezone, gestion erreurs (rate limit -> retry/backoff).
* [x] **analysis_llm (stub)** :

  * [x] texte sans injonction “acheter/vendre”, résume RSI/MA/levels/patterns, longueur max.

### Intégration — `tests/integration/*`

* [x] **market_routes** : 200/400/401, payload OHLCV, limites (max limit).
* [x] **indicators_routes** : calculs end-to-end (avec FAKE provider).
* [x] **levels/patterns_routes** : cohérence structures.
* [x] **analysis_routes** : orchestration complète (sans streaming).
* [x] **stream_sse** :

  * [x] ouverture de flux, réception d’une **séquence** minimale : `tool_start` -> `tool_end` -> `result_partial` -> `token` (≥1) -> `result_final` -> `done`.
  * [x] **heartbeat** reçu si latence (comment lignes).
  * [x] fermeture propre (client/server).

### Snapshots — `tests/snapshots/*`

* [x] **indicators_payload.json** : forme de sortie stable.
* [x] **analysis_summary.json** : gabarit de synthèse attendu (sans positions).

### Qualité

* [x] Lint : `ruff .` (aucune erreur).
* [x] Typage : `mypy src/` (0 error).
* [x] Format : `black`, `isort`.
* [x] Couverture : `pytest --cov=src --cov-report=xml` ≥ **80 %**.

---

## 🏗️ Build & Run (exigences)

* [x] **Make targets** (ou scripts npm/uv) :

  * [x] `make setup` (installer deps),
  * [x] `make dev` (uvicorn reload + .env),
  * [x] `make test`, `make lint`, `make typecheck`, `make format`,
  * [x] `make docker-build`, `make docker-run`.
* [x] **Startup** : app log au boot (routes, exchange, TFs supportées).
* [x] **Healthcheck** : conteneur sain en < 3s.
* [x] **Ressources** : limiter mémoire/CPU (pandas) ; batchiser calculs longs.
* [x] **Sécurité** : token obligatoire sur **toutes** les routes sauf `/health` ; CORS whitelist configurable.

---

## 🔐 Contrats d’API (extraits indispensables)

### `GET /api/v1/market/ohlcv`

```http
Authorization: Bearer <API_TOKEN>
```

Réponse (200):

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "source": "binance",
  "rows": [
    {"ts": 1730000000, "o": 35000.1, "h": 35200.0, "l": 34980.5, "c": 35110.0, "v": 123.45}
  ]
}
```

### `POST /api/v1/indicators/compute`

Body:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "indicator": "ema",
  "params": {"window": 50}
}
```

Réponse (200):

```json
{"series":[{"ts":1730000000,"value":35090.2}],"meta":{"indicator":"ema","window":50}}
```

### `GET /stream/analysis?...` (SSE, NDJSON par event `data:`)

```
event: tool_start
data: {"tool":"get_crypto_data","symbol":"BTCUSDT","timeframe":"1h"}
event: result_partial
data: {"indicators":{"ema50":35090.2,"rsi14":72.1}}
event: token
data: {"text":"Le prix évolue au-dessus de l’EMA 50..."}
event: result_final
data: {"summary":"...","levels":[...],"patterns":[...]}
event: done
data: {}
```

---

## 🧭 Rappels critiques pour l’agent

* **Alpha stricte** : crypto uniquement, **pas** de conseil en investissement.
* **Streaming** : privilégier **SSE** (compat front Vercel) pour **texte IA** et **logs d’outils**.
* **Extensibilité** : toutes les couches passent par **interfaces** (providers, services).
* **Robustesse** : gérer **rate limits**/erreurs exchange, NaN warmup indicateurs, timezones.
* **Lisibilité** : schémas `pydantic` pour **toutes** les entrées/sorties ; NDJSON **stable**.
* **Qualité** : 0 lint/type error, ≥ 80 % cov, CI verte, image Docker slim et saine.

---

Si tu suis cette checklist de bout en bout, on obtient une **alpha exploitable** : API sécurisée + SSE, **tools MCP** opérationnels, indicateurs/levels/patterns **fiables**, et une **synthèse IA** sobre. Elle sera prête à être branchée à un front `vercel/ai-chatbot` et servira de base solide pour l’extension multi-actifs ensuite.

[1]: https://github.com/AvacynLab/chart-mcp "AvacynLab/chart-mcp · GitHub"

---
Historique récent:
- 2025-10-23T22:44:47 : Initialisation complète de l'architecture, implémentation API/SSE/MCP, ajout des tests et CI, mise à jour documentation.
