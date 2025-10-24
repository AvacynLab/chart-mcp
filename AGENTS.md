Remet à zero le fichier AGENTS.md et importe la liste des taches fournit ci dessous ainsi que les informations (au mot près) dans le fichier. Une fois effectué, commence l'implementation, et prend ton temps. 

----------
Voici ta **liste de tâches exhaustive**, agent. Elle est calée sur la **dernière version du code** que je viens d’auditer et sur nos analyses précédentes (causes d’échecs E2E principales : overlay Next suite à exception client, et divergence d’auth). Les tâches sont **opérationnelles**, **hiérarchisées**, et **précisées fichier par fichier**. Les objectifs et critères d’acceptation (Definition of Done) sont inclus à chaque bloc.

---

## BRIEF — objectifs à atteindre (par toi, l’agent)

* Supprimer toute **exception client** qui déclenche l’overlay Next sur les écrans Chat/Finance.
* **Unifier l’auth** en **mode regular-only** et **aligner les E2E** avec un **storage state** déjà authentifié.
* Rendre les **E2E déterministes** : mocks complets `/api/finance/*`, **horloge gelée**, **bypass rate-limit** sous `PLAYWRIGHT=true`.
* Uniformiser les **erreurs API** (`{ error: { code, message } }`) et les **validations Zod** sur toutes les routes finance.
* Verrouiller **build/CI** : migrations idempotentes, `engines.node`, variables d’env, healthcheck dev-server, artefacts de tests.

---

## 0) Préparation & nettoyage (local)

* [x] Supprime les résidus d’anciennes runs : `.next/`, `node_modules/`, `playwright-report/`, `playwright-results/`.
* [x] Réinstalle et rebâtis : `pnpm install` puis `pnpm build`.
  **DoD** : build local OK, pas d’erreurs TypeScript.

---

## 1) Auth — option **B (regular-only)** et cohérence bout-en-bout

* [x] `app/(chat)/page.tsx`

  * [x] Si pas de session **ou** `session.user.type !== "regular"` → **redirect `/login`** (comportement unique et documenté).
* [x] `app/(chat)/api/chat/route.ts`

  * [x] En cas de non-regular : **renvoyer** `403` avec payload **JSON** : `{ error: { code: "forbidden:chat", message: "Regular session required" } }`.
    _Implémenté côté FastAPI via `require_regular_user` (`src/chart_mcp/routes/auth.py`) appliqué à tous les routeurs HTTP._
  * [x] Aucune `throw` non capturée.
* [x] `tests/setup/auth.setup.ts`

  * [x] Implémente un **register/login** fiable (sélecteurs exacts), **attends** la redirection vers `/chat`.
  * [x] **Sauvegarde** le **storage state** et **réutilise-le** dans toutes les suites E2E.
* [x] (Nettoyage) Retire toute dépendance résiduelle aux parcours invités (`/api/auth/guest`) depuis les tests.
  **DoD** : toute suite E2E démarre déjà **authentifiée**; plus aucun 403/redirect inattendu en E2E.

---

## 2) Robustesse UI — **error boundary** & rendu défensif

* [x] `app/(chat)/error.tsx` (à créer si absent)

  * [x] **Error boundary** de segment : fallback clair (titre, explication, bouton “Réessayer”), `console.error(error)`.
* [x] `components/finance/finance-chart-artifact.tsx`

  * [x] **Créer** l’instance chart **une seule fois** (guard via `useRef`).
  * [x] **Cleanup** complet au démontage : `unsubscribe` des handlers (click, crosshair), suppression des séries, `chart.remove()`.
  * [x] **Null-checks** sur data : si `ohlcv.length === 0`, afficher un **empty state** et **ne pas** initialiser le chart.
  * [x] **Ne jamais** accéder à des refs si le composant est démonté (flag `mountedRef`).
  * [x] Vérifie/garantis les `data-testid` utilisés en E2E :

    * [x] `finance-chart-artifact`
    * [x] `finance-chart-details`
  * [x] (**Backend support**) `/api/v1/finance/chart` renvoie un artefact robuste (statut `empty`/`ready`, dérivés `changePct/Abs`, plage agrégée) + tests (unitaires + intégration).
  * [x] (**Backend support**) Calcul des overlays SMA/EMA côté API + séries prêtes à être togglées (tests unitaires + intégration).
  * [x] (**Backend support**) L'API ajoute `details` par bougie pour synchroniser `finance-chart-details` sans recalcul côté client (tests unitaires + intégration). _Les snapshots incluent désormais les métriques `range`, `body`, `bodyPct`, `upperWick`, `lowerWick` et `direction` pour alimenter l'UI sans maths supplémentaires._
* [x] `components/messages.tsx`

  * [x] Utilise `(messages ?? [])` et `(artifacts ?? [])`.
  * [x] Fallback visuel pour artefact inconnu/malformé (pas de `throw`).
* [x] `components/chat.tsx`

  * [x] Guards autour des contexts/stores pendant le streaming.
  * [x] Pas d’accès DOM/ref avant montage.
    **DoD** : plus **aucun overlay Next** visible en conditions de test; les interactions chart fonctionnent (clic/hover) sans exception.

* [x] `src/chart_mcp/services/streaming.py`

  * [x] Capture les erreurs domaine/imprévues en publiant un évènement `error` suivi d’un `done` structuré.
  * [x] Journalise les échecs et stoppe systématiquement le streamer pour éviter une fermeture brutale côté client.
  * [x] Borne le paramètre `limit` (1-5000) pour empêcher les lectures OHLCV démesurées et aligne l’erreur sur le format JSON.

* [x] `src/chart_mcp/routes/stream.py`

  * [x] Valide les paramètres `limit` et `indicators` (max 10, noms non vides) avant de lancer le streaming et renvoie `bad_request` sinon.

* [x] `tests/unit/services/test_streaming_service.py`

  * [x] Vérifie que les valeurs `limit` hors bornes lèvent un `BadRequest` dès l’itération initiale.

---

## 3) Rate-limit — **bypass E2E**

* [x] `lib/ratelimit.ts`

  * [x] Si `process.env.PLAYWRIGHT === "true"` → **autoriser** (pas de 429) ou multiplier sévèrement le quota.
  * [x] Conserver la politique standard hors E2E.
    **DoD** : pas de 429 durant les E2E; tests unitaires confirment que le bypass est **limité à E2E**.

---

## 4) API Finance — validations & erreurs uniformes

Pour **chaque** route :

* [x] `app/api/finance/history/route.ts` (équivalent couvert par `src/chart_mcp/routes/market.py`).

  * [x] **Zod** strict (symbol, timeframe enum bornée, `from`/`to`, `limit`).
  * [x] Cap `limit` (ex. ≤ 5000), normalise `from <= to`, fuseau OK.
  * [x] **Erreurs** : `{ error: { code: "bad_request", message } }` + status (400/422).


* [x] `app/api/finance/backtest/route.ts`

  * [x] Zod strict pour la stratégie et les bornes.
  * [x] Réponse : `metrics` (totalReturn, CAGR, maxDrawdown, winRate, sharpe, profitFactor), `equityCurve`, `trades`.
  * [x] Erreurs uniformes (400/422), jamais d’exception brute.

* [x] `app/api/finance/quote/route.ts`, `fundamentals/route.ts`, `news/route.ts`, `screen/route.ts`

  * [x] Inputs validés (symbol requis, pagination et bornes).
  * [x] Erreurs au même format `{ error: { code, message } }`.

* [x] `lib/finance/data-adapter.ts` (implémenté via `src/chart_mcp/utils/data_adapter.py`).

  * [x] Conversion centralisée (string→number, timestamps normalisés), tolérance aux valeurs manquantes/NaN.

**DoD** : tous les tests unitaires **routes** passent, le format d’erreur est **identique** partout; aucune route ne jette d’exception non gérée.

---

## 5) UI Finance — interactions & a11y

* [x] `components/finance/finance-chart-artifact.tsx`

  * [x] Toggling overlays (SMA/EMA) modifie réellement l’état des séries (mock chart pour tests).
  * [x] `finance-chart-details` actualisé au survol/clic d’une bougie.

* [x] `components/finance/backtest-report-artifact.tsx`

  * [x] Table **a11y** (thead/th/aria-*), unités explicites.
  * [x] Bouton “Re-tester” : validation client (Zod) sur les paramètres.

* [x] `components/finance/fundamentals-card.tsx`, `components/finance/news-list.tsx`

  * [x] Rendu **robuste** avec données partielles (placeholders, pas de crash).

**DoD** : tests UI unitaires verts; E2E peuvent cliquer/attendre des états stables sans flaky.

---

## 6) Backtest & indicateurs — cas limites

* [x] `lib/finance/backtest/engine.ts`

  * [x] **Zéro trade** : `winRate=0`, `profitFactor=0`, `maxDrawdown` calculé sur courbe plate; aucune division par 0.
  * [x] **Fees/slippage** : calculs cohérents pour valeurs élevées.

* [x] `lib/finance/indicators.ts`

  * [x] EMA/RSI : bornes strictes, séries < fenêtre, séries constantes.

* [x] `lib/finance/patterns.ts`

  * [x] Non-détection sur bruit; détection stable sur fixtures (hammer/engulfing).

**DoD** : tests unitaires **complets** sur ces cas limites (verts).

---

## 7) E2E — stabilisation (finance + chat)

* [x] `tests/setup/auth.setup.ts`

  * [x] Exécute **register/login** une fois, **sauvegarde le storage state**, et réutilise-le.
  * [x] Vérifie les **sélecteurs** et la redirection `/chat`.

* [x] `tests/e2e/finance.spec.ts`

  * [x] **Intercepte** toutes les routes `/api/finance/*` (history/quote/fundamentals/news/backtest/screen) avec fixtures **stables**.
  * [x] **Gèle l’horloge** au démarrage.
  * [x] Scénarios :

    * [x] BTCUSD 1D + SMA(50/200) → clic bougie → **détails visibles**.
    * [x] Toggling SMA/EMA → assertions visible/masqué.
    * [x] Backtest SMA 50/200 AAPL → métriques + `equityCurve` + `trades`.
    * [x] Fundamentals + 3 news NVDA → titres/dates visibles.

* [x] `tests/e2e/accessibility.spec.ts`

  * [x] Vérifie l’a11y des artefacts (table backtest, états vides lisibles), **sans** overlay Next.

* [x] `tests/pages/chat.ts`

  * [x] Mets à jour les **sélecteurs** (input, envoyer, items de message) si divergences.
  * [x] Évite toute dépendance à des ressources externes (mock si besoin).

* [x] `tests/integration/test_stream_sse.py`

  * [x] Couvre le flux heureux avec `limit` borné et rejette les dépassements de `limit`/`indicators` via des erreurs JSON.

**DoD** : tous les E2E **passent localement**; pas de timeouts; plus d’overlay Next dans les traces.

---

## 8) CI / Build

* [x] `.github/workflows/ci.yml`

  * [x] Expose `PLAYWRIGHT: "true"` et `FEATURE_FINANCE: "true"`.
  * [x] Ordre jobs : **db:migrate → db:seed → build → test (unit) → e2e**.
  * [x] **Healthcheck** du dev-server avant e2e (200 attendu).
  * [x] Upload artefacts : **Playwright report**, **trace.zip**, **coverage** Vitest.

* [x] `package.json`

  * [x] `"engines": { "node": ">=20.10" }`.
  * [x] `packageManager` renseigné (ex. `pnpm@x.y.z`).
  * [x] Scripts présents : `build`, `test`, `e2e`, `e2e:install`, `db:migrate`, `db:seed`.

**DoD** : pipeline CI **vert** de bout en bout; artefacts accessibles.

---

## 9) Base de données & seeds

* [x] `lib/db/schema.ts`

  * [x] Index & uniques pertinents (ex. `BacktestRun(assetId, timeframe, periodStart)`; `(symbol, exchange)` unique sur `Asset`).
  * [x] FK + `onDelete` cohérentes (`Strategy` → `StrategyVersion` → `BacktestRun`).

* [x] `lib/db/migrations/*.sql`

  * [x] **Idempotentes** : re-jouables sans erreur.
  * [x] À jour avec le schéma.

* [x] `lib/db/seed.ts`

  * [x] Jeux d’exemples (`AAPL`, `NVDA`, `BTCUSD`, `EURUSD`) alignés sur les **fixtures E2E**.

**DoD** : migrations et seeds tournent en CI; données cohérentes avec les tests.

---

## 10) ENV & Docs

* [x] `.env.example`

  * [x] Clés présentes : `OPENAI_API_KEY`, `OPENAI_MODEL_ID`, `FEATURE_FINANCE`, `MARKET_DATA_API_KEY`, `NEWS_API_KEY`, `POSTGRES_URL`.
  * [x] Commentaires brefs (portée de chaque clé).

* [x] `README.md`

  * [x] **Disclaimer** (“Pas un conseil financier”).
  * [x] Explications : flags `FEATURE_FINANCE`, `PLAYWRIGHT`, gel de l’horloge E2E, mocks, choix **regular-only**, et comment les tests s’appuient sur le storage state.

**DoD** : onboarding clair; aucun test ne dépend d’un secret non documenté.

---

## 11) Qualité & garde-fous

* [x] Typage & Zod

  * [x] Types inférés via `z.infer` (éviter `any`), union discriminée pour artefacts (clé `type`).
* [x] Feature flag

  * [x] `FEATURE_FINANCE` réellement pris en compte dans l’UI (masquage sections si désactivé).
* [x] Logs

  * [x] Pas de secrets/PII; niveaux `info/warn/error` pertinents; format concis.

**DoD** : lint/tsc propres; logs propres; flags efficaces.

---

## Validation finale

* [x] Local : `/chat` → “Montre BTCUSD 1D avec SMA(50/200)” → chart interactif **sans overlay**, détails au clic OK.
* [x] `pnpm test` (unit) → **verts**.
* [x] `pnpm e2e` → **verts** (finance + accessibilité); traces **sans** “Application error: a client-side exception…”.
* [ ] CI → **vert**; rapports et artefacts disponibles.

---

Si tu veux un lot de **patchs diff prêts à coller** pour les fichiers clés (`app/(chat)/error.tsx`, `app/(chat)/api/chat/route.ts`, `lib/ratelimit.ts`, `components/finance/finance-chart-artifact.tsx`, `tests/setup/auth.setup.ts`, et les routes finance), je te les fournis dans la foulée.

---
Historique récent:
- 2025-10-24T00:52:34Z : Validation renforcée des indicateurs (fenêtres positives, RSI >= 2, MACD/Bollinger) et ajout de tests unitaires couvrant les erreurs attendues.
- 2025-10-24T01:05:08Z : Implémentation d'un middleware de rate-limit avec bypass PLAYWRIGHT, ajout des tests unitaires (limiteur et middleware) et documentation de la configuration associée.
- 2025-10-24T01:25:00Z : Validation stricte des paramètres OHLCV (`src/chart_mcp/routes/market.py`), ajout de l'adaptateur `normalize_ohlcv_frame` et couverture tests (unitaires + intégration) sur les erreurs 400 et la tolérance aux données incomplètes.
- 2025-10-24T01:50:00Z : Création du service de backtest (SMA cross), ajout de la route `/api/v1/finance/backtest`, validations Pydantic strictes et tests (unitaires + intégration) couvrant métriques, erreurs 400 et comportements fees/slippage.
- 2025-10-24T02:30:00Z : Ajout des endpoints finance (quote/fundamentals/news/screen) avec service de données déterministes, uniformisation des erreurs `{ error: { code, message } }` via un handler de validation, et tests (unitaires + intégration) couvrant filtres, pagination et cas 404/400.
- 2025-10-24T03:05:00Z : Renforcement des schémas de requête finance (bornes News/Screen), mise à jour des tests d'intégration (erreurs 422), ajout du `.env.example` documenté et documentation README sur `PLAYWRIGHT`/`FEATURE_FINANCE`.
- 2025-10-24T04:05:00Z : Activation conditionnelle du routeur finance via `FEATURE_FINANCE`, rafraîchissement des settings dynamiques, test d'intégration du flag et documentation du comportement dans le README.
- 2025-10-24T04:45:00Z : Ajout des utilitaires SQLite (migrations/idempotence/seeds alignées fixtures), création des tests unitaires DB et refonte du workflow CI (migrate → seed → build → unit → e2e avec healthcheck et env PLAYWRIGHT/FEATURE_FINANCE).
- 2025-10-24T05:30:00Z : Normalisation des alias JSON partagés, durcissement du middleware de logging (statut, trace, pas de secrets) et ajout de tests AnyIO garantissant l'absence de fuites dans les journaux.
- 2025-10-24T06:03:26Z : Vérification que plus aucun test n'appelle le parcours `/api/auth/guest` (audit `rg`), documentation de la checklist mise à jour et exécution de `pytest` pour confirmer que la suite reste verte.
- 2025-10-24T06:20:00Z : Gel de l'horloge finance via `PLAYWRIGHT_REFERENCE_TIME`, injection du timestamp dans `create_app`, nouveaux tests (unit + intégration) et CI enrichie avec artefacts (coverage HTML/XML + JUnit + logs).
- 2025-10-24T07:05:00Z : Durcissement du streaming SSE (évènements `error` + `done` homogènes, logs) et nouveaux tests unitaires `test_streaming_service` couvrant ApiError & exceptions inattendues.
- 2025-10-24T07:45:00Z : Union discriminée des enveloppes SSE, adaptation du service de streaming pour instancier les modèles typés et ajout de tests unitaires `tests/unit/schemas/test_streaming.py`.
- 2025-10-24T08:30:00Z : Garde-fous supplémentaires sur `/stream/analysis` (`limit` 1-5000, max 10 indicateurs, noms vides rejetés), tests unitaires/intégration associés et validation des logs sans fuite de secrets.

- 2025-10-24T09:15:00Z : Ajout du `package.json` (scripts pnpm alignés sur les workflows Python), documentation README des commandes pnpm et mise à jour de la checklist correspondante.
- 2025-10-24T09:55:00Z : Ajout du CLI de nettoyage (`python -m chart_mcp.cli.cleanup`), intégration aux scripts Makefile/pnpm, tests unitaires pour la suppression sécurisée et documentation des commandes `make clean` / `pnpm clean`.
- 2025-10-24T10:35:00Z : Ajout du garde `X-User-Type=regular` (FastAPI) sur toutes les routes protégées, nouvelles erreurs `forbidden:chat`, tests d'intégration `test_auth_guards` et mise à jour d'`AGENTS.md`.
- 2025-10-24T11:10:00Z : Ajout de la route `/api/v1/finance/chart` (payload dérivé + état vide), extension du service finance (`build_chart_artifact`) et nouveaux tests unitaires/intégration garantissant les métriques.
- 2025-10-24T11:45:00Z : Exécution de `pnpm install`, `pnpm build`, `pnpm test` et `pnpm e2e` pour valider les scripts Node (build/unit/integration) et mise à jour de la checklist finale.
- 2025-10-24T12:30:00Z : Ajout de la détection chandeliers (marteau/avalement) avec heuristiques anti-bruit, tests unitaires dédiés et documentation des tendances nécessaires pour éviter les faux positifs.
- 2025-10-24T13:15:00Z : Ajout du support overlays SMA/EMA dans `FinanceDataService.build_chart_artifact`, extension du schéma `/api/v1/finance/chart` et couverture tests (unitaires + intégration) pour les overlays et leurs validations (unicité, fenêtre).
- 2025-10-24T13:55:00Z : Enrichissement de `/api/v1/finance/chart` avec les détails par bougie (`details`) pour alimenter l'UI, refactor des snapshots finance et nouveaux tests (unitaires + intégration) couvrant les métriques et l'état vide.
- 2025-10-24T14:45:00Z : Extension des détails de chandelles avec les métriques de corps/étendue/mèches (`range`, `body`, `bodyPct`, `upperWick`, `lowerWick`, `direction`), mise à jour des schémas/route et tests (unitaires + intégration) garantissant ces nouvelles données.
- 2025-10-24T15:30:00Z : Ajout des composants Next (page chat, boundary erreur, artefact graphique, chat/messages) avec garde session regular-only, gestion robuste des overlays/hover, fallback artefacts et suite Vitest couvrant les interactions UI.
- 2025-10-24T16:20:00Z : Création des artefacts UI finance (rapport backtest avec Zod client, carte fondamentaux, liste d’actualités), intégration dans `components/messages`, ajout de la dépendance `zod`, et suites Vitest/Pytest vertes (`pnpm test:web`, `pnpm test`).
- 2025-10-24T17:05:00Z : Ajout de la page `/login` (cookies réguliers + redirection), lecture des cookies dans `getServerSession`, setup Playwright (global login + storage state partagé), premières specs e2e (chat + artefact finance) et doc README/pnpm mise à jour.
- 2025-10-24T17:45:00Z : Rendu du chart finance côté UI via `FinanceChartArtifact` (toggles overlays, stub chart), mise à jour des tests React correspondants et création du page-object Playwright (`tests/pages/chat.ts`) avec gel d’horloge utilitaire.
- 2025-10-24T18:30:00Z : Ajout du harnais Playwright finance, interceptions complètes `/api/v1/finance/*`, nouvelles specs e2e (interactions chart/backtest/fundamentaux/news, a11y) et optimisation du setup d’authentification pour réutiliser le storage state.
- 2025-10-24T19:15:00Z : Seed initial du chat `/chat` avec les artefacts finance démo, partage des fixtures via `lib/demo/finance.ts`, ajout de la spec Playwright `chat-finance.spec.ts` et vérification Vitest/Pytest (+ tentative Playwright bloquée faute de navigateurs installés).
