2025-10-25T05:24:31Z — 8865bdaf9f36eefb2146a03a750b5c10a355c4c3

# 🎯 Brief à l’agent (mise à jour)

* L’alpha crypto-only est presque bouclée : API sécurisée + SSE OK, indicateurs/levels/patterns OK, normalisation symboles OK, CI/Docker/Makefile OK.
* Il reste à :

  1. **exposer un vrai serveur MCP** (aujourd’hui on a des fonctions “tools” mais pas de serveur MCP réel),
  2. **émettre des événements `metric`** dans le stream SSE (le schéma les prévoit),
  3. boucler quelques **tests complémentaires** (MCP, feature flag finance off/on supplémentaire),
  4. retoucher la **doc** pour le run MCP.
* Invariants : jamais de conseil d’investissement ; couverture ≥ **80 %** ; 0 erreur lint/type ; Docker healthcheck OK.

---

# ✅ Tâches à cocher — uniquement ce qu’il reste à corriger/ajouter (par fichier)

## 1) Serveur MCP : implémentation réelle

### `requirements.txt`

* [x] **Ajouter** la dépendance MCP serveur :

  * [x] `fastmcp` (ou équivalent MCP server)
  * [x] épingler une version si possible (ex. `fastmcp==x.y.z`) pour CI stable.

### `src/chart_mcp/mcp_server.py`

> Les tools sont OK (JSON, symboles normalisés). Il manque l’**exposition via MCP**.

* [x] **Ne change pas** les fonctions existantes (contrats JSON OK).
* [x] **Ajouter** en bas du fichier une **fabrique d’enregistrement** MCP pour ces tools ; ou créer un module séparé `mcp_main.py` (voir ci-dessous) si tu préfères séparer “tools” et “serveur”.

### `src/chart_mcp/mcp_main.py` (nouveau)

* [x] **Créer** un entrypoint MCP qui :

  * [x] instancie le serveur MCP,
  * [x] **enregistre** les tools de `mcp_server.py` sous des noms stables,
  * [x] lance le serveur (stdio ou TCP/WS selon le lib choisi).
* [x] Exemple minimal (à **adapter** au lib retenu) :

  ```python
  from __future__ import annotations

  import asyncio
  # import du serveur MCP choisi, exemple fastmcp
  from fastmcp import MCPServer  # exemple: ajuste au vrai import

  from chart_mcp import mcp_server as tools

  def register(server: MCPServer) -> None:
      server.tool("get_crypto_data")(tools.get_crypto_data)
      server.tool("compute_indicator")(tools.compute_indicator)
      server.tool("identify_support_resistance")(tools.identify_support_resistance)
      server.tool("detect_chart_patterns")(tools.detect_chart_patterns)
      server.tool("generate_analysis_summary")(tools.generate_analysis_summary)

  async def main() -> None:
      server = MCPServer()
      register(server)
      # stdio mode: adapter à l’API du lib MCP choisi
      await server.serve_stdio()

  if __name__ == "__main__":
      asyncio.run(main())
  ```
* [x] Garantir une **gestion d’erreur** propre (trace → logs, réponse MCP normalisée).
* [x] **Ne pas** exposer d’objets non-sérialisables (tu retournes déjà des dict/list).

### `Makefile`

* [x] **Ajouter** :

  ```make
  mcp-run:
  python -m chart_mcp.mcp_main
  ```
* [x] Laisser les cibles existantes (elles sont correctes, tabs OK).

### `.github/workflows/ci.yml`

* [x] **Ajouter** un job rapide “**mcp-smoke**” (Python 3.11) qui :

  * [x] installe les deps + `fastmcp`,
  * [x] exécute `python -m chart_mcp.mcp_main` **en arrière-plan** (timeout court),
  * [x] lance un **smoke test** minimal (selon le transport :

    * stdio → importer `mcp_main.register` et vérifier que les tools sont enregistrables,
    * TCP/WS → `nc`/client MCP de test pour lister les tools si dispo),
  * [x] tue le process proprement.

### `README.md`

* [x] **Ajouter** une section **“Serveur MCP”** :

  * [x] Comment l’installer (mention `fastmcp`),
  * [x] Comment le **lancer** (`make mcp-run`),
  * [x] **Contrats** et **noms** des tools exposés,
  * [x] Exemple d’appel MCP (selon le client) & note “auth côté MCP : NA (géré au niveau client/runner)”.

### `tests/unit/mcp/test_server_runtime.py` (nouveau)

* [x] **Créer** un test unitaire qui :

  * [x] importe `mcp_main.register`,
  * [x] instancie un serveur **mock** du lib MCP,
  * [x] appelle `register(server)` et **vérifie** que la liste des tools contient :
    `get_crypto_data`, `compute_indicator`, `identify_support_resistance`, `detect_chart_patterns`, `generate_analysis_summary`.
  * [x] **Skip** si le lib MCP n’est pas importable (pour éviter un faux négatif local).

---

## 2) Streaming SSE : ajouter les événements `metric`

### `src/chart_mcp/services/streaming.py`

> Le schéma `metric` est défini, mais **non émis** dans le pipeline.

* [x] **Ajouter** la mesure de temps par étape (data, indicateurs, levels, patterns, summary) et **publier** `event: metric` à chaque fin d’étape :

  ```python
  start = time.perf_counter()
  # ... exécution step ...
  await streamer.publish(
      "metric",
      {"step": "indicators", "ms": (time.perf_counter() - start) * 1000.0},
  )
  ```
* [x] En cas d’exception, tu publies déjà `error` puis `done` (garde ce comportement) – vérifie que l’exception **n’interrompt pas** l’envoi de la dernière métrique si la step a fini.

### `src/chart_mcp/schemas/streaming.py`

* [x] **Vérifier** que le `Literal["metric"]` existe déjà (c’est le cas) et que le payload accepte `{step:str, ms:float}` (sinon, ajouter un petit modèle `MetricDetails`).

### `tests/integration/test_stream_headers.py`

* [x] **Étendre** le test pour **accepter** aussi la présence d’au moins **un** `event: metric` dans le flux (au même titre que `token`/`result_partial`).

  * [x] Si l’horaire du test est serré, injecter un `monkeypatch` minimal autour de la clock/latence pour garantir l’émission d’une métrique.

---

## 3) Finance (flag) : durcir les tests de feature flag

> Le flag `FEATURE_FINANCE` est bien géré et déjà testé, mais on renforce un cas.

### `tests/integration/test_finance_feature_flag.py`

* [x] **Ajouter** un test supplémentaire “finance_routes_enabled_smoke” qui :

  * [x] force `FEATURE_FINANCE=true`, reconstruit l’app (tu le fais déjà partiellement),
  * [x] **appelle** un endpoint **read-only** (`/api/v1/finance/quote?symbol=BTCUSD`) et **vérifie** le 200 + structure minimale (sans dépendre d’un provider externe : stub/fixtures déjà en place).
  * [x] Restaure les settings en fin de test (`get_settings.cache_clear()`).

---

## 4) Documentation / DX

### `README.md`

* [x] **Relire** la table des variables d’env. Elle liste post-alpha des clés (NEWS_API_KEY/POSTGRES_URL…) :

  * [x] Marquer clairement **“futur / optionnel”** pour éviter la confusion.
  * [x] Déplacer la table MCP (noms des tools, exemples d’inputs/outputs) juste après la section API HTTP.

### `AGENTS.md`

* [x] **Remplacer** le contenu par la **présente** checklist + brief + “tests & build”.
* [x] Ajouter l’entête avec **date + commit hash** courant (tu le fais déjà).

---

# 🧪 Tests & Build — ce que tu dois continuer à respecter

* **Couverture** : `pytest --cov=src --cov-report=xml` ≥ **80 %** après ajout des tests MCP & metric.
* **Linters/formatters** : `ruff` / `black` / `isort` **sans erreur** (déjà câblé en CI avec `format-check`).
* **Typing** : `mypy src` **strict** (0 erreur).
* **Sécu** : aucune route hormis `/health` sans `Authorization: Bearer`; blacklist des secrets dans les logs (test déjà présent).
* **Docker** : image slim, user non-root, **HEALTHCHECK** via `docker/healthcheck.py` (OK).
* **SSE** : headers (`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`) **déjà** présents ; heartbeat OK.
* **Neutralité** : synthèse IA informative uniquement (test de vocabulaire & longueur ≤ 400 caractères présent).

---

## 📎 Patches prêts-à-coller (extraits)

**Emission des métriques SSE**

```python
# src/chart_mcp/services/streaming.py
import time

# ...
t0 = time.perf_counter()
frame = await provider.get_ohlcv(symbol, timeframe, limit=limit)  # ou sync selon impl
await streamer.publish("metric", {"step": "data", "ms": (time.perf_counter() - t0) * 1000.0})

t1 = time.perf_counter()
ind_res = indicator_service.compute_all(frame, indicators_spec)
await streamer.publish("metric", {"step": "indicators", "ms": (time.perf_counter() - t1) * 1000.0})

# idem pour levels / patterns / summary…
```

**Entrée MCP (main)**

```python
# src/chart_mcp/mcp_main.py
from __future__ import annotations
import asyncio
from fastmcp import MCPServer  # adapte au vrai import du serveur MCP
from chart_mcp import mcp_server as tools

def register(server: MCPServer) -> None:
    server.tool("get_crypto_data")(tools.get_crypto_data)
    server.tool("compute_indicator")(tools.compute_indicator)
    server.tool("identify_support_resistance")(tools.identify_support_resistance)
    server.tool("detect_chart_patterns")(tools.detect_chart_patterns)
    server.tool("generate_analysis_summary")(tools.generate_analysis_summary)

async def main() -> None:
    server = MCPServer()
    register(server)
    await server.serve_stdio()

if __name__ == "__main__":
    asyncio.run(main())
```

**Script Make**

```make
mcp-run:
python -m chart_mcp.mcp_main
```

**Test d’enregistrement des tools**

```python
# tests/unit/mcp/test_server_runtime.py
import importlib
import pytest

def test_tools_registered():
    m = importlib.import_module("chart_mcp.mcp_main")
    class Dummy:
        def __init__(self):
            self.names = []
        def tool(self, name):
            def deco(fn):
                self.names.append(name)
                return fn
            return deco
    server = Dummy()
    m.register(server)
    for name in [
        "get_crypto_data","compute_indicator",
        "identify_support_resistance","detect_chart_patterns",
        "generate_analysis_summary",
    ]:
        assert name in server.names
```

---

si tu coches **tout** ci-dessus, on clôt l’alpha avec : **MCP serveur réel**, **flux SSE métriques**, **tests renforcés**, **doc MCP claire** — le tout sans régression sur l’API HTTP existante. Tu peux maintenant **remplacer `AGENTS.md`** par cette liste et enchaîner.
---
Historique récent:
- 2025-10-25T04:17:56Z : Ajout du serveur MCP FastMCP (entrypoint stdio + job CI), émission `metric` typée côté SSE, extension README/Makefile et tests (unitaires & finance flag) validés via pytest ciblé.
- 2025-10-25T04:29:27Z : Vérification locale FastMCP (import + API stdio), exécution des tests ciblés (`pytest tests/unit/mcp/test_server_runtime.py tests/integration/test_stream_headers.py tests/integration/test_finance_feature_flag.py`) et rafraîchissement de ce journal.
- 2025-10-25T05:01:13Z : Correction ruff (`I001`, `D202`, `D204`) sur l'entrée MCP + tests ciblés (`pytest tests/unit/mcp/test_server_runtime.py tests/integration/test_finance_feature_flag.py`) pour confirmer l'absence de régressions.
- 2025-10-25T05:12:43Z : Ajout d'un stub `fastmcp` pour mypy, élargissement du protocole d'enregistrement afin d'accepter `FastMCP`, formatage `black` sur les modules MCP et validation `mypy`, `make format-check`, `pytest tests/unit/mcp/test_server_runtime.py`, `ruff check` ciblé.
- 2025-10-25T05:24:31Z : Tri des imports dans le stub `fastmcp/__init__.pyi` via `ruff --fix`, exécution de `pytest tests/unit/mcp/test_server_runtime.py` et `ruff check .` pour confirmer l'alignement lint/typage.
