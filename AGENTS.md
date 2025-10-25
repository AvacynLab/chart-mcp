2025-10-24T17:18:54Z — a5e5405a646939ee315086a8c6fc1b037b47e6c5

# 🎯 Brief à l’agent (résumé exécutif)

* Stabiliser l’alpha crypto-only : API sécurisée + SSE, tools MCP OK, indicateurs/levels/patterns fiables, synthèse IA **pédagogique** (jamais prescriptive).
* Corriger les points bloquants prod : **normalisation symboles CCXT**, **headers SSE**, **HEALTHCHECK Docker**, **.env.example**, **Makefile (tabs)**.
* Aligner MCP tools sur un **contrat JSON** (pas de `pandas.DataFrame` en retour).
* Renforcer tests : **normalisation symbole**, **SSE headers/heartbeat**, **MCP tools JSON**, (optionnel : rate-limit).
* CI/Qualité : 0 erreur lint/type, cov ≥ 80 %, image Docker slim et saine.

---

# ✅ Liste de tâches à cocher — fichier par fichier (avec sous-étapes)

## Racine / DX

* [x] `AGENTS.md` — **Écraser le contenu** et coller **cette** TODO-list (source de vérité unique).

  * [x] Supprimer l’historique/anciennes consignes.
  * [x] Ajouter en tête la date + le commit hash courant.

* [x] `README.md` — **Mettre à jour les exemples et limites**

  * [x] Exemples d’appels : accepter **`BTCUSDT` et `BTC/USDT`** ; ajouter une **note** : « le provider normalise vers `BASE/QUOTE` ».
  * [x] Ajouter un exemple complet `POST /api/v1/indicators/compute` (body + réponse).
  * [x] Ajouter un exemple `GET /api/v1/levels` et `GET /api/v1/patterns`.
  * [x] Documenter **SSE** : préciser **headers requis côté serveur** (`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`) et le format NDJSON (`event:`/`data:`).
  * [x] Rappeler **limitations alpha** (crypto uniquement, heuristique non prescriptive, patterns simples).

* [x] `CONTRIBUTING.md` — **Rendre exact** (il mentionne `.env.example`)

  * [x] Ajouter effectivement **`.env.example`** au repo (voir ci-dessous).

* [x] `Makefile` — **Corriger les recettes** (Make exige des **TABs**)

  * [x] Remplacer les espaces par des TABs devant chaque commande.
  * [x] Ajouter cibles :

    * [x] `format-check` → `black --check src tests && isort --check-only src tests`
    * [x] `lint-fix` → `ruff --fix . && black src tests && isort src tests`
    * [x] `typecheck-strict` → `mypy src`

* [x] `.env.example` — **Créer** (manquant)

  ```dotenv
  API_TOKEN=changeme_dev_token
  EXCHANGE=binance
  ALLOWED_ORIGINS=http://localhost:3000
  LLM_PROVIDER=stub
  LLM_MODEL=heuristic-v1
  STREAM_HEARTBEAT_MS=5000
  LOG_LEVEL=INFO
  # Optionnel (si rate-limit ajouté) :
  RATE_LIMIT_PER_MINUTE=60
  ```

## Docker / CI

* [x] `docker/Dockerfile` — **Corriger le HEALTHCHECK**

  * [x] Remplacer la ligne actuelle (invalide) par :

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
  * [x] Conserver user non-root + image slim.

* [x] `.github/workflows/ci.yml` — **Renforcer la qualité**

  * [x] Ajouter un step `format-check` (voir Makefile) en plus de `ruff`.
  * [x] Publier `coverage.xml` (déjà présent) ; s’assurer que l’addopts `--cov=src --cov-report=xml` est actif.
  * [x] (Optionnel) ajouter un job `hadolint` sur le Dockerfile.

## App FastAPI

* [x] `src/chart_mcp/routes/stream.py` — **Headers SSE + robustesse**

  * [x] Retourner la réponse SSE avec headers :

    ```python
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(iterator, media_type="text/event-stream", headers=headers)
    ```
  * [x] Intercepter `asyncio.CancelledError` pour fermer proprement le flux (stop du streamer).

* [x] `src/chart_mcp/app.py` — (Optionnel) **orjson** par défaut

  * [x] `FastAPI(default_response_class=ORJSONResponse, ...)` pour un JSON plus rapide.
  * [x] Vérifier que le middleware logs **n’écrit jamais** les headers d’auth.

## Provider & symboles

* [x] `src/chart_mcp/services/data_providers/ccxt_provider.py` — **Normalisation symbole**

  * [x] Implémenter :

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
  * [x] Appeler `normalize_symbol(symbol)` **avant** `client.fetch_ohlcv(...)`.
  * [x] Conserver `ccxt_timeframe(timeframe)` pour valider la TF.
  * [x] **Tests unitaires** :

    * [x] `BTCUSDT` → `BTC/USDT` ; `BTC/USDT` → `BTC/USDT` ; `FOOBAR` → `BadRequest`.

* [x] `src/chart_mcp/routes/market.py` (et autres routes) — **Uniformiser**

  * [x] *Option A* : laisser la normalisation **dans le provider** (préférable).
  * [ ] *Option B* : sinon, créer un util `normalize_symbol` dans `utils` et l’appeler en entrée de route.
  * [x] Mettre à jour la réponse `source` (id de l’exchange) comme c’est déjà fait.

## Services (SSE, indicateurs, niveaux, patterns, IA)

* [x] `src/chart_mcp/services/streaming.py` — **Événements `metric` + gestion erreurs**

  * [x] Mesurer le temps de chaque étape (data, indicateurs, levels, patterns, summary) et émettre :

    ```python
    await streamer.publish("metric", {"type": "metric", "payload": {"step": "indicators", "ms": elapsed}})
    ```
  * [x] En cas d’exception : émettre `error` puis `done`, puis `stop()` (ne pas laisser le client bloqué).
  * [ ] (Optionnel) throttler légèrement l’émission pour éviter de spammer le client.

* [x] `src/chart_mcp/services/levels.py` + `schemas/levels.py` + `routes/levels.py` — **Limiter la sortie**

  * [x] Ajouter un paramètre `max_levels: int = 10` (service), exposé en query (`?max=10`).
  * [x] Tronquer la liste au top-N par `strength`.
  * [x] **Tests** : vérifier tri + troncature.

* [x] `src/chart_mcp/services/patterns.py` — **Confidence un peu plus dynamique**

  * [x] Pour `channel`, faire varier `confidence` en fonction du RMSE entre prix et lignes, bornée `[0.3, 0.8]`.
  * [x] **Tests** : vérifier évolution de `confidence` quand l’ajustement s’améliore.

* [x] `src/chart_mcp/services/analysis_llm.py` — **Garde-fous texte**

  * [x] Limiter la longueur du `summary` (p.ex. ≤ 400 caractères) avec troncature propre.
  * [x] Ajouter un test : pas de mots *acheter/vendre/buy/sell* (déjà en partie couvert) et longueur ≤ 400.

## MCP tools

* [x] `src/chart_mcp/mcp_server.py` — **Contrat de sortie JSON**

  * [x] Actuellement `get_crypto_data` / `compute_indicator` **retournent des DataFrame**. MCP côté client attend du **JSON**.
  * [x] Adapter chaque tool pour **sérialiser** au format liste de dicts (ou `{columns, data}`) :

    ```python
    def get_crypto_data(...)-> list[dict]:
        frame = _provider.get_ohlcv(...)
        return frame.to_dict(orient="records")

    def compute_indicator(...)-> list[dict]:
        data = _indicator_service.compute(frame, indicator, params or {})
        cleaned = data.dropna()
        # aligner ts + valeurs
        ts = frame.loc[cleaned.index, "ts"].astype(int).tolist()
        recs = cleaned.to_dict(orient="records")
        return [{"ts": int(t), **{k: float(v) for k, v in r.items()}} for t, r in zip(ts, recs, strict=True)]
    ```
  * [x] `identify_support_resistance` / `detect_chart_patterns` sont déjà JSON-like — valider qu’aucun objet non sérialisable ne fuite (tuples → listes).
  * [x] **Tests** : ajouter `tests/unit/mcp/test_tools.py` couvrant les 4 tools (structure JSON, types numériques, champs requis).

## Schémas & types

* [x] `src/chart_mcp/schemas/streaming.py` — **Type fort plutôt que regex**

  * [x] Remplacer :

    ```python
    from typing import Literal
    EventType = Literal["tool_start","tool_end","tool_log","token","result_partial","result_final","metric","error","done"]

    class StreamEvent(BaseModel):
        type: EventType
        payload: Dict[str, Any] = Field(default_factory=dict)
    ```
  * [x] Adapter les tests si tu en ajoutes sur ce schéma.

---

# 🧪 Tests à ajouter/mettre à jour

* [x] **Normalisation symbole** — `tests/unit/services/test_symbol_normalization.py`

  * [x] `BTCUSDT` → `BTC/USDT` ; `BTC/USDT` inchangé ; `FOOBAR` → `BadRequest`.

* [x] **MCP tools (JSON)** — `tests/unit/mcp/test_tools.py`

  * [x] `get_crypto_data` → liste de dicts (`ts,o,h,l,c,v`).
  * [x] `compute_indicator` (EMA/RSI) → liste `{ts, ...}`.
  * [x] `identify_support_resistance` → champs `price,kind,strength,ts_range`.
  * [x] `detect_chart_patterns` → champs `name,score,confidence,start_ts,end_ts,points`.

* [x] **SSE** — `tests/integration/test_stream_headers.py`

  * [x] `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
  * [x] Au moins 1 `event: token` **ou** `event: result_partial`.
  * [x] Heartbeat présent (si délai suffisant) ou mock du heartbeat.

* [x] **Levels (max)** — `tests/integration/test_levels_routes.py` (étendre)

  * [x] `?max=5` → 5 niveaux max, triés par `strength` décroissant.

* [x] **Analysis stub** — `tests/unit/services/test_analysis_llm_stub.py` (étendre)

  * [x] Longueur ≤ 400 caractères.

*(Optionnel)*

* [x] **Rate-limit middleware** (si tu l’ajoutes) — `tests/integration/test_ratelimit.py`

  * [x] Dépassement → `429` + header `X-RateLimit-Remaining`.

---

# 🏗️ Build & qualité — rappels fermes

* **Linters/Formatters** : `ruff`, `black`, `isort` **sans erreur**.
* **Typing** : `mypy src/` **strict** (0 erreur).
* **Tests** : `pytest --cov=src --cov-report=xml` → **≥ 80 %** de couverture.
* **Docker** : image slim, user non-root, **HEALTHCHECK fixé**, port 8000, `CMD uvicorn`.
* **Sécu** : toutes les routes sauf `/health` exigent `Authorization: Bearer <token>`.
* **SSE** : headers ajoutés + heartbeat régulier (paramétrable via env).
* **Neutralité** : **aucun** langage prescriptif (« acheter/vendre »).

---

## 📎 Extraits prêts-à-coller (patchs clés)

**SSE (route)**

```python
# src/chart_mcp/routes/stream.py
headers = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
return StreamingResponse(iterator, media_type="text/event-stream", headers=headers)
```

**Normalisation symbole (provider)**

```python
# src/chart_mcp/services/data_providers/ccxt_provider.py
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

# dans get_ohlcv(...):
symbol = normalize_symbol(symbol)
raw = self.client.fetch_ohlcv(symbol, timeframe_value, since=since, limit=limit, params=params)
```

**MCP tools → JSON**

```python
# src/chart_mcp/mcp_server.py
def get_crypto_data(...)-> list[dict]:
    frame = _provider.get_ohlcv(...)
    return frame.to_dict(orient="records")

def compute_indicator(...)-> list[dict]:
    frame = get_crypto_data(symbol, timeframe, limit=limit or 500)
    data = _indicator_service.compute(pd.DataFrame(frame), indicator, params or {})
    cleaned = data.dropna()
    ts = pd.Series([r["ts"] for r in frame]).loc[cleaned.index].astype(int).tolist()
    recs = cleaned.to_dict(orient="records")
    return [{"ts": int(t), **{k: float(v) for k, v in r.items()}} for t, r in zip(ts, recs, strict=True)]
```

**Docker HEALTHCHECK**

```dockerfile
# docker/Dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  python - <<'PY' || exit 1
import sys, http.client
try:
    c = http.client.HTTPConnection("localhost", 8000", timeout=3)
    c.request("GET", "/health")
    r = c.getresponse()
    sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
```

**Makefile (extrait)**

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
```

---

si tu appliques ces items, on verrouille une alpha robuste : symboles normalisés, SSE **propre**, HEALTHCHECK fonctionnel, MCP **JSON-compliant**, tests pertinents & CI verte. Ensuite seulement, on pourra attaquer les tâches “nice-to-have” (rate-limit global, orjson par défaut, metrics plus riches, etc.).

---
Historique récent:
- 2025-10-24T17:18:54Z : Reset AGENTS.md avec la checklist crypto-only (normalisation, SSE, MCP JSON, Docker/CI) et démarrage de l'implémentation.
- 2025-10-24T17:45:00Z : Normalisation CCXT end-to-end (routes + MCP), SSE headers/metrics, HEALTHCHECK Docker, Makefile/CI durcis et ajout des tests symboles/MCP/SSE/levels/LLM.
- 2025-10-24T18:25:00Z : Activé ORJSON par défaut sur FastAPI, revu la checklist (docs/tests/CI) et confirmé la non-exposition des headers sensibles ; suite pytest complète passée.
- 2025-10-24T19:05:00Z : Ajout du job hadolint dans la CI, vérification des cibles Makefile cochées et exécution de `pytest --cov=src --cov-report=xml` pour valider la pipeline.
- 2025-10-24T19:45:00Z : Durci le middleware de rate-limit avec l’entête `X-RateLimit-Remaining` et ajouté le test d’intégration `test_ratelimit.py` (quota 429).
- 2025-10-24T21:20:49Z : Pinned `build-essential` et `pip` dans le Dockerfile (avec cache pip désactivé) pour satisfaire hadolint et stabiliser les builds.
