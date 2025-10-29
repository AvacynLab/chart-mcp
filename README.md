# chart-mcp (alpha)

![CI](https://github.com/your-org/chart-mcp/actions/workflows/ci.yml/badge.svg)

`chart-mcp` assemble un backend FastAPI, un serveur MCP (Model Context Protocol),
un frontend Next.js basé sur le template **Vercel AI Chatbot** et une instance
**SearxNG** autohébergée pour produire un copilote d’analyse crypto. Le projet
diffuse les étapes d’analyse technique via SSE et propose deux artefacts
spécifiques :

* `finance` — pipeline temps réel (OHLCV, indicateurs, niveaux, patterns et
  résumé tokenisé).
* `search` — agrégation des dépêches et documents issus de SearxNG.

⚠️ Alpha : l’analyse restituée est pédagogique. Aucune recommandation
d’investissement n’est fournie.

## Architecture

| Composant | Rôle principal |
| --- | --- |
| **FastAPI (src/chart_mcp)** | Routes REST sécurisées par jeton (`/api/v1/*`), SSE `/stream/analysis`, exposition MCP stdio. |
| **Services Python** | Connecteurs CCXT, calculs d’indicateurs, détection supports/résistances, patterns chartistes, résumé LLM tokenisé, client SearxNG. |
| **SSE utils** | `chart_mcp/utils/sse.py` gère les entêtes, heartbeats, annulation et sérialisation des événements finance. |
| **SearxNG (docker/searxng)** | Service Dockerisé utilisé par le routeur `/api/v1/search` et le tool MCP `web_search`. |
| **Frontend (`frontend/ai-chatbot`)** | Copie stricte du template Vercel AI Chatbot étendue avec artefacts `finance` et `search`, réutilisant les composants chart internes. |
| **CI GitHub Actions** | Pipeline séquentiel `lint → typecheck → tests → build → e2e` couvrant Python et Node. |

## Environnement de développement

### Pré-requis

* Python 3.11 ou 3.12
* Node.js 20 + `pnpm`
* Docker / Docker Compose (pour SearxNG et exécution conteneurisée)

### Backend (FastAPI + MCP)

```bash
make setup              # installe les dépendances Python
make dev                # lance uvicorn en mode hot-reload sur http://localhost:8000
```

### SearxNG auto-hébergé

```bash
docker compose -f docker/docker-compose.yml up searxng
# SearxNG écoute ensuite sur http://localhost:8080
```

### Frontend Vercel AI Chatbot

```bash
cd frontend/ai-chatbot
pnpm install
pnpm dev                # http://localhost:3000 (utilise l’API MCP locale)
```

## Variables d’environnement

Copiez les fichiers `.env.example` (racine et `frontend/ai-chatbot/`) puis
adaptez les valeurs. Les variables critiques côté backend :

| Variable | Description |
| --- | --- |
| `API_TOKEN` | Jeton Bearer requis pour toutes les routes protégées et le flux SSE. |
| `ALLOWED_ORIGINS` | Origines CORS autorisées (séparateur `,`). Obligatoire en production. |
| `EXCHANGE` | Exchange CCXT utilisé pour l’OHLCV (`binance` par défaut). |
| `OHLC_CACHE_TTL_SECONDS` / `OHLC_CACHE_MAX_ENTRIES` | Paramètres du cache OHLCV en mémoire. |
| `FEATURE_FINANCE` | Active/désactive les routes finance optionnelles. |
| `SEARXNG_BASE_URL` | URL interne de l’instance SearxNG (ex. `http://searxng:8080`). |
| `SEARXNG_TIMEOUT` | Timeout (secondes) des requêtes SearxNG. |
| `RATE_LIMIT_PER_MINUTE` | Quota appliqué par le middleware de rate limiting. |

Côté frontend (`frontend/ai-chatbot/.env.example`) :

| Variable | Description |
| --- | --- |
| `MCP_API_BASE` | Base URL du backend (ex. `http://localhost:8000`). |
| `MCP_API_TOKEN` | Jeton Bearer à réutiliser côté navigateur. |
| `MCP_SESSION_USER` | Valeur envoyée dans `X-Session-User` pour les appels artefacts. |

## Appels API utiles

Les routes REST sont documentées via Swagger (`/docs`). Rappels `curl` :

```bash
# OHLCV
curl -H "Authorization: Bearer $API_TOKEN" \
     -H "X-Session-User: regular" \
     "http://localhost:8000/api/v1/market/ohlcv?symbol=BTCUSDT&timeframe=1h&limit=500"

# Indicateurs
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
     -H "X-Session-User: regular" \
     -H "Content-Type: application/json" \
     -d '{"symbol":"BTCUSDT","timeframe":"1h","indicator":{"name":"ema","params":{"window":21}},"limit":200}' \
     http://localhost:8000/api/v1/indicators/compute

# Supports/Résistances
curl -H "Authorization: Bearer $API_TOKEN" \
     -H "X-Session-User: regular" \
     "http://localhost:8000/api/v1/levels?symbol=BTCUSDT&timeframe=4h&limit=500&max=5"

# Patterns chartistes
curl -H "Authorization: Bearer $API_TOKEN" \
     -H "X-Session-User: regular" \
     "http://localhost:8000/api/v1/patterns?symbol=BTC/USDT&timeframe=1h&limit=500"

# Synthèse agrégée
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
     -H "X-Session-User: regular" \
     -H "Content-Type: application/json" \
     -d '{"symbol":"BTCUSDT","timeframe":"1h","include_levels":true,"include_patterns":true}' \
     http://localhost:8000/api/v1/analysis/summary

# Recherche SearxNG
curl -H "Authorization: Bearer $API_TOKEN" \
     -H "X-Session-User: regular" \
     "http://localhost:8000/api/v1/search?q=bitcoin%20etf&categories=news,science"

# Metrics Prometheus
curl http://localhost:8000/metrics
```

## Consommer le flux SSE finance

```ts
import { fetchEventSource } from "@microsoft/fetch-event-source";

const controller = new AbortController();
await fetchEventSource("http://localhost:8000/stream/analysis?symbol=BTCUSDT&timeframe=1h", {
  headers: {
    Authorization: `Bearer ${process.env.MCP_API_TOKEN}`,
    "X-Session-User": "regular",
  },
  signal: controller.signal,
  onmessage(message) {
    if (!message.event) return;
    const payload = JSON.parse(message.data);
    switch (message.event) {
      case "token":
        appendToken(payload.text);
        break;
      case "ohlcv":
        updateChart(payload.candles);
        break;
      case "done":
        controller.abort();
        break;
    }
  },
});
```

Les entêtes envoyés par le backend garantissent l’absence de buffering :

```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

## Tests & CI

Tous les jobs sont déclarés dans `.github/workflows/ci.yml` et s’exécutent en
pipeline strict.

| Étape | Commandes locales |
| --- | --- |
| Lint Python | `ruff check .`, `black --check src tests`, `isort --check-only src tests` |
| Typage Python | `mypy src` |
| Tests backend | `pytest -q` (avec couverture générée dans `coverage.xml`) |
| Build Docker | `docker build -f docker/Dockerfile .` (healthcheck intégré) |
| Front typecheck | `cd frontend/ai-chatbot && pnpm exec tsc --noEmit` |
| Tests frontend | `pnpm --filter ai-chatbot exec vitest run` + `pnpm exec playwright test` |

Les artefacts JUnit/couverture sont publiés par la CI pour faciliter le suivi.

## Sécurité & bonnes pratiques

* Ne jamais committer de `.env` ou de secrets — seuls les fichiers `.env.example`
  sont versionnés.
* Configurer `ALLOWED_ORIGINS` explicitement en production ; l’application
  refuse de démarrer si la liste est vide hors mode Playwright.
* Les routes critiques exigent `Authorization: Bearer <API_TOKEN>` et
  `X-Session-User`.
* Le serveur MCP (`python -m chart_mcp.mcp_main`) enregistre les tools
  `create_finance_artifact`, `create_search_artifact`, `web_search`, `market`
  etc. pour une intégration symétrique avec le frontend.
* Les services enregistrent métriques et journaux structurés (`/metrics`).

## Packaging & déploiement

```bash
docker compose -f docker/docker-compose.yml up --build
# -> lance l’API FastAPI (port 8000) et SearxNG (port 8080)
```

Le Dockerfile inclut un `HEALTHCHECK` appelant `docker/healthcheck.py`, ce qui
permet à Kubernetes, Docker Compose ou la CI de valider la disponibilité de
l’API. Pour déployer le frontend Next.js, suivez les instructions Vercel (ou
déployez l’app en mode Node.js standard) en pointant `MCP_API_BASE` vers votre
API sécurisée.

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
