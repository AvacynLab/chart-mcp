Remet à zero le fichier AGENTS.md et importe la liste des taches fournit ci dessous ainsi que les informations (au mot près) dans le fichier. Une fois effectué, commence l’implementation, et prend ton temps. 

----------
Parfait. Voici une **liste de tâches exhaustive à cocher** (avec sous-étapes) **à destination de l’agent IA**. Elle consolide : (1) le cahier des charges PDF, (2) l’état actuel du code, (3) nos audits précédents. Chaque point précise **quoi corriger/ajouter/supprimer/modifier**, **où (fichier par fichier)**, et **ce qu’il faut savoir pour les tests & le build**.

> Références d’exigences issues du cahier des charges (MCP, CCXT, SSE, indicateurs, figures chartistes, front Next.js, etc.).     

---

# 🎯 Brief (objectifs & consignes)

**À toi, l’agent :**
Ton objectif est d’aligner parfaitement l’alpha sur le cahier des charges crypto/MCP. Tu dois :

* **Exposer proprement les outils MCP** (données, indicateurs, S/R, figures, résumés pédagogiques). 
* **Fournir un flux temps réel** par **SSE** (événements d’étapes + texte IA tokenisé). 
* **Calculer les indicateurs classiques** (SMA/EMA/RSI/MACD/Bollinger…) et **détecter les niveaux S/R** (pics + regroupement). 
* **Détecter les figures chartistes clés** (incluant **tête-épaules** explicitement). 
* **Brancher un front minimal Next.js** consommant SSE + charting (Lightweight Charts). 
* **Prévoir et intégrer une instance SearxNG autohébergée** (recherche actus/docu crypto locale et privée) et l’exposer proprement côté back.
* **Fiabiliser build & déploiement Docker Compose**, configurer CORS, secrets, healthcheck.
* **Couvrir par des tests** (unitaires, intégration API, e2e SSE), plus **CI** (lint/typecheck/tests/build).

**Règles tests & build à respecter** (global) :

* Tests Python via **pytest** ; types via **mypy** ; lint via **ruff**.
* Front tests via **Vitest**/**Playwright** si présent.
* **CI** : pipeline unique (lint → typecheck → tests → build images Docker → artefacts).
* **Build Docker** : images reproductibles, **HEALTHCHECK** qui tape `/health`, variables `.env` **non commitées**.
* **SSE** : vérifier **heartbeats**, **annulation client**, **ordre des événements** et **buffering off** (headers). 

---

# ✅ Backlog détaillé (à cocher), avec sous-étapes et fichiers

## 1) MCP : outils & contrat I/O

* [x] **Vérifier/normaliser les outils MCP exposés**
  **Fichiers :** `src/chart_mcp/mcp_main.py`, `src/chart_mcp/mcp_server.py`

  * [x] S’assurer que les tools suivants existent et valident leurs schémas :

    * [x] `get_crypto_data(symbol, timeframe, limit)` → OHLCV normalisé
    * [x] `compute_indicator(symbol, timeframe, name, params)` → séries indicateurs
    * [x] `identify_support_resistance(symbol, timeframe, params)` → niveaux + score
    * [x] `detect_chart_patterns(symbol, timeframe, params)` → liste patterns (incl. **tête-épaules**)
    * [x] `generate_analysis_summary(payload)` → texte pédagogique
  * [x] **Valider les types MCP** (entrées/sorties) : pydantic `schemas/*` cohérents et documentés.
  * [x] **Tests** : `tests/mcp/test_tools_contract.py` (mocks fournisseurs & snapshots de payload).

  > Le cahier exige l’exposition d’outils côté serveur MCP pour data + TA. 

* [x] **Documenter l’usage MCP (README)**
  **Fichier :** `README.md`

  * [x] Section “Server MCP (stdio)”, commande d’exécution, exemples d’appels, liste des tools.
  * [x] Lien vers spec MCP & FastMCP (réf).

---

## 2) Acquisition données (CCXT) & timeframes

* [x] **Provider CCXT : robustesse & normalisation symbole**
  **Fichiers :** `src/chart_mcp/services/data_providers/ccxt_provider.py`, `src/chart_mcp/utils/timeframes.py`

  * [x] Mapper strict `timeframe` (1m/5m/1h/1d…) → formats CCXT ; lever `422` si invalide. 
  * [x] Normaliser `symbol` (e.g., `BTC/USDT`) ; gestion exchange configurable (`EXCHANGE`).
  * [x] **Tests** : `tests/providers/test_ccxt_provider.py` (table de timeframes + erreurs réseau/ratelimit).
  * [x] Optionnel : **cache OHLC** (mémoire/SQLite/Mongo) avec TTL. (Optimisation recommandée)

---

## 3) Indicateurs techniques

* [x] **Implémentations SMA / EMA / RSI / MACD / Bollinger** (pandas/ta-lib/ta)
  **Fichier :** `src/chart_mcp/services/indicators.py`

  * [x] Paramètres par défaut documentés (ex : périodes EMA 12/26, RSI 14…).
  * [x] Retour unifié : colonnes nommées (`ema_12`, `ema_26`, `macd`, `macd_signal`, `bb_upper`, `bb_lower`, etc.).
  * [x] **Tests** : `tests/indicators/test_indicators_values.py` (golden values sur séries connues + cas bords).

---

## 4) Supports/Résistances (pics SciPy + regroupement)

* [x] **Détection S/R via pics**
  **Fichier :** `src/chart_mcp/services/levels.py`

  * [x] `scipy.signal.find_peaks` -> extraire **maxima/minima** ; **clusteriser** niveaux proches ; scorer “fort” vs “général”.
  * [x] Paramètres exposés (`distance`, `prominence`, `merge_threshold`).
  * [x] **Tests** : `tests/levels/test_levels_detection.py` (séries synthétiques + cas bruités).

---

## 5) Figures chartistes (incl. **tête-épaules**)

* [x] **Ajouter la figure “Head & Shoulders”**
  **Fichier :** `src/chart_mcp/services/patterns.py`

  * [x] Heuristique : trois sommets, épaule G ≈ épaule D, tête plus haute, “neckline” détectée, tolérances %.
  * [x] Déjà couverts : doubles sommets/fonds, triangles, chandeliers (marteau/étoile/engulfing).
  * [x] **Sortie** : `type`, `confidence`, `indices` (iL, iHead, iR, iNeckline1, iNeckline2), `direction` (bearish/bullish).
  * [x] **Tests** : `tests/patterns/test_head_shoulders.py` (séries synthétiques + faux positifs).

  > Le cahier cite explicitement “tête-épaules” comme motif attendu. 

---

## 6) API FastAPI : routes & sécurité

* [x] **Routes marché/TA/stream**
  **Fichiers :** `src/chart_mcp/app.py`, `src/chart_mcp/routes/market.py`, `routes/indicators.py`, `routes/levels.py`, `routes/patterns.py`, `routes/analysis.py`, `routes/stream.py`, `routes/auth.py`

  * [x] **Auth** : header `Authorization: Bearer <API_TOKEN>` requis ; **403** si absent/invalid.
  * [x] **Rôle** : `X-Session-User: regular` exigé si applicable (garde).
  * [x] **OpenAPI** : tags/summary/params ; exemples `curl`/`httpie` dans `README.md`.
  * [x] **Tests** : `tests/api/test_auth.py`, `tests/api/test_routes_ok_ko.py`.

* [x] **CORS**
  **Fichier :** `src/chart_mcp/app.py`, `.env`

  * [x] Renseigner `ALLOWED_ORIGINS` (ex : `http://localhost:3000` pour Next).
  * [x] **Tests** : `tests/api/test_cors.py` (prévol CORS, headers).

---

## 7) SSE : pipeline d’événements + **streaming tokenisé du texte IA**

* [x] **Événements SSE**
  **Fichiers :** `src/chart_mcp/routes/stream.py`, `src/chart_mcp/services/streaming.py`, `src/chart_mcp/utils/sse.py`, `src/chart_mcp/schemas/streaming.py`

  * [x] Émettre : `heartbeat`, `step:start`/`step:end` (ohlcv, indicators, levels, patterns), `token` (texte IA **token par token**), `result_partial`, `done`.
  * [x] Headers : `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`, **désactiver buffering** côté proxy.
  * [x] Annulation client : respecter `request.is_disconnected()` ; couper proprement.
  * [x] **Tests intégration** : `tests/stream/test_sse_flow.py` (client SSE → ordre d’événements, timeouts, annulation).

* [x] **Service de résumé IA**
  **Fichier :** `src/chart_mcp/services/analysis_llm.py`

  * [x] Exposer un mode **génération tokenisée** (simulateur si pas d’API IA) -> “flush” par `yield`.
  * [x] **Tests** : `tests/analysis/test_streaming_text.py` (reconstruction du texte, flux partiel).

---

## 8) Front minimal **Next.js** + **Lightweight Charts** (recommandé par le cahier)

* [x] **Créer un front Next.js (apps dir)**
  **Dossier :** `frontend/` (nouveau)

  * [x] Page `/chart` avec formulaire (symbol, timeframe, indicateurs), chart **Lightweight Charts** et **EventSource** sur `/stream/analysis`.
  * [x] Rendu progressif : appliquer les overlays (EMA/RSI/MACD/BB) au fil des `step:end`.
  * [x] Tokenisation texte IA : afficher flux `token` en direct (zone d’analyse).
  * [x] **Tests** : `components/chart/chart-analysis.test.tsx` (Vitest) + `tests/e2e/chart-analysis.spec.ts` (Playwright : vérifie arrivée d’events SSE).

---

## 9) **SearxNG** autohébergé et intégré

**Objectif :** disposer d’un moteur de recherche privé (actu crypto, docs techniques), accessible par le back et par l’agent.

* [x] **Ajouter service SearxNG au Compose**
  **Fichiers :** `docker/docker-compose.dev.yml`, `docker/docker-compose.yml`

  * [x] Service `searxng` (image officielle), ports `8080:8080`, volume config `searxng:/etc/searxng`.
  * [x] Var env : `BASE_URL=http://searxng:8080`, `SEARXNG_SECRET=…`, `UWsgi`/`workers` raisonnables.

* [x] **Configuration SearxNG**
  **Fichiers :** `docker/searxng/settings.yml` (nouveau)

  * [x] Activer moteurs pertinents : news (GNews/Bing si clés), GitHub, Reddit (si clé), Wikipedia, crypto-news RSS, docs techniques.
  * [x] Forcer **safesearch=Off**, langue par défaut `fr`, `max_results` 20–50.

* [x] **Client back pour SearxNG**
  **Fichiers :** `src/chart_mcp/services/search/searxng_client.py`, `src/chart_mcp/routes/search.py` (nouveau)

  * [x] Endpoint : `GET /api/v1/search?q=...&categories=news,science` → agrège `title,url,snippet,source,score`.
  * [x] **Tests** : `tests/search/test_searxng_client.py` (contract HTTP, erreurs réseau) ; `tests/api/test_search_route.py`.

* [x] **Intégration agent**
  **Fichier :** `src/chart_mcp/mcp_server.py`

  * [x] Tool MCP `web_search(query, categories, time_range)` → s’appuie sur client SearxNG.
  * [x] **Tests** : `tests/mcp/test_web_search_tool.py`.

*(Le cahier ne l’exige pas explicitement, mais c’est un besoin projet. On l’intègre en option autonome et documentée.)*

---

## 10) Config, secrets, CORS, **Healthcheck Docker**

* [x] **Config Pydantic**
  **Fichier :** `src/chart_mcp/config.py`, `.env.example`

  * [x] Variables : `API_TOKEN`, `EXCHANGE`, `ALLOWED_ORIGINS`, `FEATURE_FINANCE`, `SEARXNG_BASE_URL`.
  * [x] `.env.example` = valeurs fictives, commentées ; **ne pas commiter `.env`**.

* [x] **Healthcheck Docker**
  **Fichiers :** `docker/Dockerfile`, `docker/healthcheck.py` (nouveau)

  * [x] `HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python","docker/healthcheck.py"]`
  * [x] Script : requête `GET http://localhost:8000/health` → exit 0/1.
  * [x] **Tests** : `tests/docker/test_healthcheck_script.py` (simule 200/500).

* [x] **CORS**
  **Fichier :** `src/chart_mcp/app.py`

  * [x] Charger `ALLOWED_ORIGINS` depuis env ; refuser si vide **en prod** ; autoriser localhost en dev.
  * [x] **Test** : cf. §6.

---

## 11) Finance (feature flag) – si présent dans le repo

* [x] **Feature flag**
  **Fichiers :** `src/chart_mcp/app.py`, `src/chart_mcp/routes/finance/*.py`

  * [x] Monter/démonter le router si `FEATURE_FINANCE=true`.
  * [x] **Tests** : `tests/api/test_finance_flag.py`.

---

## 12) Observabilité & logs

* [x] **Logs structurés**
  **Fichier :** `src/chart_mcp/utils/logging.py`

  * [x] Inclure `request_id`, `stage`, `latency_ms`, `symbol`, `timeframe`.
  * [x] **Tests** : `tests/utils/test_logging_context.py` (enrichissement MDC/ctx).

* [x] **/metrics Prometheus** (optionnel)
  **Fichiers :** `src/chart_mcp/routes/metrics.py`

  * [x] Compteurs : erreurs provider, latence par étape SSE, nb d’events envoyés.
  * [x] **Tests** : `tests/api/test_metrics.py`.

---

## 13) Documentation développeur

* [x] **README**
  **Fichier :** `README.md`

  * [x] Sections : **Architecture**, **MCP usage**, **API endpoints**, **SSE client snippet**, **SearxNG** (démarrage + variables), **Docker/Compose**, **Tests/CI**, **Sécurité**.
  * [x] Exemples `curl` : `/api/v1/market/ohlcv`, `/api/v1/indicators/compute`, `/api/v1/levels`, `/api/v1/patterns`, `/stream/analysis`, `/api/v1/search`.
  * [x] **Badge CI** + matrice versions (Py 3.11/3.12).

---

## 14) Pipelines CI/CD

* [x] **GitHub Actions**
  **Fichiers :** `.github/workflows/ci.yml`

  * [x] Jobs : `lint (ruff)`, `typecheck (mypy)`, `test (pytest -q)`, `build-backend (docker build)`, `build-frontend`, `playwright-e2e`.
  * [x] Cache pip/pytest ; artefacts coverage/**junit** ; push image `:sha` sur registry si secrets fournis.

---

## 15) Nettoyage & cohérence

* [x] **Supprimer code mort / renommer incohérences**
  **Fichiers :** `src/chart_mcp/**`

  * [x] Éliminer utilitaires non utilisés, uniformiser noms (`finance-chart-artifact` ↔ `frontend/components/ChartArtifact.tsx`).
  * [x] **Tests** : adapter snapshots/imports.

* [x] **Conventions**
  **Fichiers :** `pyproject.toml` / `ruff.toml` / `mypy.ini`

  * [x] Règles strictes : `no-redefined-builtin`, `no-implicit-optional`, `warn-redundant-casts`.
  * [x] **CI** échoue si lints échouent.

---

# 🧪 Plan de tests (récapitulatif)

* **Unitaires** :

  * `tests/indicators/*` (SMA/EMA/RSI/MACD/BB — valeurs attendues) 
  * `tests/levels/*` (pics + clustering) 
  * `tests/patterns/*` (**tête-épaules**) 
  * `tests/providers/*` (CCXT + erreurs)
  * `tests/analysis/*` (streaming tokenisé) 

* **Intégration API** :

  * `tests/api/test_routes_ok_ko.py` (200/4xx), `test_auth.py`, `test_cors.py`, `test_search_route.py` (SearxNG).

* **SSE** :

  * `tests/stream/test_sse_flow.py`: ordre, heartbeat, annulation, `token` puis `done`. 

* **E2E Front (Playwright)** :

  * chargement `/chart`, saisie symbol/timeframe, réception d’events SSE, rendu chart, rendu du texte tokenisé.

---

# 🏗️ Build & run (contrôles)

* **Backend** :

* [x] `make setup && make dev`
  * [ ] Docker : `docker compose up --build` (services : `api`, `searxng`).
  * [ ] `HEALTHCHECK` OK (`/health`).

* **Frontend** :

* [x] `pnpm i && pnpm dev` (Next sur 3000), `EventSource` vers `http://localhost:8000/stream/analysis`.

* **SearxNG** :

  * [ ] accessible `http://localhost:8080`, route back `/api/v1/search` opérationnelle.

* **CI** :

  * [ ] lint/typecheck/tests passent ; images Docker construites ; e2e vert.
    * ✅ 2025-10-28 — Déclenchement corrigé : la workflow `CI` s'exécute maintenant sur toutes les branches (`push`/`pull_request`) et peut être lancée manuellement via `workflow_dispatch`.
    * Playwright `pnpm test:e2e` démarre désormais automatiquement Next.js et injecte un état de session, mais il reste à valider le pipeline complet (lint → build images).

---

## Notes finales

* Le **tête-épaules** et le **texte tokenisé** sont les compléments majeurs pour coller au cahier.  
* L’**instance SearxNG** ajoute de la valeur (recherches actus/docu crypto) sans complexifier le cœur.
* Le front **Next.js + Lightweight Charts** est recommandé par le cahier pour une expérience réactive. 

Si tu veux, je peux enchaîner par des **patches prêts à appliquer** (diffs) pour chaque fichier listé.

---

## Historique

- 2025-10-27T19:21:05+00:00 — gpt-5-codex : Implémentation de la détection tête-épaules (classique + inversée), ajout des métadonnées direction/indices, extension du dataclass `PatternResult` et création des tests unitaires dédiés.

- 2025-10-27T19:32:07Z — gpt-5-codex : Normalisation stricte des timeframes (422 en cas d'erreur), enrichissement du provider CCXT (retries, mapping symboles) et ajout des tests unitaires `tests/providers/test_ccxt_provider.py` + ajustements lint.
- 2025-10-27T19:42:17+00:00 — gpt-5-codex : Refonte de la détection supports/résistances (clustering tolérant, scoring fort/général, paramètres exposés) + mise à jour des schémas/streams et création des tests `tests/levels/test_levels_detection.py`.
- 2025-10-27T20:10:00+00:00 — gpt-5-codex : Uniformisation des indicateurs (alias SMA/MA, colonnes `ema_<window>`, `macd_signal`, `bb_upper`...), documentation des paramètres par défaut, ajout des validations RSI/MACD et création de `tests/indicators/test_indicators_values.py` + corrections API analysis (strength_label & bad_request timeframe).
- 2025-10-27T20:55:00+00:00 — gpt-5-codex : Refonte du pipeline SSE (événements `step:start`/`step:end`, heartbeat horodaté, arrêt via `request.is_disconnected`), génération IA tokenisée et nouveaux tests `tests/analysis/test_streaming_text.py` & `tests/stream/test_sse_flow.py` couvrant ordre, heartbeat et annulation.
- 2025-10-27T21:35:00+00:00 — gpt-5-codex : Harmonisation des gardes d'authentification (`X-Session-User`), durcissement CORS (fallback dev + erreur en prod) et ajout des tests `tests/integration/test_auth_guards.py`, `test_market_routes.py`, `test_cors.py` après mise à jour des fixtures/env.
- 2025-10-27T22:20:00+00:00 — gpt-5-codex : Normalisation complète du serveur MCP (schémas Pydantic dédiés, tests `tests/mcp/test_tools_contract.py` avec snapshots) et documentation README mise à jour (section MCP/stdio, lien spec, exemple FastMCP).
- 2025-10-27T22:55:00+00:00 — gpt-5-codex : Intégration SearxNG (services Compose + settings), ajout du client HTTP + route `/api/v1/search`, extension de la config `.env` et création des tests `tests/search/test_searxng_client.py` & `tests/api/test_search_route.py`.
- 2025-10-27T22:03:41Z — gpt-5-codex : Ajout du tool MCP `web_search` (validation Pydantic + client SearxNG partagé), nouveaux schémas de réponse et tests `tests/mcp/test_web_search_tool.py`, mise à jour des contrats existants.
- 2025-10-27T23:40:00Z — gpt-5-codex : Externalisation du probe Docker vers `docker/healthcheck.py`, ajout du HEALTHCHECK Dockerfile et création de `tests/docker/test_healthcheck_script.py` pour couvrir succès, retries et échecs verbalisés.

- 2025-10-28T00:25:00Z — gpt-5-codex : Documentation OpenAPI (tags & summaries), ajout du test `tests/integration/test_openapi_docs.py` et refonte README (sections architecture, SearxNG, SSE, badge CI, exemples curl).
- 2025-10-28T01:45:00Z — gpt-5-codex : Implémentation de la page `/chart` (formulaire, Lightweight Charts, flux SSE via fetch-event-source), ajout des tests Vitest `components/chart/chart-analysis.test.tsx` et Playwright `tests/e2e/chart-analysis.spec.ts`, documentation README/ENV mise à jour et ajout des variables `NEXT_PUBLIC_API_*`.
- 2025-10-28T02:40:00Z — gpt-5-codex : Instrumentation des logs structurés (contextvars, `log_stage`, enrichissement symbol/timeframe), intégration aux routes/SSE, création de `tests/utils/test_logging_context.py` et validation via `tests/stream/test_sse_flow.py`.
- 2025-10-28T03:30:00Z — gpt-5-codex : Ajout du registre Prometheus (compteurs provider, histogrammes SSE, compteur d'événements), création du endpoint `/metrics`, instrumentation CCXT/SSE, renforcement Ruff (`A`), documentation README et nouveaux tests `tests/api/test_metrics.py` + `tests/services/test_metrics_registry.py`.
- 2025-10-28T04:20:00Z — gpt-5-codex : Ajout du cache OHLCV en mémoire (LRU + TTL configurables), extension de la config `.env`, documentation README et nouveaux tests `tests/providers/test_ccxt_provider.py` couvrant hit/expiration/éviction.
- 2025-10-28T05:10:00Z — gpt-5-codex : Renommage de `finance-chart-artifact` en `ChartArtifact`, mise à jour des imports/tests (Playwright, Vitest, harness) et ajustement des `data-testid`; exécution de `pnpm vitest --run components/finance/ChartArtifact.test.tsx components/messages.test.tsx`.
- 2025-10-28T06:45:00Z — gpt-5-codex : Correction de l'indentation Makefile (tabs), ajout de la documentation backend (`make setup` + `ALLOWED_ORIGINS`) et validation de `make setup` + `make dev`.
- 2025-10-28T07:55:00Z — gpt-5-codex : Stabilisation de l'espace Next.js (dépendances `next`/`lightweight-charts` figées, scripts `pnpm` documentés, typage SSE ajusté), ajout d'un stub TypeScript pour `@vitejs/plugin-react` et conversion de Vitest en import dynamique. Vérification via `pnpm lint`, `pnpm typecheck`, `pnpm vitest --run`.
- 2025-10-28T08:45:00Z — gpt-5-codex : Automatisation du serveur Next.js pour Playwright (`webServer` + session JSON), mise à jour de `tests/setup/auth.setup.ts`, ajout du root layout App Router et documentation README/`.gitignore`. Tests : `pnpm typecheck`, `pnpm exec playwright test tests/e2e/chart-analysis.spec.ts --reporter=list`.
- 2025-10-28T09:30:00Z — gpt-5-codex : Correction du déclenchement CI (workflow sur toutes les branches + déclenchement manuel `workflow_dispatch`) pour que les jobs démarrent sur les branches de travail.
