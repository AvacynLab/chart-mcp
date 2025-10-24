# Contribuer à chart-mcp

Merci de votre intérêt pour l'alpha de `chart-mcp` !

## Préparer son environnement

1. Créez un environnement virtuel (`python -m venv .venv`).
2. Activez-le et installez les dépendances : `pip install -r requirements.txt`.
3. Copiez `.env.example` en `.env` et configurez au minimum `API_TOKEN`. Les autres clefs documentées dans le fichier couvrent l'exchange par défaut, les origines autorisées et le rythme des heartbeats SSE.

## Règles de qualité

- `ruff`, `black`, `isort` doivent être exécutés avant chaque commit.
- `mypy src/` ne doit remonter aucun avertissement.
- `pytest --cov=src --cov-report=xml` doit afficher une couverture ≥ 80 %.

## Process de contribution

1. Créez une branche.
2. Implémentez vos changements en ajoutant commentaires et documentation.
3. Ajoutez ou mettez à jour les tests, puis assurez-vous qu'ils passent tous.
4. Ouvrez une Pull Request en décrivant vos modifications et la méthode de test.

Merci 💜
