"""Stub analysis service generating pedagogical summaries."""

from __future__ import annotations

from typing import Dict, Iterable, List

from chart_mcp.services.levels import LevelCandidate
from chart_mcp.services.patterns import PatternResult


class AnalysisLLMService:
    """Generate human-readable summary without giving financial advice."""

    disclaimer = "Cette analyse est informative et ne constitue pas un conseil d'investissement."

    def summarize(
        self,
        symbol: str,
        timeframe: str,
        indicator_highlights: Dict[str, float],
        levels: Iterable[LevelCandidate],
        patterns: Iterable[PatternResult],
    ) -> str:
        """Create a deterministic summary string."""
        parts: List[str] = []
        parts.append(
            f"Analyse de {symbol.upper()} sur l'horizon {timeframe}. Les observations suivantes ressortent :"
        )
        if indicator_highlights:
            formatted = ", ".join(
                f"{name} à {value:.2f}" for name, value in indicator_highlights.items()
            )
            parts.append(f"Indicateurs clés : {formatted}.")
        else:
            parts.append("Aucun indicateur spécifique demandé.")
        levels_list = list(levels)
        if levels_list:
            level_desc = ", ".join(
                f"{lvl.kind} autour de {lvl.price:.2f}" for lvl in levels_list[:3]
            )
            parts.append(f"Niveaux observés : {level_desc}.")
        patterns_list = list(patterns)
        if patterns_list:
            pattern_desc = ", ".join(p.name.replace("_", " ") for p in patterns_list[:3])
            parts.append(f"Patterns détectés : {pattern_desc}.")
        parts.append("Ces éléments décrivent la structure actuelle du marché sans prise de position.")
        return " ".join(parts)


__all__ = ["AnalysisLLMService"]
