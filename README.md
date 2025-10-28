# chart-mcp (alpha)

![CI](https://github.com/your-org/chart-mcp/actions/workflows/ci.yml/badge.svg)

`chart-mcp` est un serveur Market Charting Pipeline (MCP) en Python dédié aux marchés **crypto** pour l'alpha. Il expose :

- une API FastAPI sécurisée par token pour récupérer des données de marché et calculer indicateurs, niveaux et figures,
- un flux SSE (Server-Sent Events) pour suivre en direct les étapes de l'analyse et le texte généré,
- un serveur MCP (Model Context Protocol) pour intégrer ces outils dans des agents IA,
- une intégration SearxNG autohébergée pour la veille news/docu crypto.

⚠️ Alpha : l'analyse générée est **pédagogique** uniquement. Aucune recommandation d'achat ou de vente n'est fournie.

## Architecture

| Composant | Rôle |
| --- | --- |
| **FastAPI** | Expose les routes REST (market, indicateurs, niveaux, patterns, analyse, finance, recherche) et gère l'authentification Bearer + `X-Session-User`. |
| **Services Python** | Implémentent l'accès CCXT, les indicateurs (SMA/EMA/RSI/MACD/Bollinger), la détection S/R et figures chartistes, ainsi que la génération IA tokenisée. |
| **SSE** | Route `/stream/analysis` diffusant `heartbeat`, `step:start`, `step:end`, `token`, `result_partial` et `done`. |
| **MCP (stdio)** | Serveur `python -m chart_mcp.mcp_main` exposant les mêmes outils aux agents compatibles Model Context Protocol. |
| **SearxNG** | Service Docker optionnel accessible via `/api/v1/search` et le tool MCP `web_search`. |
| **Frontend Next.js** | Page `/chart` affichant Lightweight Charts et consommant le flux SSE + les endpoints REST pour appliquer les overlays en direct. |

## Prise en main rapide

### Prérequis

- Python 3.11 ou 3.12
- `pip` ou `uv`
- Docker (optionnel pour l'exécution conteneurisée)

### Installation (environnement local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Copiez `.env.example` vers `.env` et ajustez les valeurs (token API, exchange, options CORS, etc.). Les variables principales :

| Clef | Description |
| --- | --- |
| `API_TOKEN` | Jeton obligatoire pour authentifier les requêtes HTTP. |
| `EXCHANGE` | Identifiant de l'exchange source pour les données OHLCV. |
| `OHLC_CACHE_TTL_SECONDS` | Durée de vie du cache OHLCV en mémoire (``0`` = désactivé). |
| `OHLC_CACHE_MAX_ENTRIES` | Nombre maximum d'entrées conservées dans le cache OHLCV. |
| `ALLOWED_ORIGINS` | Liste séparée par des virgules des origines autorisées en CORS. |
| `NEXT_PUBLIC_API_BASE_URL` | Origine HTTP utilisée par le front Next.js pour joindre l'API (vide = même domaine). |
| `NEXT_PUBLIC_API_TOKEN` | Jeton Bearer injecté côté front pour appeler les routes protégées. |
| `PLAYWRIGHT` | Active le mode tests déterministe (bypass du rate-limit et fixtures stables). |
| `FEATURE_FINANCE` | Active les endpoints finance (quotes, news, backtests...). |
| `SEARXNG_BASE_URL` | URL interne vers l'instance SearxNG conteneurisée. |
| `OPENAI_API_KEY` / `OPENAI_MODEL_ID` | Identifiants pour un fournisseur OpenAI *(optionnel / futur)*. |
| `MARKET_DATA_API_KEY` | Clé API pour un agrégateur de données marché externe *(optionnel)*. |
| `NEWS_API_KEY` | Clé API pour les dépêches financières externes *(optionnel)*. |
| `POSTGRES_URL` | Chaîne de connexion PostgreSQL *(futur, réservée aux migrations complètes)*. |

> ℹ️ `PLAYWRIGHT=true` est utilisé dans la suite de tests pour geler l'horloge, bypasser le rate limit et fournir des jeux de données entièrement mocks.

Lorsque `FEATURE_FINANCE=false`, le serveur ne monte pas les routes `/api/v1/finance/*`.

Le provider CCXT embarque un cache LRU en mémoire (activé par défaut) pour éviter
de solliciter l'exchange à chaque rafraîchissement UI. Ajustez
`OHLC_CACHE_TTL_SECONDS` et `OHLC_CACHE_MAX_ENTRIES` selon la fréquence de vos
requêtes ou fixez la durée de vie à ``0`` pour désactiver complètement la mise
en cache.

### Lancement du serveur

```bash
uvicorn chart_mcp.app:app --host 0.0.0.0 --port 8000 --reload
```

## API endpoints

Les routes principales sont documentées via OpenAPI/Swagger (voir `/docs`). Exemples `curl` :

### OHLCV — `/api/v1/market/ohlcv`

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  -H "X-Session-User: regular" \
  "http://localhost:8000/api/v1/market/ohlcv?symbol=BTCUSDT&timeframe=1h&limit=500"
```

### Indicateurs — `/api/v1/indicators/compute`

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  -H "X-Session-User: regular" \
  -H "Content-Type: application/json" \
  -X POST "http://localhost:8000/api/v1/indicators/compute" \
  -d '{
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicator": {"name": "ema", "params": {"window": 21}},
        "limit": 200
      }'
```

### Supports/Résistances — `/api/v1/levels`

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  -H "X-Session-User: regular" \
  "http://localhost:8000/api/v1/levels?symbol=BTCUSDT&timeframe=4h&limit=500&max=5"
```

### Figures chartistes — `/api/v1/patterns`

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  -H "X-Session-User: regular" \
  "http://localhost:8000/api/v1/patterns?symbol=BTC/USDT&timeframe=1h&limit=500"
```

### Synthèse complète — `/api/v1/analysis/summary`

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  -H "X-Session-User: regular" \
  -H "Content-Type: application/json" \
  -X POST "http://localhost:8000/api/v1/analysis/summary" \
  -d '{
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "include_levels": true,
        "include_patterns": true
      }'
```

### Recherche SearxNG — `/api/v1/search`

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  -H "X-Session-User: regular" \
  "http://localhost:8000/api/v1/search?q=bitcoin%20etf&categories=news,science"
```

### Metrics Prometheus — `/metrics`

```bash
curl http://localhost:8000/metrics
```

> Le endpoint est public afin de simplifier le branchement aux scrapers Prometheus.

## SSE client snippet

```ts
// Exemple TypeScript/Next.js minimal consommant le flux SSE d'analyse.
const source = new EventSource("http://localhost:8000/stream/analysis?symbol=BTCUSDT&timeframe=1h", {
  withCredentials: true,
});

source.addEventListener("step:end", (event) => {
  const payload = JSON.parse(event.data);
  console.log("Étape terminée", payload.step, payload.duration_ms);
});

source.addEventListener("token", (event) => {
  const { text } = JSON.parse(event.data);
  // Accumuler le texte tokenisé en direct côté UI.
  appendToLiveSummary(text);
});

source.addEventListener("done", () => {
  console.log("Analyse complète");
  source.close();
});
```

Les en-têtes SSE envoyés :

```text
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

## Frontend Next.js

La page `/chart` (répertoire `app/chart`) offre une visualisation complète pilotée par SSE :

- un formulaire permet de choisir le symbole, le timeframe et les indicateurs (EMA, RSI, MACD, Bollinger),
- la courbe principale repose sur **Lightweight Charts** avec surcharges dynamiques lorsque `step:end` est reçu,
- le texte IA est rendu token par token au fil des événements `token`.

### Lancer le front

```bash
pnpm install
pnpm dev
# => http://localhost:3000/chart (session régulière requise via /login)
```

Configurez `NEXT_PUBLIC_API_BASE_URL` et `NEXT_PUBLIC_API_TOKEN` pour pointer vers votre instance FastAPI (par défaut : même origine avec le token local). Les tests Vitest couvrent `components/chart` tandis que Playwright vérifie `/chart` via des routes mockées.

> ℹ️ La configuration Playwright démarre automatiquement `pnpm dev` et génère un état de session (cookies) avant chaque campagne de tests. Aucun démarrage manuel du front n'est requis.

Scripts additionnels utiles côté frontend :

```bash
# Analyse statique Next.js (ESLint)
pnpm lint

# Vérifie les types TypeScript sans émettre de fichiers
pnpm typecheck

# Lance les tests Vitest en mode surveillance
pnpm test:watch

# Démarre la suite e2e Playwright locale (le serveur Next.js est lancé automatiquement)
pnpm test:e2e
```

## Backend FastAPI

```bash
make setup
ALLOWED_ORIGINS=http://localhost:3000 make dev
```

- `make setup` installe les dépendances Python et inscrit le projet en mode editable.
- `ALLOWED_ORIGINS` doit contenir au moins une origine autorisée ; en local on
  peut réutiliser l'URL du front Next.js (`http://localhost:3000`).
- Le serveur s'exécute sur <http://localhost:8000> avec rechargement automatique.

## Serveur MCP

- **Installation** : `pip install -r requirements.txt` installe `fastmcp`.
- **Lancement** : `python -m chart_mcp.mcp_main` démarre le serveur MCP (stdio).
- **Documentation** : schémas d'entrées/sorties décrits dans `chart_mcp/schemas/mcp.py` et spécification <https://modelcontextprotocol.io>.

### Outils exposés

| Tool | Entrées principales | Sortie |
| --- | --- | --- |
| `get_crypto_data` | `symbol`, `timeframe`, `limit`, `start`, `end` | Liste d'OHLCV `{ts,o,h,l,c,v}` validée par Pydantic |
| `compute_indicator` | `symbol`, `timeframe`, `indicator`, `params`, `limit` | Liste `{ts, valeurs...}` sans `NaN` |
| `identify_support_resistance` | `symbol`, `timeframe`, `limit`, `params` | Niveaux `{price, kind, strength, strength_label, ts_range}` |
| `detect_chart_patterns` | `symbol`, `timeframe`, `limit`, `params` | Figures `{name, score, confidence, points, metadata}` |
| `generate_analysis_summary` | `payload` (`symbol`, `timeframe`, options) | Texte pédagogique + `disclaimer` |
| `web_search` | `query`, `categories`, `time_range` | Résultats SearxNG `{title, url, snippet, source, score}` |

### Exemple d'appel (client FastMCP)

```bash
fastmcp call python -m chart_mcp.mcp_main compute_indicator \
  '{"symbol": "BTCUSDT", "timeframe": "1h", "indicator": "ema", "limit": 100}'
```

## SearxNG

Le dépôt inclut un service SearxNG prêt à l'emploi :

- Fichiers : `docker/docker-compose.yml`, `docker/docker-compose.dev.yml`, `docker/searxng/settings.yml`.
- Variables environnement : `SEARXNG_BASE_URL`, `SEARXNG_SECRET` (non commité), `SEARXNG_TIMEOUT` (optionnelle).
- Démarrage :

```bash
docker compose -f docker/docker-compose.dev.yml up --build searxng
```

L'API FastAPI exposera `/api/v1/search` dès que `SEARXNG_BASE_URL` pointera vers `http://searxng:8080`. Le tool MCP `web_search` s'appuie sur la même configuration.

## Docker & Compose

```bash
make docker-build
make docker-run
```

- L'image embarque un `HEALTHCHECK` exécutant `docker/healthcheck.py` (requête `GET /health`).
- `docker-compose.dev.yml` lance `api` et `searxng` pour un stack complet.

## Tests & CI

Commandes locales :

```bash
make lint        # ruff
make typecheck   # mypy
make test        # pytest (unitaires + intégration + SSE)
```

Pipeline CI (défini dans `.github/workflows/ci.yml`, à créer) : `ruff` → `mypy` → `pytest` → build images Docker → tests frontend (Vitest/Playwright) → artefacts.

## Sécurité

- Authentification obligatoire : `Authorization: Bearer <API_TOKEN>` + `X-Session-User: regular`.
- CORS strict : origines définies via `ALLOWED_ORIGINS`. Aucun fallback en production.
- Secrets : `.env` non commité, variables sensibles injectées via environnement/Docker secrets.

## Matrice de versions

| Langage | Versions supportées |
| --- | --- |
| Python | 3.11, 3.12 |
| Node.js (frontend à venir) | 20.x |

## Limitations alpha

- Données crypto uniquement (pas de support actions ou forex pour le moment).
- Synthèse IA basée sur une heuristique pédagogique, jamais prescriptive.
- Détection de patterns basique (channels, triangles, chandeliers simples).

## Licence

MIT
