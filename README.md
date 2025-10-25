# chart-mcp (alpha)

`chart-mcp` est un serveur Market Charting Pipeline (MCP) en Python dédié aux marchés **crypto** pour l'alpha. Il expose :

- une API FastAPI sécurisée par token pour récupérer des données de marché et calculer des indicateurs, niveaux et figures,
- un flux SSE (Server-Sent Events) pour suivre en direct les étapes de l'analyse et le texte généré,
- un serveur MCP compatible avec les outils du protocole Model Context Protocol.

⚠️ Alpha : l'analyse générée est **pédagogique** uniquement. Aucune recommandation d'achat ou de vente n'est fournie.

## Prise en main rapide

### Prérequis

- Python 3.11+
- `pip` ou `uv`
- Docker (optionnel pour l'exécution conteneurisée)

### Installation (environnement local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Copiez `.env.example` vers `.env` et ajustez les valeurs (token API, exchange, options CORS, etc.).
Les variables principales sont documentées ci-dessous :

| Clef | Description |
| --- | --- |
| `API_TOKEN` | Jeton obligatoire pour authentifier les requêtes HTTP. |
| `EXCHANGE` | Identifiant de l'exchange source pour les données OHLCV. |
| `ALLOWED_ORIGINS` | Liste séparée par des virgules des origines autorisées en CORS. |
| `PLAYWRIGHT` | Active le mode tests déterministe (bypass du rate-limit et fixtures stables). |
| `FEATURE_FINANCE` | Active les endpoints finance (quotes, news, backtests...). |
| `OPENAI_API_KEY` / `OPENAI_MODEL_ID` | Identifiants pour un fournisseur OpenAI *(optionnel / futur)*. |
| `MARKET_DATA_API_KEY` | Clé API pour un agrégateur de données marché externe *(optionnel)*. |
| `NEWS_API_KEY` | Clé API pour les dépêches financières externes *(optionnel)*. |
| `POSTGRES_URL` | Chaîne de connexion PostgreSQL *(futur, réservée aux migrations complètes)*. |

> ℹ️ `PLAYWRIGHT=true` est utilisé dans la suite de tests pour geler l'horloge, bypasser le rate limit
> et fournir des jeux de données entièrement mocks.

Lorsque `FEATURE_FINANCE=false`, le serveur ne monte pas les routes `/api/v1/finance/*` et ignore
la configuration associée au service de données financières. Cette bascule permet de déployer une
instance plus légère centrée sur l'OHLCV de base.

### Lancement du serveur

```bash
uvicorn chart_mcp.app:app --host 0.0.0.0 --port 8000 --reload
```

### Exemple : récupérer de l'OHLCV

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/market/ohlcv?symbol=BTCUSDT&timeframe=1h&limit=500"

curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/market/ohlcv?symbol=BTC/USDT&timeframe=1h&limit=500"
```

Réponse (extrait) :

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

> ℹ️ Le provider normalise systématiquement les symboles vers le format `BASE/QUOTE`.

### Exemple : calculer un indicateur

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "http://localhost:8000/api/v1/indicators/compute" \
  -d '{
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicator": {
          "name": "ema",
          "params": {"window": 21}
        },
        "limit": 200
      }'
```

Réponse (extrait) :

```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "indicator": "ema",
  "rows": [
    {"ts": 1730000000, "value": 35080.42}
  ]
}
```

### Exemple : supports/résistances

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/levels?symbol=BTCUSDT&timeframe=4h&limit=500&max=5"
```

Réponse (extrait) :

```json
{
  "symbol": "BTC/USDT",
  "timeframe": "4h",
  "levels": [
    {
      "price": 34850.0,
      "strength": 0.6,
      "kind": "support",
      "ts_range": {"start_ts": 1729990000, "end_ts": 1730000000}
    }
  ]
}
```

### Exemple : détection de figures chartistes

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/patterns?symbol=BTC/USDT&timeframe=1h&limit=500"
```

Réponse (extrait) :

```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "patterns": [
    {
      "name": "channel",
      "score": 0.7,
      "confidence": 0.52,
      "start_ts": 1729985000,
      "end_ts": 1730000000,
      "points": [
        [1729985000, 34750.0],
        [1730000000, 35010.0]
      ]
    }
  ]
}
```

### Exemple : flux SSE de synthèse d'analyse

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  -N "http://localhost:8000/stream/analysis?symbol=BTCUSDT&timeframe=1h"
```

Sortie (troncature) :

```
event: tool_start
data: {"tool":"get_crypto_data","symbol":"BTCUSDT","timeframe":"1h"}

...

event: token
data: {"text":"Le prix reste au-dessus de l'EMA 50, ce qui suggère une dynamique haussière courte."}

event: done
data: {}
```

Le serveur émet des évènements SSE avec les en-têtes suivants :

```text
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

Chaque message est encodé au format NDJSON et suit la structure `event: <type>`, `data: <payload>`.

## Serveur MCP

Le projet embarque désormais un serveur Model Context Protocol complet :

- **Installation** : `pip install -r requirements.txt` installe `fastmcp` et ses dépendances.
- **Lancement** : `make mcp-run` démarre le serveur en mode stdio (idéal pour un runner MCP ou un client CLI).
- **Authentification** : aucune authentification spécifique n'est requise sur la couche MCP (elle est gérée côté client/runner si nécessaire).

### Outils exposés

| Tool | Entrées principales | Sortie |
| --- | --- | --- |
| `get_crypto_data` | `symbol`, `timeframe`, `limit`, bornes temporelles optionnelles | Liste d'OHLCV sérialisés `{ts,o,h,l,c,v}` |
| `compute_indicator` | `symbol`, `timeframe`, `indicator` (`name` + `params`), `limit` | Liste `{ts, ...valeurs indicateur...}` sans `NaN` |
| `identify_support_resistance` | `symbol`, `timeframe` | Liste de niveaux `{price, kind, strength, ts_range}` |
| `detect_chart_patterns` | `symbol`, `timeframe` | Liste de patterns `{name, score, confidence, points}` |
| `generate_analysis_summary` | `symbol`, `timeframe`, indicateurs optionnels | Chaîne courte résumant tendances, niveaux et patterns |

### Exemple d'appel (client Python `fastmcp`)

```bash
python - <<'PY'
import asyncio
from fastmcp.client import Client, StdioTransport


async def main() -> None:
    client = Client(transport=StdioTransport(cmd=["python", "-m", "chart_mcp.mcp_main"]))
    await client.start()
    try:
        result = await client.call_tool(
            "get_crypto_data",
            {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 5},
        )
        print(result.data or result.content)
    finally:
        await client.close()


asyncio.run(main())
PY
```

Le client reçoit un dictionnaire JSON directement sérialisable (aucun objet Pandas n'est exposé).

### Scripts utiles

```
make setup        # installer les dépendances
make dev          # lancer le serveur en local avec rechargement
make lint         # exécuter ruff
make format       # exécuter black + isort
make typecheck    # exécuter mypy
make test         # lancer la suite de tests avec couverture
make clean        # supprimer .next/, node_modules/ et artefacts Playwright
```

### Scripts pnpm (optionnels)

Un fichier `package.json` est fourni pour aligner la checklist produit sur les environnements
Node/Playwright. Les scripts encapsulent les commandes Python existantes :

```
pnpm clean        # supprime .next/, node_modules/ et les artefacts Playwright
pnpm build        # compile les modules Python pour détecter les erreurs de syntaxe
pnpm test         # lance pytest sur l'ensemble du projet
pnpm e2e          # exécute les tests d'intégration API (mocks déterministes)
pnpm e2e:ui       # lance Playwright avec un storage state régulier pré-généré
pnpm db:migrate   # applique les migrations SQLite idempotentes
pnpm db:seed      # injecte les fixtures finance cohérentes avec les tests
```

> ℹ️ `pnpm e2e:install` affiche simplement un rappel. La nouvelle suite
> `pnpm e2e:ui` repose sur un setup Playwright qui visite `/login`, crée un
> cookie `sessionType=regular` puis réutilise le storage state pour l'ensemble
> des scénarios UI.

## Docker

```bash
make docker-build
make docker-run
```

Un `HEALTHCHECK` interroge `GET /health` pour valider le démarrage.

## Tests & qualité

- `pytest --cov=src --cov-report=xml`
- `ruff`, `black`, `isort`
- `mypy src/`

Les tests d'intégration consomment un `FinanceDataService` déterministe et activent
`PLAYWRIGHT=true` pour reproduire les conditions E2E (storage state déjà authentifié
et absence de rate-limit aléatoire).

## Limitations alpha

- Données crypto uniquement (pas de support actions ou forex pour le moment).
- Synthèse IA basée sur une heuristique pédagogique, jamais prescriptive.
- Détection de patterns basique (channeaux, triangles, chandeliers simples).

## Licence

MIT
