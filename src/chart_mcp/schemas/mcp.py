"""Pydantic models describing the MCP stdio contract.

The Model Context Protocol (MCP) relies on JSON payloads when exchanging
messages with tools exposed over stdio.  Keeping a strongly typed schema on
our side guarantees that the stdio surface remains in sync with the REST
API: every field is documented, validated and serialised deterministically.
The models defined here are re-used by :mod:`chart_mcp.mcp_server` to parse
incoming requests and to validate the response payloads before they are
returned to FastMCP.
"""

from __future__ import annotations

import collections.abc as collections_abc
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol
from chart_mcp.utils.errors import BadRequest, UnprocessableEntity
from chart_mcp.utils.timeframes import ccxt_timeframe


class _SymbolTimeframeMixin(BaseModel):
    """Mixin applying consistent validation to ``symbol`` and ``timeframe``.

    The logic mirrors the REST layer: symbols are stripped and normalised to the
    ``BASE/QUOTE`` format accepted by CCXT, while timeframes must belong to the
    canonical registry defined in :mod:`chart_mcp.utils.timeframes`.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    symbol: str = Field(
        ...,
        min_length=3,
        max_length=25,
        description="Paire de trading à la notation CCXT (ex: BTC/USDT).",
    )
    timeframe: str = Field(
        ...,
        min_length=2,
        max_length=6,
        description="Intervalle temporel (1m, 1h, 4h, 1d, etc.).",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def _normalise_symbol(cls, value: str) -> str:
        """Force le format ``BASE/QUOTE`` pour les paires CCXT."""
        try:
            return normalize_symbol(str(value))
        except BadRequest as exc:  # pragma: no cover - defensive guard
            raise ValueError(str(exc)) from exc

    @field_validator("timeframe", mode="before")
    @classmethod
    def _validate_timeframe(cls, value: str) -> str:
        """S'assure que le timeframe appartient à la table supportée."""
        try:
            return ccxt_timeframe(str(value))
        except UnprocessableEntity as exc:  # pragma: no cover - mirrored from API layer
            raise ValueError(str(exc)) from exc


class MCPWindowedQuery(_SymbolTimeframeMixin):
    """Requête comprenant les paramètres de fenêtre ``limit``/``start``/``end``."""

    limit: int = Field(
        500,
        ge=10,
        le=5000,
        description="Nombre maximum de chandelles à récupérer (borne supérieure 5k).",
    )
    start: int | None = Field(
        default=None,
        ge=0,
        description="Timestamp UNIX (secondes) de début de fenêtre, optionnel.",
    )
    end: int | None = Field(
        default=None,
        ge=0,
        description="Timestamp UNIX (secondes) de fin de fenêtre, optionnel.",
    )

    @field_validator("end")
    @classmethod
    def _validate_window(cls, value: int | None, info: ValidationInfo) -> int | None:
        """Empêche une fenêtre ``end`` antérieure au ``start`` fourni."""
        start = info.data.get("start") if info else None
        if start is not None and value is not None and value <= start:
            raise ValueError("'end' must be greater than 'start'")
        return value


class MCPIndicatorRequest(MCPWindowedQuery):
    """Requête de calcul d'indicateur technique."""

    indicator: str = Field(
        ...,
        min_length=2,
        max_length=48,
        description="Nom canonique de l'indicateur (ema, rsi, macd, bbands...).",
    )
    params: Dict[str, float] = Field(
        default_factory=dict,
        description="Paramètres numériques optionnels propres à l'indicateur.",
    )

    @field_validator("params", mode="before")
    @classmethod
    def _coerce_params(cls, value: Mapping[str, Any] | None) -> Dict[str, float]:
        """Cast mapping values to floats to guarantee uniformity."""
        if value is None:
            return {}
        coerced: Dict[str, float] = {}
        for key, raw in dict(value).items():
            coerced[str(key)] = float(raw)
        return coerced


class MCPLevelsParams(BaseModel):
    """Paramètres optionnels pour l'extraction des supports/résistances."""

    model_config = ConfigDict(extra="forbid")

    max_levels: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Nombre maximum de niveaux à retourner.",
    )
    distance: int | None = Field(
        default=None,
        ge=1,
        description="Nombre minimal de chandelles entre deux pics successifs.",
    )
    prominence: float | None = Field(
        default=None,
        ge=0.0,
        description="Prominence minimale des pics identifiés (voir scipy.find_peaks).",
    )
    merge_threshold: float | None = Field(
        default=None,
        ge=0.0001,
        le=0.05,
        description="Tolérance relative utilisée pour fusionner les clusters proches.",
    )
    min_touches: int | None = Field(
        default=None,
        ge=1,
        description="Nombre minimal de contacts pour conserver un niveau.",
    )


class MCPLevelsRequest(MCPWindowedQuery):
    """Requête pour récupérer les niveaux de support/résistance."""

    params: MCPLevelsParams | None = Field(
        default=None,
        description="Affinage optionnel de l'algorithme de détection.",
    )


class MCPPatternsParams(BaseModel):
    """Paramètres additionnels utilisés lors de la détection de figures."""

    model_config = ConfigDict(extra="forbid")

    max_patterns: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Nombre maximal de figures retournées.",
    )
    min_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score minimal pour filtrer les figures faibles.",
    )


class MCPPatternsRequest(MCPWindowedQuery):
    """Requête orientée détection de figures chartistes."""

    params: MCPPatternsParams | None = Field(
        default=None,
        description="Filtre optionnel sur le nombre et la qualité des figures.",
    )


class MCPAnalysisIndicatorSpec(BaseModel):
    """Description d'un indicateur à calculer avant la génération IA."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    name: str = Field(
        ...,
        min_length=2,
        max_length=48,
        description="Nom de l'indicateur (ema, rsi, macd...).",
    )
    params: Dict[str, float] = Field(
        default_factory=dict,
        description="Paramètres numériques propres à l'indicateur.",
    )

    @field_validator("params", mode="before")
    @classmethod
    def _coerce_indicator_params(cls, value: Mapping[str, Any] | None) -> Dict[str, float]:
        """Normalise les valeurs en flottants pour simplifier la consommation."""
        if value is None:
            return {}
        coerced: Dict[str, float] = {}
        for key, raw in dict(value).items():
            coerced[str(key)] = float(raw)
        return coerced


class MCPAnalysisPayload(MCPWindowedQuery):
    """Payload complet attendu par ``generate_analysis_summary``."""

    indicators: list[MCPAnalysisIndicatorSpec] = Field(
        default_factory=list,
        description="Liste optionnelle d'indicateurs à calculer avant la synthèse.",
    )
    include_levels: bool = Field(
        default=True,
        description="Inclure ou non la détection de supports/résistances.",
    )
    include_patterns: bool = Field(
        default=True,
        description="Inclure la détection de figures chartistes dans le résumé.",
    )
    levels_params: MCPLevelsParams | None = Field(
        default=None,
        description="Paramètres spécifiques aux niveaux, réutilisés dans la synthèse.",
    )
    patterns_params: MCPPatternsParams | None = Field(
        default=None,
        description="Paramètres spécifiques aux figures chartistes pour la synthèse.",
    )


class MCPOhlcvPoint(BaseModel):
    """Représentation JSON d'une chandelle OHLCV."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ts: int = Field(..., ge=0, description="Horodatage UNIX (secondes).")
    o: float = Field(..., description="Prix d'ouverture.")
    h: float = Field(..., description="Plus haut de la période.")
    l: float = Field(..., description="Plus bas de la période.")  # noqa: E741
    c: float = Field(..., description="Prix de clôture.")
    v: float = Field(..., ge=0.0, description="Volume échangé pendant la période.")


class MCPIndicatorPoint(BaseModel):
    """Point d'indicateur associé à un timestamp précis."""

    model_config = ConfigDict(extra="forbid")

    ts: int = Field(..., ge=0, description="Horodatage UNIX (secondes).")
    values: Dict[str, float] = Field(
        default_factory=dict,
        description="Valeurs numériques produites par l'indicateur.",
    )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MCPIndicatorPoint":
        """Crée un point depuis un mapping plat ``{"ts": ..., "ema": ...}``."""
        data = dict(payload)
        timestamp = int(data.pop("ts"))
        numeric_values: Dict[str, float] = {str(key): float(value) for key, value in data.items()}
        return cls(ts=timestamp, values=numeric_values)

    def as_dict(self) -> Dict[str, float | int]:
        """Retourne une représentation aplatie compatible avec l'API historique."""
        record: Dict[str, float | int] = {"ts": int(self.ts)}
        record.update({key: float(value) for key, value in self.values.items()})
        return record


class MCPLevelRange(BaseModel):
    """Fenêtre temporelle couverte par un niveau de prix."""

    model_config = ConfigDict(extra="forbid")

    start_ts: int = Field(..., ge=0, description="Premier timestamp contribuant au niveau.")
    end_ts: int = Field(..., ge=0, description="Dernier timestamp contribuant au niveau.")


class MCPLevelPayload(BaseModel):
    """Payload JSON retourné par le tool ``identify_support_resistance``."""

    model_config = ConfigDict(extra="forbid")

    price: float = Field(..., ge=0.0, description="Prix moyen du niveau.")
    strength: float = Field(..., ge=0.0, le=1.0, description="Score de confiance agrégé.")
    strength_label: str = Field(..., description="Catégorie qualitative (fort/général).")
    kind: str = Field(..., description="Nature du niveau (support ou resistance).")
    ts_range: MCPLevelRange = Field(..., description="Plage temporelle couverte par le niveau.")


class MCPPatternPoint(BaseModel):
    """Point constitutif d'une figure chartiste."""

    model_config = ConfigDict(extra="forbid")

    ts: int = Field(..., ge=0, description="Horodatage du point.")
    price: float = Field(..., description="Prix au niveau du point.")


class MCPPatternPayload(BaseModel):
    """Figure chartiste sérialisée pour le protocole MCP."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Nom canonique de la figure.")
    score: float = Field(..., ge=0.0, le=1.0, description="Score heuristique de la figure.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Indice de confiance global.")
    start_ts: int = Field(..., ge=0, description="Horodatage de début de la figure.")
    end_ts: int = Field(..., ge=0, description="Horodatage de fin de la figure.")
    points: list[MCPPatternPoint] = Field(
        default_factory=list,
        description="Liste ordonnée des points clés de la figure.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Informations supplémentaires (direction, indices, etc.).",
    )


class MCPAnalysisResponse(BaseModel):
    """Structure minimaliste retournée par ``generate_analysis_summary``."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., description="Texte pédagogique synthétisant l'analyse.")
    disclaimer: str = Field(..., description="Mention de non-conseil financier.")


class MCPWebSearchRequest(BaseModel):
    """Requête décrivant l'appel au moteur de recherche SearxNG."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    query: str = Field(
        ...,
        min_length=3,
        max_length=256,
        description="Requête utilisateur (minimum 3 caractères).",
    )
    categories: List[str] = Field(
        default_factory=list,
        description="Catégories SearxNG optionnelles (ex: news,science).",
    )
    time_range: str | None = Field(
        default=None,
        description="Fenêtre temporelle SearxNG (day, week, month...).",
    )
    language: str = Field(
        default="fr",
        min_length=2,
        max_length=8,
        description="Code langue transmis à SearxNG (par défaut fr).",
    )

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        """Vérifie que la requête finale n'est pas vide après nettoyage."""
        trimmed = value.strip()
        if len(trimmed) < 3:
            raise ValueError("query must contain at least 3 visible characters")
        return trimmed

    @field_validator("categories", mode="before")
    @classmethod
    def _coerce_categories(cls, value: Any) -> List[str]:
        """Normalise les catégories en liste unique et en minuscules."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            candidates = value.split(",")
        elif isinstance(value, collections_abc.Iterable):
            candidates = list(value)
        else:  # pragma: no cover - validation garde-fou
            raise TypeError("categories must be a string or iterable of strings")
        cleaned: List[str] = []
        seen: set[str] = set()
        for raw in candidates:
            candidate = str(raw).strip().lower()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            cleaned.append(candidate)
        return cleaned


class MCPWebSearchResult(BaseModel):
    """Item de résultat renvoyé par le tool ``web_search``."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Titre du résultat.")
    url: str = Field(..., description="URL destination.")
    snippet: str = Field(..., description="Extrait de contenu.")
    source: str = Field(..., description="Moteur à l'origine du résultat.")
    score: float = Field(..., ge=0.0, description="Score agrégé fourni par SearxNG.")


class MCPWebSearchResponse(BaseModel):
    """Structure de réponse normalisée pour l'intégration MCP."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Requête utilisateur normalisée.")
    categories: List[str] = Field(
        default_factory=list,
        description="Catégories SearxNG retenues après nettoyage.",
    )
    time_range: str | None = Field(
        default=None,
        description="Fenêtre temporelle appliquée côté SearxNG.",
    )
    language: str = Field(..., description="Code langue utilisé pour la requête.")
    results: List[MCPWebSearchResult] = Field(
        default_factory=list,
        description="Résultats normalisés retournés par SearxNG.",
    )


def flatten_indicator_records(records: Iterable[Mapping[str, Any]]) -> list[Dict[str, float | int]]:
    """Normalise et valide une séquence de points d'indicateurs.

    Les outils FastMCP manipulent des dictionnaires plats pour la compatibilité.
    Cette fonction convertit donc les payloads validés par
    :class:`MCPIndicatorPoint` en dictionnaires prêts à être renvoyés côté MCP.
    """
    validated = [MCPIndicatorPoint.from_payload(record) for record in records]
    return [item.as_dict() for item in validated]


def coerce_mapping(payload: Mapping[str, Any] | MutableMapping[str, Any]) -> Dict[str, Any]:
    """Retourne une copie ``dict`` d'un mapping pydantic-compatible."""
    return dict(payload)


__all__ = [
    "MCPWindowedQuery",
    "MCPIndicatorRequest",
    "MCPLevelsParams",
    "MCPLevelsRequest",
    "MCPPatternsParams",
    "MCPPatternsRequest",
    "MCPAnalysisIndicatorSpec",
    "MCPAnalysisPayload",
    "MCPOhlcvPoint",
    "MCPIndicatorPoint",
    "MCPLevelPayload",
    "MCPLevelRange",
    "MCPPatternPayload",
    "MCPPatternPoint",
    "MCPAnalysisResponse",
    "MCPWebSearchRequest",
    "MCPWebSearchResult",
    "MCPWebSearchResponse",
    "flatten_indicator_records",
    "coerce_mapping",
]
