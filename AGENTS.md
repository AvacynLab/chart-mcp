2025-10-26T02:36:54+00:00 — 3e12e74009e3280e9f4d9f9742028116895ff222

# 🎯 Brief (objectif alpha)

* **Périmètre** : crypto-only, API FastAPI sécurisée + **SSE** stable, tools **MCP** exposés via serveur réel (stdio), indicateurs (MA/EMA/RSI/MACD/BB), niveaux S/R, patterns (double top/bottom, triangle, canal), résumé IA **pédagogique** (jamais prescriptif).
* **État** : services d’analyse OK dans l’ensemble ; **beaucoup de “…”** subsistent (schemas, 2–3 routes, provider CCXT – ok mais à valider, entrypoints MCP/stream OK mais **schéma streaming vide**, front & tests TS contiennent des `...`).
* **Cible** :

  1. **Supprimer tous les `...`** (implémentations réelles),
  2. **Compléter les schémas Pydantic** (notamment `schemas/streaming.py`),
  3. Finaliser **routes** `levels.py`, `patterns.py`, `stream.py`,
  4. Vérifier/compléter **provider CCXT** & normalisation symbole,
  5. Aligner **tests Python** (déjà présents) + **tests TS** (remplir placeholders),
  6. Conserver headers SSE, metrics, neutralité “non-conseil”.

---

# ✅ To-do à cocher — fichier par fichier (avec sous-étapes)

## 0) Remplacement de la source de vérité

* [x] **`AGENTS.md`** — **Écraser** et coller **exclusivement** la présente liste (avec date + commit hash).

---

## 1) Schémas Pydantic (nombreux `...`)

### `src/chart_mcp/schemas/streaming.py` — **À écrire entièrement**

* [x] Créer un **union discriminé** par `type` avec `Literal[...]`.
* [x] Modèles :

  * [x] `ToolEventDetails`: `tool: str`, `name: str | None`, `latest: dict[str, float] | None`.
  * [x] `ToolStreamPayload`: `type="tool"`, `payload: ToolEventDetails`.
  * [x] `TokenPayload`: `text: str` (`min_length=1`).
  * [x] `TokenStreamPayload`: `type="token"`, `payload: TokenPayload`.
  * [x] `LevelPreview`: `kind: str`, `strength: float >=0`.
  * [x] `ResultPartialDetails`: `levels: list[LevelPreview] = []`, `progress: float | None`.
  * [x] `ResultPartialStreamPayload`: `type="result_partial"`, `payload: ResultPartialDetails`.
  * [x] `LevelDetail(LevelPreview)` + `PatternDetail`: `name, score, start_ts, end_ts, points: list[tuple[int,float]]`, `confidence: float`.
  * [x] `ResultFinalDetails`: `summary: str (min_length=1)`, `levels: list[LevelDetail]`, `patterns: list[PatternDetail]`.
  * [x] `ResultFinalStreamPayload`: `type="result_final"`, `payload: ResultFinalDetails`.
  * [x] `MetricDetails`: `step: str (min_length=1)`, `ms: float >=0`.
  * [x] `MetricStreamPayload`: `type="metric"`, `payload: MetricDetails`.
  * [x] `ErrorDetails`: `code: str`, `message: str`.
  * [x] `ErrorStreamPayload`: `type="error"`, `payload: ErrorDetails`.
  * [x] `DoneDetails`: `ok: bool = True`.
  * [x] `DoneStreamPayload`: `type="done"`, `payload: DoneDetails | dict = Field(default_factory=dict)`.
* [x] `EventType = Literal["tool","token","result_partial","result_final","metric","error","done"]`.
* [x] `StreamPayload = Union[ToolStreamPayload,TokenStreamPayload,ResultPartialStreamPayload,ResultFinalStreamPayload,MetricStreamPayload,ErrorStreamPayload,DoneStreamPayload]`.
* [x] `StreamEvent` avec `type: EventType` + `payload: dict | model`; expose `__all__` (déjà listé).
* [x] Satisfaire `tests/unit/schemas/test_streaming.py` (obligatoire : token vide → ValidationError, summary vide → ValidationError).

### `src/chart_mcp/schemas/market.py`, `indicators.py`, `levels.py`, `patterns.py`, `common.py`, `finance.py`, `backtest.py`

* [x] **Remplacer tous les `...`** et garantir :

  * [x] **`market.py`** : Request/Response avec `symbol` uppercased, timeframe validée (via util), OHLCV `[{"ts","o","h","l","c","v"}]`.
  * [x] **`indicators.py`** : `indicator` ∈ {"ma","ema","rsi","macd","bbands"}, `params` optionnels, réponse `[{ts,...}]`.
  * [x] **`levels.py`** : `Level(kind:str, price:float, strength:float, ts_range[start_ts,end_ts])`; `LevelsResponse(levels:list[Level])`.
  * [x] **`patterns.py`** : `Pattern(name, score, start_ts, end_ts, points:list[PatternPoint], confidence)`.
  * [x] **`finance.py`/`backtest.py`** : compléter champs (CAGR, Sharpe, profit_factor, trades, equity_curve…), **types numériques** (float|int), `model_config = {"populate_by_name": True}` partout.
  * [x] **`common.py`** : helpers/aliases partagés, types “SymbolNormalized” si utilisé.

---

## 2) Routes FastAPI (incomplètes)

### `src/chart_mcp/routes/levels.py`

* [x] Compléter `router = APIRouter(tags=["levels"], prefix="/api/v1/levels", dependencies=[Depends(require_token), Depends(require_regular_user)])`.
* [x] Paramètres : `symbol: str`, `timeframe: str`, `limit: int=Query(500,ge=1,le=5000)`, `max: int=Query(10,ge=1,le=100)`.
* [x] Implémenter corps (déjà presque fait) : `parse_timeframe`, `provider.get_ohlcv`, `service.detect_levels(..., max_levels=max)`, mapping → `LevelsResponse`.
* [x] **Retourner `symbol` normalisé** (via `normalize_symbol`).
* [x] Aligner sur `tests/integration/test_levels_routes.py` (tri par `strength` décroissant, troncature `max`).

### `src/chart_mcp/routes/patterns.py`

* [x] Compléter `router = APIRouter(tags=["patterns"], prefix="/api/v1/patterns", dependencies=[Depends(require_token), Depends(require_regular_user)])`.
* [x] Paramètres : `symbol, timeframe, limit`.
* [x] Implémenter mapping `PatternResult` → `PatternsResponse` (déjà amorcé).
* [x] Normaliser `symbol` à la sortie.

### `src/chart_mcp/routes/stream.py`

* [x] Compléter la signature (paramètres manquants) :

  * [x] `limit: int = Query(500, ge=1, le=5000)`
  * [x] `include_levels: bool = Query(True)`, `include_patterns: bool = Query(True)`
  * [x] `streaming: bool = Query(True)` (si utilisé par le service)
  * [x] `request: Request` et dépendances `Depends(require_token)`, `Depends(require_regular_user)`.
* [x] Construire `indicator_specs` à partir de `indicators` (`"ema:21,rsi:14"` → liste).
* [x] Appeler `get_streaming_service(request).stream_analysis(...)`.
* [x] **Garder les en-têtes SSE** (déjà posés en bas) :
  `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
* [x] Gérer `asyncio.CancelledError` avec fermeture propre (le _guard est là, valider qu’il s’exécute).

---

## 3) Provider & normalisation

### `src/chart_mcp/services/data_providers/ccxt_provider.py`

* [x] **Vérifier la `Protocol` `_ExchangeLike`** (les `...` dans signatures sont **OK** en PEP544).
* [x] **`normalize_symbol` est présent** : valider quotes = `("USDT","USD","USDC","BTC","ETH","EUR","GBP")`, uppercasing, slash, `BadRequest` sinon.
* [x] `get_ohlcv` : mapping `ccxt_timeframe(timeframe)`, retries 429/ratelimit, DataFrame colonnes `["ts","o","h","l","c","v"]`, timestamp **en secondes**, tri croissant, filtrage `end` si fourni.
* [x] Satisfaire :

  * `tests/unit/services/test_ccxt_provider.py`
  * `tests/unit/services/test_symbol_normalization.py`.

---

## 4) MCP

### `src/chart_mcp/mcp_main.py`

* [x] **Déjà OK** : `REGISTERED_TOOL_NAMES`, `register()`, `build_server()`, `main()` stdio. **Ne rien casser.**

### `src/chart_mcp/mcp_server.py`

* [x] **Confirmer** que toutes les fonctions **renvoient du JSON pur** (list/dict) — **pas** de DataFrame.
* [x] Vérifier que les caches (`_provider`, `_indicator_service`, …) sont **tous** définis (pas de `...` résiduel au milieu du fichier).
* [x] `register_tools(registrar)` **expose** :
  `get_crypto_data`, `compute_indicator`, `identify_support_resistance`, `detect_chart_patterns`, `generate_analysis_summary`.
* [x] Satisfaire `tests/unit/mcp/test_tools.py` et `tests/unit/mcp/test_server_runtime.py`.

---

## 5) Application / Config / SSE / Logs

### `src/chart_mcp/app.py`

* [x] **Relire la factory** : CORS depuis `settings.allowed_origins`, GZip, middlewares logs (jamais logguer `Authorization`).
* [x] Monter **toutes** les routes : `health`, `market`, `finance` (feature-flag), `indicators`, `levels`, `patterns`, `analysis`, `stream`.
* [x] Gestion erreurs : `ApiError`, `HTTPException`, `RequestValidationError`, catch-all.
* [x] `StreamingService` instancié dans `app.state` (déjà le cas).
* [x] (Facultatif) `ORJSONResponse` par défaut.

### `src/chart_mcp/config.py`

* [x] **Enlever tout `...`** résiduel.
* [x] Champs : `api_token`, `exchange`, `allowed_origins` (split str→list), `llm_provider`, `llm_model`, `stream_heartbeat_ms`, `log_level`, `rate_limit_per_minute`, `feature_finance` (bool, desc claire), `playwright_mode` (bool pour e2e).
* [x] Fournir un **proxy `settings`** monkeypatchable (déjà présent ; terminer méthodes si tronquées).
* [x] Valider avec tests d’intégration (e.g. finance feature flag).

---

## 6) Services (vérifs rapides)

### `src/chart_mcp/services/streaming.py`

* [x] **Déjà OK** : émission `metric` (on voit 9 occurrences). Garde : `error` → `done` sur exception, `heartbeat` via `utils.sse`.
* [x] Les `token` ne doivent pas être vides (le schéma le fera respecter).

### `src/chart_mcp/services/indicators.py`, `levels.py`, `patterns.py`, `analysis_llm.py`

* [x] **Conserver** les implémentations ; valider les paramètres/retours contre les schémas finalisés.
* [x] `analysis_llm` : long. ≤ 400, jamais “acheter/vendre/buy/sell”.

---

## 7) Frontend (TS/TSX) — **placer le minimum viable et supprimer les `...`**

**NB :** plusieurs fichiers front contiennent des `...` qui cassent la compilation/tests. Mets-les en état “alpha minimal”.

### Composants

* [x] `components/chat.tsx` — **remplacer les `...`** :

  * [x] Contexte `ChatStore` avec `sendMessage`, `isStreaming`.
  * [x] Formulaire : onSubmit → appel `/stream/analysis` en SSE ; **ajouter** un stub simple côté client (pas besoin de MCP pour les tests unitaires).
  * [x] Gestion état : `messages`, `artifacts` (passe à `<Messages />`).
* [x] `components/messages.tsx` — **remplacer les `...`** :

  * [x] Rendre messages/artefacts ; pour artefacts inconnus, **fallback** `<div data-testid="artifact-fallback">`.
  * [x] Couvrir les artefacts finance (chart/news/backtest) comme dans les tests existants (ils vérifient le fallback, les toggles d’overlay, etc.).
* [x] `components/finance/backtest-report-artifact.tsx` & `.test.tsx`, `components/finance/finance-chart-artifact.test.tsx` — **enlever les `...`** et s’aligner avec les types déjà importés.

### Harness e2e (Playwright)

* [x] `tests/e2e/harness.tsx`, `tests/e2e/finance-fixtures.ts`, `tests/pages/chat.ts` — **remplacer les `...`** :

  * [x] Rendre un `<FinanceChatHarness />` minimal avec `<Chat />`.
  * [x] Stubs d’API fetch pour e2e (si besoin) ou marquer **skipped** les tests e2e non essentiels en alpha (préférer rendre le harness fonctionnel).

### Config tests

* [x] `playwright.config.ts` — **enlever `...`** et conserver config standard.
* [x] `vitest.config.ts` / `vitest.setup.ts` : laisser tel quel si déjà ok.

---

## 8) Tests Python — cohérence finale

* [x] **Corriger tout `...`** présent **même dans les tests** (`tests/unit/mcp/test_server_runtime.py`, `tests/unit/services/test_streaming_service.py`, etc.). Remplis les petites classes Dummy où le `...` coupe la méthode.
* [x] **SSE headers** : `tests/integration/test_stream_headers.py` existe — il s’attend à `no-cache`, `keep-alive`, `X-Accel-Buffering: no`, au moins un `event: token`/`result_partial` et un `event: metric` + `: ping`.
* [x] **Levels/Patterns routes** : s’assurer que les deux tests d’intégration passent (symbol normalisé → `BTC/USDT`, tri/`max`).
* [x] **MCP** : `tests/unit/mcp/test_tools.py` & `test_server_runtime.py` doivent passer (outil JSON, noms exposés via `REGISTERED_TOOL_NAMES`).
* [x] **Feature flag finance** : `tests/integration/test_finance_feature_flag.py` OK (enabled/disabled).

---

## 9) Build / CI / Docker

* [x] **`.github/workflows/ci.yml`** — garder : `ruff`, `black/isort --check`, `mypy`, `pytest --cov=src --cov-report=xml`, build Docker.
* [x] **Dockerfile** — **healthcheck** fonctionnel (la version Python inline OK) ; image slim, user non-root.
* [x] **`.env.example`** — déjà présent (vérifier variables : `API_TOKEN`, `EXCHANGE`, `ALLOWED_ORIGINS`, `LLM_PROVIDER`, `LLM_MODEL`, `STREAM_HEARTBEAT_MS`, `LOG_LEVEL`, `RATE_LIMIT_PER_MINUTE`).
* [x] **Makefile** — recettes avec **TABs** ; cibles `format-check`, `lint-fix`, `typecheck-strict`, `mcp-run`.

---

## 10) Améliorations continues

* [x] Ajouter un ratio de progression dans les événements `result_partial` du streaming SSE et couvrir le comportement par des tests unitaires.
* [x] Structurer le détail des étapes de pipeline dans les événements `result_partial` (statuts `pending/in_progress/completed/skipped`) et documenter les cas sautés.
* [x] Exposer un champ `progress` sur chaque étape du pipeline pour refléter l'avancement fractionnaire et couvrir la validation côté schémas/tests de service.
* [x] Centraliser la liste des indicateurs supportés et renforcer le parsing SSE/REST (`_parse_indicator_spec`) avec trimming et messages d'erreur dédiés.
* [x] Normaliser le symbole dans la route d'analyse avant d'interroger le provider et couvrir le comportement par un test d'intégration.
* [x] Dédupliquer les indicateurs fournis à la route SSE avant d'appeler le service et vérifier l'ordre via un test d'intégration.
* [x] Respecter le paramètre `max` de la route SSE afin de borner les niveaux renvoyés (payload partiel et final) et couvrir le comportement par des tests d'intégration/unitaires.

---

# 📌 Patches / snippets utiles (rappel)

**SSE headers (route)**

```python
headers = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
return StreamingResponse(iterator, media_type="text/event-stream", headers=headers)
```

**Normalisation symbole (si besoin de corriger)**

```python
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

**MCP (entrypoint déjà OK — ne rien casser)**

```python
# mcp_main.py
REGISTERED_TOOL_NAMES = (
    "get_crypto_data","compute_indicator",
    "identify_support_resistance","detect_chart_patterns",
    "generate_analysis_summary",
)
```

---

# 🧪 Exigences tests & build (à respecter strictement)

* **Python** : `ruff`, `black`, `isort` propres ; `mypy src` **0 erreur**.
* **Coverage** : `pytest --cov=src --cov-report=xml` **≥ 80%**.
* **Routes** : toutes sauf `/health` protégées par `Authorization: Bearer`.
* **SSE** : headers requis + heartbeat régulier ; évènements `metric` émis.
* **Neutralité** : aucun langage prescriptif (“acheter/vendre/buy/sell”).
* **Docker** : image slim, non-root, healthcheck **OK**.

---

👉 **Action immédiate** :

1. **Remplace `AGENTS.md`** par cette liste.
2. **Supprime tous les `...`** dans les fichiers listés et implémente les parties manquantes (schémas, 3 routes, tests TS & Python).
3. Lance la CI locale : `make format-check && make typecheck-strict && pytest -q`.
4. Corrige jusqu’au **tout-vert**.

Ensuite on pourra ouvrir le scope (autres assets) sans refactor massif.

# Historique

- 2025-10-26T02:36:54+00:00 — Agent gpt-5-codex : remplacement complet d'`AGENTS.md` par la nouvelle checklist fournie.
- 2025-10-26T02:52:17+00:00 — Agent gpt-5-codex : refonte des schémas Pydantic (streaming, market, indicators, levels, patterns, finance, backtest, common), finalisation des routes levels/patterns/stream avec parsing indicateurs SSE et options, ajustements du service de streaming (flags include*, validation done), mise à jour des tests associés, puis exécution de `make format-check`, `make typecheck-strict`, `pytest -q`.
- 2025-10-26T03:04:04+00:00 — Agent gpt-5-codex : contrôle complet du provider CCXT et de la normalisation symbole, vérification des caches MCP et du retour JSON, revue de la factory FastAPI/config, audit des composants front/harness e2e, exécution ciblée des tests (`pytest tests/unit/services/test_ccxt_provider.py tests/unit/services/test_symbol_normalization.py`, `pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_server_runtime.py`, `pytest tests/integration/test_finance_feature_flag.py`, `pytest tests/integration/test_levels_routes.py tests/integration/test_patterns_routes.py tests/integration/test_stream_headers.py`), puis mise à jour de la checklist.
- 2025-10-26T03:12:14+00:00 — Agent gpt-5-codex : vérification de l'absence de placeholders `...`, exécution de `pnpm vitest run`, `make format-check`, `make typecheck-strict`, `pytest -q`, puis validation finale de la checklist (section schémas et config Vitest).
- 2025-10-26T03:17:14+00:00 — Agent gpt-5-codex : ajout du suivi de progression côté `StreamingService` pour enrichir `result_partial`, création du test unitaire dédié, exécution de `make format-check`, `make typecheck-strict`, `pytest -q`, `pnpm vitest run`, mise à jour de la checklist.
- 2025-10-26T03:28:00+00:00 — Agent gpt-5-codex : ajout des statuts détaillés des étapes de pipeline dans les événements `result_partial`, recalcul du ratio via pondération par étape, nouvelles validations Pydantic et tests (unitaires schéma + service) couvrant les cas sautés.
- 2025-10-26T03:46:07+00:00 — Agent gpt-5-codex : ajout du champ de progression par étape (`steps[].progress`), ajustement du calcul du ratio global pondéré, mise à jour de la boucle indicateurs pour refléter l'avancement incrémental et nouveaux tests Pydantic/service.
- 2025-10-26T04:02:00+00:00 — Agent gpt-5-codex : factorisation de la constante `SUPPORTED_INDICATORS`, validation renforcée du parsing SSE (trim, lower-case, messages explicites) et ajout de tests unitaires dédiés à `_parse_indicator_spec`.
- 2025-10-26T04:17:00+00:00 — Agent gpt-5-codex : normalisation du symbole côté `/analysis/summary`, ajout du test d'intégration associé, déduplication des indicateurs dans `/stream/analysis` avec garde d'ordre et couverture intégration.
- 2025-10-26T04:28:00+00:00 — Agent gpt-5-codex : ajout du paramètre `max` côté SSE, validation `max_levels` dans le service de streaming, couverture unitaire/integration sur la troncature des niveaux.
- 2025-10-26T04:44:00+00:00 — Agent gpt-5-codex : correction des avertissements `ruff` (imports en tête de module, formatage des docstrings), exécution de `ruff check .` pour confirmer le linting.
