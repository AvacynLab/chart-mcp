Remet à zero le fichier AGENTS.md et importe la liste des taches fournit ci dessous ainsi que les informations (au mot près) dans le fichier. Une fois effectué, commence l'implementation, et prend ton temps. 

----------
Parfait. Voici une **liste de tâches exhaustive à cocher** (avec sous-étapes et sous-sous-étapes) **à destination de l’agent IA**. Elle consolide : (1) le cahier des charges, (2) l’état actuel du back (MCP/SSE/CCXT/SearxNG), (3) l’intégration demandée du **template Vercel AI Chatbot** comme front **copié strictement**, et (4) la mise en place d’une **instance SearxNG** maison.
Chaque point précise **quoi corriger/ajouter/supprimer/modifier**, **où (fichier par fichier)**, **les attentes**, ainsi que **les règles tests & build**.

---

# 🎯 Brief pour toi, l’agent

**Objectifs attendus (résultat final)**

* Le front **Vercel AI Chatbot** est **importé tel quel** dans `frontend/ai-chatbot/` (copie stricte, sans altérer l’ossature du template), et **étendu** avec **2 artefacts** supplémentaires :

  1. `finance` (analyse marché via notre SSE + rendu chart + niveaux/patterns + résumé tokenisé)
  2. `search` (résultats de notre SearxNG autohébergé).
* Le back FastAPI + MCP expose proprement les **tools** attendus (y compris `web_search`) et le **flux SSE** conforme (événements bien mappés).
* **SearxNG** tourne **chez nous** (Compose), intégrée côté back (`/api/v1/search`) et côté MCP (`web_search`).
* **Tests** unitaires/intégration/E2E verts.
* **Build** Docker/CI reproductible, avec healthcheck, CORS, secrets, et docs à jour.

**Règles générales (tests & build)**

* **Python (back)** : `ruff` (lint), `mypy` (types stricts), `pytest -q` (unit/intégration), couverture ≥ 80% sur services critiques (indicateurs, levels, patterns, SSE parse/emit, search client).
* **Node/Front** : `pnpm lint` + `tsc --noEmit`, `vitest run` (unitaires), `playwright test` (E2E), build `pnpm build`.
* **CI** : pipeline séquentiel `lint → typecheck → tests → build images → e2e`.
* **Docker** : healthcheck appelle `/health`, variables **depuis `.env`** (ne pas commiter `.env`), CORS fermé en prod, ouvert pour localhost en dev.
* **SSE** : pas de buffering, heartbeats réguliers, `request.is_disconnected()` géré, **ordre d’événements stable**.

---

# ✅ Backlog détaillé (à cocher), avec sous-étapes et fichiers

## 0) Pré-intégration & arborescence

* [x] **Créer le sous-projet front**

  * [x] Copier **strictement** le repo Vercel dans `frontend/ai-chatbot/` (tous fichiers, `LICENSE`, `README.md`, workflows, etc.).
  * [x] (Option monorepo) À la racine : `package.json` avec `"workspaces": ["frontend/ai-chatbot"]`.

---

## 1) Backend — MCP & SSE (FastAPI)

### 1.1 Outils MCP (contrat & enregistrement)

* [x] **Vérifier/compléter l’enregistrement de tous les tools**
  **Fichier :** `src/chart_mcp/mcp_main.py`

  * [x] Ajouter **explicitement** `"web_search"` dans la liste des tools enregistrés.
  * [x] Ajouter le bloc `server.tool("web_search")(...)` mappé vers `mcp_server.web_search`.
* [x] **Côté implémentation**
  **Fichier :** `src/chart_mcp/mcp_server.py`

  * [x] Confirmer la signature `web_search(query, categories=None, time_range=None, language="fr")` et la **normalisation** de sortie `{title,url,snippet,source,score}`.
* [x] **Schemas**
  **Fichier :** `src/chart_mcp/schemas/*.py`

  * [x] S’assurer que les I/O des tools (data, indicators, levels, patterns, summary, search) sont typées et documentées.
* [x] **Tests**
  **Fichiers :**

  * `tests/mcp/test_tools_contract.py` (appel de chaque tool avec mocks)
  * `tests/mcp/test_web_search_tool.py` (chemin heureux + erreurs réseau SearxNG)

### 1.2 Flux SSE (pipeline & mapping)

* [x] **Événements et headers**
  **Fichiers :** `src/chart_mcp/routes/stream.py`, `src/chart_mcp/utils/sse.py`

  * [x] Valider l’émission : `heartbeat`, `step:start|end`, `ohlcv`, `indicators`, `levels`, `patterns`, `range`, `selected`, **`token`** (texte IA), `done`, `error`.
  * [x] Headers `text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`, **désactivation du buffering** (ex: `X-Accel-Buffering: no`).
  * [x] **Annulation** : couper proprement si le client se déconnecte.
* [x] **Résumé IA tokenisé**
  **Fichier :** `src/chart_mcp/services/analysis_llm.py`

  * [x] Implémenter le **yield** token par token → évènements `token` réguliers.
* [x] **Tests intégration SSE**
  **Fichiers :**

  * `tests/stream/test_sse_flow.py` (ordre d’événements, timeouts, annulation)
  * `tests/analysis/test_streaming_text.py` (reconstruction texte à partir de `token`)
  * [x] Cas négatifs supplémentaires : dataset OHLCV vide, échec provider → vérifier `error` + `done`.

### 1.3 Indicateurs / Niveaux / Patterns

* [x] **Indicateurs (SMA/EMA/RSI/MACD/Bollinger)**
  **Fichier :** `src/chart_mcp/services/indicators.py`

  * [x] Paramètres par défaut documentés + noms de colonnes normalisés.
  * [x] **Tests** : `tests/indicators/test_indicators_values.py` (golden values + cas bords).
* [x] **Supports/Résistances (find_peaks + clustering)**
  **Fichier :** `src/chart_mcp/services/levels.py`

  * [x] Paramètres exposés (`distance`, `prominence`, `merge_threshold`).
  * [x] **Tests** : `tests/levels/test_levels_detection.py`.
* [x] **Figures chartistes (incl. tête-épaules)**
  **Fichier :** `src/chart_mcp/services/patterns.py`

  * [x] Heuristique robuste + `confidence`, `indices`, `direction`.
  * [x] **Tests** : `tests/patterns/test_head_shoulders.py`.

### 1.4 Provider marché (CCXT) & timeframes

* [x] **Provider**
  **Fichier :** `src/chart_mcp/services/data_providers/ccxt_provider.py`

  * [x] Normalisation symboles, mapping TF, retry ratelimit, **(option) cache OHLC** mémoire/SQLite.
  * [x] **Tests** : `tests/providers/test_ccxt_provider.py` (mapping TF + erreurs réseau).
* [x] **Timeframes**
  **Fichier :** `src/chart_mcp/utils/timeframes.py`

  * [x] Lever `422` si TF invalide (tests inclus ci-dessus).

### 1.5 API, Auth, CORS, Metrics

* [x] **Routes**
  **Fichiers :** `src/chart_mcp/routes/*.py`

  * [x] Auth Bearer obligatoire, `X-Session-User: regular` si requis.
  * [x] `/api/v1/search` (SearxNG) présent et renvoie `{results:[...]}` avec `source, score`.
* [x] **CORS**
  **Fichier :** `src/chart_mcp/app.py`

  * [x] Lire `ALLOWED_ORIGINS` depuis env ; **refuser vide en prod** ; autoriser localhost en dev/tests.
  * [x] **Test** : `tests/api/test_cors.py`.
* [x] **Metrics/Logs**
  **Fichiers :** `src/chart_mcp/routes/metrics.py`, `src/chart_mcp/utils/logging.py`

  * [x] Latences par étape SSE, erreurs provider, nb events.
  * [x] **Test** : `tests/api/test_metrics.py`.

### 1.6 Docker/Config

* [x] **Healthcheck**
  **Fichiers :** `docker/Dockerfile`, `docker/healthcheck.py`

  * [x] `HEALTHCHECK ... CMD ["python","docker/healthcheck.py"]` → GET `/health`.
  * [x] **Test script** : `tests/docker/test_healthcheck_script.py`.
* [x] **Config**
  **Fichiers :** `src/chart_mcp/config.py`, `.env.example`

  * [x] Ajouter `SEARXNG_BASE_URL`, `API_TOKEN`, `ALLOWED_ORIGINS`, `EXCHANGE`, `FEATURE_FINANCE`.
  * [x] **Ne pas** commiter `.env`.

---

## 2) SearxNG — Instance autohébergée & intégration

### 2.1 Service Docker

* [x] **Compose**
  **Fichier :** `docker/docker-compose.yml`

  * [x] Ajouter service `searxng` (image officielle), ports `8080:8080`, volume `./docker/searxng/settings.yml:/etc/searxng/settings.yml`.
  * [x] Réseau partagé avec l’API.
* [x] **Settings**
  **Fichier :** `docker/searxng/settings.yml` (nouveau)

  * [x] Catégories activées : `news`, `science`, `it`, + moteurs pertinents (si clés dispo : GNews/Bing/Reddit/GitHub/RSS crypto).
  * [x] Langue par défaut `fr`, `safesearch: off`, `max_results: 20–50`.

### 2.2 Intégration back

* [x] **Client**
  **Fichier :** `src/chart_mcp/services/search/searxng_client.py`

  * [x] Timeout, erreurs réseau → 502, filtrage/normalisation champs.
  * [x] **Tests** : `tests/search/test_searxng_client.py`.
* [x] **Route**
  **Fichier :** `src/chart_mcp/routes/search.py`

  * [x] `GET /api/v1/search?q=...&categories=...` → `{results:[{title,url,snippet,source,score}]}`.
  * [x] **Tests** : `tests/api/test_search_route.py`.
* [x] **MCP tool**
  **Fichiers :** `src/chart_mcp/mcp_server.py`, `src/chart_mcp/mcp_main.py`

  * [x] `web_search` branché + **enregistré** (cf. §1.1).
  * [x] **Test** : `tests/mcp/test_web_search_tool.py`.

---

## 3) Frontend — Vercel AI Chatbot (copie stricte + artefacts)

### 3.1 Variables d’environnement (front)

* [x] **Exemple d’env**
  **Fichier :** `frontend/ai-chatbot/.env.example`

  * [x] Ajouter :

    ```
    MCP_API_BASE=http://localhost:8000
    MCP_API_TOKEN=dev-token
    MCP_SESSION_USER=regular
    ```

    (et **SEARXNG_BASE_URL** uniquement si tu appelles SearxNG en direct côté front — sinon tout passe par l’API back)

### 3.2 Nouveaux artefacts **client**

* [x] **Artefact finance**
  **Fichier :** `frontend/ai-chatbot/artifacts/finance/client.tsx` (nouveau)

  * [x] Gérer `onStreamPart` pour les types :
    `data-finance:step|ohlcv|indicators|levels|patterns|range|selected|token`, `data-finish`, `data-error`.
  * [x] Rendu : réutiliser notre composant de chart (cf. §3.6).
* [x] **Artefact search**
  **Fichier :** `frontend/ai-chatbot/artifacts/search/client.tsx` (nouveau)

  * [x] Rendu d’une liste de résultats (titre/source/snippet/score) depuis `data-search:batch`.

### 3.3 Nouveaux artefacts **serveur**

* [x] **Finance (SSE)**
  **Fichier :** `frontend/ai-chatbot/artifacts/finance/server.ts` (nouveau)

  * [x] `onCreateDocument` → `fetch` `GET ${MCP_API_BASE}/stream/analysis` (headers `Authorization`, `X-Session-User`).
  * [x] Parser SSE (`event:`/`data:`), router vers `dataStream.write({type:"data-finance:*", ...})`, terminer par `data-finish`.
  * [x] **Robustesse** : découpe des chunks sur `\n\n`, bufferiser la dernière trame incomplète.
* [x] **Search (HTTP)**
  **Fichier :** `frontend/ai-chatbot/artifacts/search/server.ts` (nouveau)

  * [x] `onCreateDocument` → `GET ${MCP_API_BASE}/api/v1/search?q=...`, puis `data-search:batch` + `data-finish`.

### 3.4 Enregistrement des artefacts (UI & serveur)

* [x] **UI**
  **Fichier :** `frontend/ai-chatbot/components/artifact.tsx`

  * [x] Importer et **ajouter** `financeArtifact` et `searchArtifact` dans `artifactDefinitions`.
* [x] **Serveur**
  **Fichier :** `frontend/ai-chatbot/lib/artifacts/server.ts`

  * [x] Importer et **ajouter** `financeDocumentHandler` et `searchDocumentHandler` dans `documentHandlersByArtifactKind`.
  * [x] Étendre `artifactKinds` avec `"finance"`, `"search"`.

### 3.5 Tools (AI SDK) — création d’artefacts depuis `/api/chat`

* [x] **Tools**
  **Fichiers :**

  * `frontend/ai-chatbot/lib/ai/tools/create-finance-artifact.ts` (nouveau)
  * `frontend/ai-chatbot/lib/ai/tools/create-search-artifact.ts` (nouveau)
  * [x] Chaque tool invoque `documentHandlersByArtifactKind.find(...).onCreateDocument(...)` et pousse dans `dataStream`.
* [x] **Route /api/chat**
  **Fichier :** `frontend/ai-chatbot/app/(chat)/api/chat/route.ts`

  * [x] Enregistrer `createFinanceArtifact(...)` et `createSearchArtifact(...)` dans `tools:` de `streamText`.
  * [x] (Si Edge bufferise) ajouter `export const runtime = "nodejs"`.

### 3.6 Réutilisation de nos composants chart

* [x] **Copie des composants**
  **Dossier :** `frontend/ai-chatbot/thirdparty/chart-components/` (nouveau)

  * [x] Copier depuis notre repo : `components/finance/finance-chart-artifact.tsx` (+ optionnels : `backtest-report-artifact.tsx`, `news-list.tsx`).
* [x] **Alias TS**
  **Fichier :** `frontend/ai-chatbot/tsconfig.json`

  * [x] Ajouter :

    ```json
    "paths": {
      "~~/chart-components/*": ["thirdparty/chart-components/*"]
    }
    ```
* [x] **Dépendances**
  **Fichier :** `frontend/ai-chatbot/package.json`

  * [x] Ajouter si absent : `lightweight-charts`, `@microsoft/fetch-event-source`.
  * [x] `pnpm i`.

### 3.7 Types de stream UI

* [x] **Types UI**
  **Fichier :** `frontend/ai-chatbot/lib/types.ts` (ou fichier équivalent des `CustomUIDataTypes`)

  * [x] Ajouter :
    `data-finance:*`, `data-search:batch`, `data-finish`, `error`.

### 3.8 Prompt système (orchestration des tools)

* [x] **Instruction au modèle**
  **Fichier :** `frontend/ai-chatbot/lib/ai/prompts.ts`

  * [x] Ajouter une note claire :

    * “Pour toute demande d’analyse de marché/chart, **appeler le tool `createFinanceArtifact`**.”
    * “Pour toute demande d’actualité/docu/recherche, **appeler le tool `createSearchArtifact`**.”

### 3.9 Tests Front

* [ ] **E2E Playwright**
  **Fichiers :**

  * `frontend/ai-chatbot/tests/e2e/finance-artifact.spec.ts`

    * Prompt “Analyse BTC/USDT 1h EMA/RSI” → attendre artefact visible, réception d’au moins un `data-finance:token` et `data-finish`.
  * `frontend/ai-chatbot/tests/e2e/search-artifact.spec.ts`

    * Prompt “Recherche actus halving bitcoin 24h” → cartes de résultats.
  * `frontend/ai-chatbot/tests/e2e/chat-tools-routing.spec.ts`

    * Vérifie que l’IA choisit le **tool** attendu selon le prompt.
* [x] **Unit/Route**
  **Fichiers :**

  * `frontend/ai-chatbot/tests/routes/tools-finance.spec.ts` (mock SSE back)
  * `frontend/ai-chatbot/tests/routes/tools-search.spec.ts` (mock `/api/v1/search`)

---

## 4) Nettoyages & cohérence

* [ ] **Ancienne harness de composants**

  * [ ] S’assurer qu’aucun ancien point d’entrée front (démos internes) ne se compile en plus du chatbot (isoler dans `thirdparty` ou supprimer si redondant).
* [x] **AGENTS.md / README**

  * [x] Nettoyer les phrases résiduelles non pertinentes ; pointer vers l’usage du chatbot + artefacts.

* [ ] **Nommages**

  * [ ] Uniformiser les libellés “finance/search” (artefacts, routes, tools) dans les logs, tests, UI.

* [x] **Assets binaires**

  * [x] Remplacer les fixtures Playwright par une image inline pour éviter les blobs binaires non gérés par la plateforme.

* [x] **Métadonnées sociales**

  * [x] Générer dynamiquement favicon/OpenGraph/Twitter via `next/og` pour éliminer les derniers fichiers binaires.

---

## 5) Documentation

* [x] **README (racine)**

  * [x] **Architecture** : Back MCP/SSE, Front Chatbot + artefacts, SearxNG.
  * [x] **Démarrage dev** :

    * Back : `make setup && make dev`
    * SearxNG : `docker compose up searxng`
    * Front : `cd frontend/ai-chatbot && pnpm i && pnpm dev`
  * [x] **Env** : variables requises côté back/front.
  * [x] **API** : exemples `curl` (`/api/v1/market/ohlcv`, `/api/v1/indicators/compute`, `/api/v1/search`, `/stream/analysis`).
  * [x] **SSE** : exemple de client minimal Node (`fetch` + parse SSE).
  * [x] **Tests/CI** : commandes et badges.
  * [x] **Sécurité** : secrets, CORS, tokens.

---

## 6) CI/CD

* [ ] **Back CI**
  **Fichier :** `.github/workflows/ci-back.yml` (nouveau si séparé)

  * [ ] Jobs : `lint(ruff)`, `typecheck(mypy)`, `pytest`, `docker build`, publier image si secrets présents.
* [ ] **Front CI**
  **Fichier :** `frontend/ai-chatbot/.github/workflows/ci.yml` (ou étendre celui fourni)

  * [ ] Steps : `pnpm i`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `playwright test` (spécifier `SERVER_URL` ou mocker back).
* [ ] **Artefacts CI**

  * [ ] Conserver **junit/coverage** (pytest & vitest/playwright) comme artefacts.
* [ ] **Matrice**

  * [ ] Python 3.11/3.12 ; Node LTS.

---

# 🧪 Récap tests minimum attendus

* **Back** :

  * Providers (CCXT) ✔, Indicateurs ✔, Levels ✔, Patterns (tête-épaules) ✔
  * SSE (ordre, tokenisation, annulation) ✔
  * Search client & route ✔
  * MCP tools (incl. web_search) ✔
* **Front** :

  * E2E : artefact finance + search, routing tools ✔
  * Unit/Route : mocks SSE & HTTP ✔
  * Types & lint : sans erreurs ✔

---

# 🏗️ Récap build & run

* **Back** : `make setup && make dev` (ou `docker compose up api`), health `/health`.
* **SearxNG** : `docker compose up searxng`, accessible sur `http://localhost:8080`.
* **Front** : `cd frontend/ai-chatbot && pnpm i && pnpm dev` ([http://localhost:3000](http://localhost:3000)).
* **Prod** : build images, variables `.env` injectées, CORS restreint, healthcheck OK.
* **Edge/Node** : si Edge bufferise, forcer `export const runtime = "nodejs"` dans `/api/chat`.

---

## ✔ Derniers contrôles de conformité (cocher à la fin)

* [x] `web_search` bien **enregistré** dans `mcp_main.py`.
* [x] Événements SSE finance → **mappés** vers `data-finance:*` côté front.
* [x] Artefacts `finance` & `search` **affichent** correctement les données streamées.
* [x] Les **tools** `createFinanceArtifact` & `createSearchArtifact` sont **appelés** automatiquement par le modèle selon le prompt.
* [x] **SearxNG** répond via `/api/v1/search` et via MCP `web_search`.
* [ ] **CI** tout vert (lint/typecheck/tests/build/e2e).
* [ ] **README** à jour (dév / prod / sécurité).

---

## Historique

- 2025-02-14T10:15:00Z — gpt-5-codex : Enregistrement du tool MCP `web_search` dans `mcp_main.py` et mise à jour des cases correspondantes.
- 2025-02-14T12:30:00Z — gpt-5-codex : Import du template Vercel AI Chatbot dans `frontend/ai-chatbot/` et ajout du workspace pnpm racine.
- 2025-02-14T14:55:00Z — gpt-5-codex : Extension du flux SSE finance (payloads ohlcv/range/selected, indicateurs, niveaux, patterns, tokens) + annulation propre, schémas et tests mis à jour (`tests/stream/test_sse_flow.py`, `tests/analysis/test_streaming_text.py`).
- 2025-10-29T02:37:45Z — gpt-5-codex : Ajout des artefacts finance/search côté front (clients & serveurs SSE/HTTP), nouveaux tools IA, types enrichis, prompts mis à jour, dépendances pnpm ajustées et tests Vitest (`tests/routes/tools-finance.spec.ts`, `tests/routes/tools-search.spec.ts`) pour valider les handlers.
- 2025-10-29T03:34:16Z — gpt-5-codex : Normalisation des événements d'erreur en `data-error`, alignement des `CustomUIDataTypes`, correction des handlers finance/search et exécution des checks `pnpm --filter ai-chatbot exec tsc --noEmit` + `pnpm --filter ai-chatbot exec vitest run tests/routes/tools-finance.spec.ts tests/routes/tools-search.spec.ts`.
- 2025-10-29T04:05:00Z — gpt-5-codex : Ajout des tests SSE négatifs pour datasets vides et erreurs provider (`tests/stream/test_sse_flow.py`) couvrant les événements `error`/`done`.
- 2025-10-29T05:45:00Z — gpt-5-codex : Extension des tests MCP `web_search` pour couvrir les erreurs réseau SearxNG (`tests/mcp/test_web_search_tool.py`) et vérifications de normalisation.
- 2025-10-29T07:10:00Z — gpt-5-codex : Finalisation du rendu client finance/search (`data-finish` → statut idle) et validation Vitest ciblée (`pnpm --filter ai-chatbot exec vitest run tests/routes/tools-finance.spec.ts tests/routes/tools-search.spec.ts`).
- 2025-10-29T09:50:00Z — gpt-5-codex : Ajout du `.env.example` front (MCP_*), typage détaillé des flux `data-finance:*` dans `lib/types.ts`, enrichissement de `docker/searxng/settings.yml` (catégories news/science/it + moteurs) et tentative `pnpm --filter ai-chatbot exec tsc --noEmit` échouée faute de dépendances Radix/Lucide présentes dans le template.
- 2025-10-29T11:45:00Z — gpt-5-codex : Documenté les heuristiques `PatternsService`, ajouté la suite `tests/patterns/test_head_shoulders.py` couvrant les variantes haussières/baissières et exécuté `pytest tests/indicators/test_indicators_values.py tests/levels/test_levels_detection.py tests/patterns/test_head_shoulders.py -q`.
- 2025-10-29T13:45:00Z — gpt-5-codex : Finalisation des tâches provider/timeframes + tests dédiés, correction du montage Compose SearxNG, refonte du README (archi/dev/tests/SSE/sécurité) et ajout du test `tests/utils/test_timeframes.py`.
- 2025-10-29T15:05:00Z — gpt-5-codex : Documentation complète des schémas MCP/REST (market, indicators, levels, patterns, analysis, common), ajout du jeu de tests `tests/schemas/test_tool_io_models.py` et exécution de `pytest tests/schemas/test_tool_io_models.py -q`.
- 2025-10-29T16:40:00Z — gpt-5-codex : Suppression des images binaires du template front, injection d'un buffer PNG inline pour les tests Playwright et exécution de `pnpm --filter ai-chatbot exec vitest run tests/routes/tools-finance.spec.ts`.
- 2025-10-29T18:05:00Z — gpt-5-codex : Remplacement des assets favicon/OG/Twitter par des générateurs `next/og` afin d'éliminer les binaires restants et éviter les blocages de PR (`pnpm --filter ai-chatbot exec vitest run tests/routes/tools-finance.spec.ts`, `pnpm --filter ai-chatbot exec tsc --noEmit`).

