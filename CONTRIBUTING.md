# Contribuer à chart-mcp

Merci de votre intérêt pour l'alpha de `chart-mcp` !

## Préparer son environnement

1. Créez un environnement virtuel (`python -m venv .venv`).
2. Activez-le et installez les dépendances : `pip install -r requirements.txt`.
3. Copiez `.env.example` en `.env` et configurez au minimum `API_TOKEN`. Les autres clefs documentées dans le fichier couvrent l'exchange par défaut, les origines autorisées et le rythme des heartbeats SSE.
4. Passez en revue toutes les variables disponibles dans `.env.example` (p. ex. `STREAM_HEARTBEAT_MS`, `LLM_MODEL`, `RATE_LIMIT_PER_MINUTE`) afin d'adapter l'environnement à vos besoins locaux avant de lancer les tests.

## Règles de qualité

- `ruff`, `black`, `isort` doivent être exécutés avant chaque commit.
- `mypy src/` ne doit remonter aucun avertissement.
- `pytest --cov=src --cov-report=xml` doit afficher une couverture ≥ 80 %.

## Process de contribution

1. Créez une branche.
2. Implémentez vos changements en ajoutant commentaires et documentation.
3. Ajoutez ou mettez à jour les tests, puis assurez-vous qu'ils passent tous.
4. Ouvrez une Pull Request en décrivant vos modifications et la méthode de test.

### Raccourcis Makefile

Plusieurs cibles accélèrent les vérifications locales :

| Commande | Description |
| --- | --- |
| `make format-check` | Vérifie `black` et `isort` en mode lecture seule sur `src` et `tests`. |
| `make typecheck-strict` | Lance `mypy` sur le dossier `src`. |
| `make mcp-run` | Démarre le serveur MCP en stdio (`python -m chart_mcp.mcp_main`). |

Consultez également `.env.example` pour ajuster votre configuration avant d'exécuter ces cibles.

Merci 💜
