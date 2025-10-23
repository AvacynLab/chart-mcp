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

### Lancement du serveur

```bash
uvicorn chart_mcp.app:app --host 0.0.0.0 --port 8000 --reload
```

### Exemple : récupérer de l'OHLCV

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/market/ohlcv?symbol=BTCUSDT&timeframe=1h&limit=500"
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

### Scripts utiles

```
make setup        # installer les dépendances
make dev          # lancer le serveur en local avec rechargement
make lint         # exécuter ruff
make format       # exécuter black + isort
make typecheck    # exécuter mypy
make test         # lancer la suite de tests avec couverture
```

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

## Limitations alpha

- Données crypto uniquement
- Synthèse IA basée sur une heuristique, non prescriptive
- Indicateurs et patterns basiques

## Licence

MIT
