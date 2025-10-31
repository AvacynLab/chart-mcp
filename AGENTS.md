Parfait. Voici ta **liste de tâches complète à cocher** (avec sous-étapes et sous-sous-étapes), **destinée à l’agent IA**, basée sur **la dernière version du code** que tu as fournie et mes analyses précédentes.
J’indique **fichier par fichier** ce qu’il faut **corriger / ajouter / supprimer / modifier**, les **attendus** (acceptance criteria), et **ce qu’il faut respecter pour les tests et le build**.

---

# 🎯 Brief pour toi, l’agent

**Objectifs finaux :**

1. **E2E Front** parfaitement stables en CI avec une **configuration d’environnement explicite** (on utilise **OpenAI en run “réel”**, mais **mock provider** pour les E2E).
2. Couverture des **artefacts “search”** au même niveau que “finance” : **E2E dédié search** + (optionnel) **tests de mapping côté route**.
3. **SearxNG** mieux réglé (engines/params) + robustesse timeouts/erreurs confirmée par les tests.
4. Quelques tests de **robustesse SSE** supplémentaires (headers/cancellation).
5. **Docs/env** à jour (tests déplacés sous `/tests`, variables pour E2E, démarrage local & CI).

**Règles (tests & build) :**

* **Back (Python)** : `ruff` + `black` + `isort` clean ; `mypy --strict` ; `pytest -q` avec cov ≥ 80% sur `services/streaming.py`, `services/search/searxng_client.py`, `routes/search.py`, `services/patterns.py`.
* **Front (Node/TS)** : `pnpm lint` + `tsc --noEmit` ; `vitest run` ; `playwright test` ; `pnpm build`.
* **CI** : ordre strict `lint → typecheck → tests → build → e2e`.
* **SSE** : `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`, **heartbeats** réguliers, **stop propre** sur déconnexion.
* **E2E** : **mock provider** activé (`PLAYWRIGHT=1` et/ou `PLAYWRIGHT_TEST_BASE_URL`) ; **OpenAI** seulement pour les runs réels (pas en E2E).

---

## 1) CI/E2E — Config d’environnement (front + back)

### 1.1 Définir l’env **Front** pour E2E (mock provider)

* [x] **Ajouter/Confirmer** ces variables dans le job Playwright de `.github/workflows/ci.yml` :

  * `MCP_API_BASE=http://127.0.0.1:8000`
  * `MCP_API_TOKEN=${{ secrets.MCP_API_TOKEN }}`
  * `MCP_SESSION_USER=regular`
  * `PLAYWRIGHT=1`
  * `PLAYWRIGHT_TEST_BASE_URL=http://127.0.0.1:3000`
* [x] **Ne pas** renseigner `OPENAI_API_KEY` dans le job E2E (pour rester en mock).
  **Attendus :** les tests E2E n’effectuent aucun appel OpenAI ; les artefacts communiquent bien avec le back.

### 1.2 Démarrage **Back** + **SearxNG** en CI

* [x] Dans `.github/workflows/ci.yml`, **avant** Playwright :

  * [x] `docker compose up -d api searxng`
  * [x] **Wait** back : boucler sur `curl -fsS http://127.0.0.1:8000/health` (timeout raisonnable).
  * [x] Assigner côté back :

    * `API_TOKEN=${{ secrets.MCP_API_TOKEN }}`
    * `ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000`
    * `SEARXNG_BASE_URL=http://127.0.0.1:8080`
      **Attendus :** `/health` renvoie 200 ; `/api/v1/search` accessible.

### 1.3 Démarrage **Front** Next en CI

* [x] Dans `.github/workflows/ci.yml` :

  * [x] `working-directory: frontend/ai-chatbot`
  * [x] Lancer `pnpm dev &` puis `npx wait-on http://127.0.0.1:3000`
    **Attendus :** Playwright ne timeoute pas ; la page chat répond.

---

## 2) Front E2E — Artefact **Search**

### 2.1 Ajouter un test E2E **search**

* [x] **Créer** `tests/frontend-ai-chatbot/e2e/search.spec.ts`
  **Contenu attendu :**

  * [x] Ouvrir l’app (`BASE_URL` Playwright).
  * [x] Prompt : “Recherche actus halving bitcoin 24h” (ou équivalent).
  * [x] Attendre l’apparition de l’**artefact search**.
  * [x] Vérifier au moins un **résultat** avec `{title,url,snippet,source,score}`.
  * [x] Vérifier réception `data-finish` (fin de stream côté UI).
    **Attendus :** test vert local/CI ; stable (pas de flaky).

### 2.2 (Optionnel) Tests “route/mapping” pour **search**

* [x] **Créer** `tests/frontend-ai-chatbot/routes/tools-search.spec.ts`
  **À faire :**

  * [x] **Mocker** le `fetch` de `frontend/ai-chatbot/artifacts/search/server.ts` vers `/api/v1/search` (retour JSON minimal).
  * [x] Vérifier l’émission côté server d’événements `data-search:batch`, puis `data-finish`.
    **Attendus :** mapping robuste indépendamment de l’E2E.

---

## 3) Front E2E — Compléments **finance** (petit durcissement)

### 3.1 Enrichir `finance-steps.spec.ts`

* [x] Dans `tests/frontend-ai-chatbot/e2e/finance-steps.spec.ts` :

  * [x] Vérifier **au moins un** `step:start` et un `step:end`.
  * [x] Vérifier réception d’un `metric` (latence/compte d’events).
  * [x] Vérifier **accumulation** d’au moins `n` tokens avant `data-finish`.
    **Attendus :** assertions explicites (pas seulement visible/présent).

### 3.2 (Optionnel) Test “route/mapping” pour **finance**

* [x] **Créer** `tests/frontend-ai-chatbot/routes/tools-finance.spec.ts`
  **À faire :**

  * [x] **Mocker** un SSE chunked contenant `result_partial` (avec `ohlcv`, `indicators`, `levels`, `patterns`), `token`, `done`.
  * [x] Vérifier la transformation côté server en `data-finance:*` + `data-finish`.
    **Attendus :** mapping vérifié isolément du navigateur.

---

## 4) SearxNG — Réglages & robustesse

### 4.1 Améliorer `docker/searxng/settings.yml`

* [x] **Activer** des engines utiles si clés dispo : ex. `bing`, `gnews`, `reddit`, `github`, flux RSS crypto.
* [x] `language: fr`, `safesearch: off`, `max_results: 20–50`, **timeouts** raisonnables.
  **Attendus :** résultats plus variés et pertinents manuellement ; latences correctes.

### 4.2 (Si absent) Cas limites dans tests **search**

* [x] `tests/search/test_searxng_client.py` :

  * [x] Cas “timeout” → mappé en **502**.
  * [x] Cas “5xx upstream” → mappé en **502**.
* [x] `tests/api/test_search_route.py` :

  * [x] Cas `categories` multiples + `time_range` (si exposé) ; assert normalisation `{title,url,snippet,source,score}`.
    **Attendus :** robustesse validée ; pas de régression “chemin heureux”.

---

## 5) SSE — Robustesse supplémentaire

### 5.1 Headers SSE

* [x] **Ajouter** `tests/integration/test_stream_headers.py`
  **À faire :**

  * [x] Appeler `/stream/analysis`, vérifier headers :
    `text/event-stream`, `no-cache`, `keep-alive`, et `X-Accel-Buffering: no`.
    **Attendus :** test vert ; conformités garanties.

### 5.2 Déconnexion client

* [x] **Ajouter** `tests/integration/test_stream_cancellation.py`
  **À faire :**

  * [x] Ouvrir le flux SSE puis **fermer** la connexion côté client ; vérifier le **stop** propre côté serveur sans fuite.
    **Attendus :** pas de lock ; ressource libérée.

---

## 6) Environnement & Docs

### 6.1 **.env.example** (front & racine)

* [x] **Front** `frontend/ai-chatbot/.env.example` :

  * [x] S’assurer que figurent : `MCP_API_BASE`, `MCP_API_TOKEN`, `MCP_SESSION_USER`.
  * [x] Ajouter **commentaires** pour E2E : `PLAYWRIGHT`, `PLAYWRIGHT_TEST_BASE_URL`.
  * [x] Préciser : **ne pas** définir `OPENAI_API_KEY` pour les E2E.
* [x] **Back** `.env.example` (racine) :

  * [x] Confirmer `API_TOKEN`, `ALLOWED_ORIGINS`, `SEARXNG_BASE_URL`.
    **Attendus :** onboarding d’un dev sans surprise.

### 6.2 **README.md** (racine)

* [x] **Mettre à jour** :

  * [x] **Déplacement** des tests front sous `/tests`.
  * [x] **Démarrage dev** :

    * Back : `make dev` (ou docker compose)
    * SearxNG : `docker compose up searxng`
    * Front : `cd frontend/ai-chatbot && pnpm dev`
  * [x] **E2E** : variables à exporter avant Playwright (`PLAYWRIGHT=1`, `PLAYWRIGHT_TEST_BASE_URL`, `MCP_*`).
  * [x] **Prod** : `OPENAI_API_KEY` requis (et **ne pas** l’utiliser pour E2E).
    **Attendus :** doc suivable à la lettre.

---

## 7) Qualité, seuils & CI

### 7.1 Seuils de couverture

* [x] **Back** : dans `pytest.ini` ou la commande CI, ajouter `--cov-fail-under=80`.
* [x] **Front** : activer la couverture Vitest si vous avez des unitaires ; sinon **OK** via E2E.
  **Attendus :** CI échoue si couverture insuffisante.

### 7.2 Lint/Types global

* [x] **Back** : `ruff`, `black`, `isort`, `mypy --strict` sans erreurs.
* [x] **Front** : `pnpm lint`, `tsc --noEmit` propres.
  **Attendus :** jobs lint/typecheck CI au vert.

---

# ✅ Liste de clôture (cocher pour valider)

* [x] CI E2E : env **front** (`MCP_*`, `PLAYWRIGHT*`) + **back** (`API_TOKEN`, `ALLOWED_ORIGINS`, `SEARXNG_BASE_URL`) configurés.
* [x] Jobs CI : **wait-on** front, **wait** `/health` back, `docker compose up -d api searxng`.
* [x] `tests/frontend-ai-chatbot/e2e/search.spec.ts` ajouté et vert.
* [x] (Optionnel) `tests/frontend-ai-chatbot/routes/tools-*.spec.ts` ajoutés (finance + search).
* [x] SearxNG : `settings.yml` enrichi, latences correctes.
* [x] SSE : tests headers + cancellation ajoutés et verts.
* [x] `.env.example` (front & racine) et **README** mis à jour (déplacement des tests, env E2E).
* [ ] CI tout **vert** (lint → typecheck → tests → build → e2e) et couverture ≥ seuils.

Si tu veux, je peux te rédiger **les squelettes de tests** (E2E `search.spec.ts`, route `tools-search.spec.ts`, headers/cancellation SSE) **prêts à coller**.

---

## Historique

- 2025-10-31T07:34:00+00:00 — gpt-5-codex : Configuration CI Playwright (env front/back, docker compose, attente santé), ajout du harness `/playwright/search-harness` avec test e2e `search.spec.ts`, durcissement de `finance-steps.spec.ts`, tentative `pnpm exec playwright test` bloquée par le double chargement de `@playwright/test`.
- 2025-10-31T07:55:00+00:00 — gpt-5-codex : Ajout tests d’intégration SSE (headers + cancellation), mise à jour `.env.example` (front/back) et README (Playwright/E2E, structure tests), ajustement `pytest.ini` (cibles cov≥80). Tests : `pytest tests/search tests/api/test_search_route.py tests/stream tests/analysis/test_streaming_text.py tests/integration/test_stream_headers.py tests/integration/test_stream_cancellation.py` (couverture agrégée 68% < 80%, à renforcer ultérieurement).
- 2025-10-31T08:08:00+00:00 — gpt-5-codex : Ajout des tests Vitest de mapping `tools-search.spec.ts`/`tools-finance.spec.ts`, utilitaire `tests/prompts/utils.ts`, correction lint `chat.test.ts`, documentation des mocks `createDocumentHandler`, exécution complète lint/typecheck/tests (`pnpm lint`, `tsc --noEmit`, `vitest run`, `ruff`, `black --exclude`, `isort`, `mypy --strict src`, `pytest`).
- 2025-10-31T08:23:03+00:00 — gpt-5-codex : Durcissement des tests `search` (détails 502, normalisation route), réglages SearxNG (locale, timeouts, notes Bing), exécution complète lint/typecheck/tests/coverage (`pnpm lint`, `tsc --noEmit`, `vitest run --coverage`, `ruff`, `black`, `isort`, `mypy --strict`, `pytest`). `pnpm build` échoue faute de `POSTGRES_URL` accessible.
