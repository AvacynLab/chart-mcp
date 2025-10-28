"""Heuristic analysis summary stub ensuring neutral tone."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Generator, Iterable, List

from chart_mcp.services.levels import LevelCandidate
from chart_mcp.services.patterns import PatternResult

# ``acheter`` and friends must never appear in the generated copy. The substitution
# keeps the overall structure intelligible while scrubbing any prescriptive wording
# that might come from user-provided indicator names.
_FORBIDDEN_PATTERN = re.compile(r"(acheter|vendre|buy|sell)", re.IGNORECASE)


@dataclass(frozen=True)
class AnalysisSummary:
    """Value object bundling the textual summary and disclaimer."""

    summary: str
    disclaimer: str


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
    ) -> AnalysisSummary:
        """Create a deterministic summary while enforcing neutrality constraints."""
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
        parts.append(
            "Ces éléments décrivent la structure actuelle du marché sans prise de position."
        )
        summary = self._sanitize(" ".join(parts))
        if len(summary) > 400:
            summary = self._truncate(summary)
        summary = self._sanitize(summary)
        return AnalysisSummary(summary=summary, disclaimer=self.disclaimer)

    def stream_summary(
        self,
        symbol: str,
        timeframe: str,
        indicator_highlights: Dict[str, float],
        levels: Iterable[LevelCandidate],
        patterns: Iterable[PatternResult],
    ) -> Generator[str, None, AnalysisSummary]:
        """Yield a tokenised summary before returning the final :class:`AnalysisSummary`.

        The generator mimics incremental decoding by splitting the deterministic
        summary into whitespace-delimited tokens.  Each yielded element retains the
        trailing space (except the final token) so SSE consumers can simply append
        fragments to a growing text node without having to re-introduce spacing.
        """
        summary = self.summarize(symbol, timeframe, indicator_highlights, levels, patterns)
        tokens = summary.summary.split()
        total = len(tokens)
        for idx, token in enumerate(tokens):
            suffix = " " if idx < total - 1 else ""
            yield f"{token}{suffix}"
        return summary

    @staticmethod
    def _sanitize(text: str) -> str:
        """Strip prescriptive vocabulary from *text*."""
        return _FORBIDDEN_PATTERN.sub("[neutral]", text)

    @staticmethod
    def _truncate(text: str) -> str:
        """Trim *text* to the 400 character budget without cutting words."""
        truncated = text[:400]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return truncated.rstrip() + "…"


__all__ = ["AnalysisLLMService", "AnalysisSummary"]
