"""HTTP endpoint exposing the SearxNG-backed search feature."""

from __future__ import annotations

from typing import Annotated, List, cast

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.search import SearchResponse, SearchResult as SearchResultModel
from chart_mcp.services.search import SearchClientProtocol
from chart_mcp.utils.errors import BadRequest, UpstreamError

router = APIRouter(
    prefix="/api/v1/search",
    tags=["search"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_search_client(request: Request) -> SearchClientProtocol:
    """Return the configured SearxNG client from the FastAPI application state."""
    client = getattr(request.app.state, "search_client", None)
    if client is None:
        raise BadRequest("SearxNG integration is not configured")
    if not hasattr(client, "search"):
        raise BadRequest("SearxNG integration is misconfigured")
    return cast(SearchClientProtocol, client)


ClientDep = Annotated[SearchClientProtocol, Depends(get_search_client)]


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search crypto intelligence with SearxNG",
    description=(
        "Proxy vers l'instance SearxNG interne pour agréger news, articles techniques et "
        "sources communautaires."
    ),
    response_description="Résultats normalisés (titre, lien, extrait, score).",
)
def search(
    client: ClientDep,
    q: Annotated[str, Query(min_length=3, description="User search query")],
    categories: Annotated[
        str | None,
        Query(
            description="Comma-separated SearxNG categories (e.g. news,science)",
            example="news,science",
        ),
    ] = None,
    time_range: Annotated[
        str | None,
        Query(description="Optional SearxNG time filter such as day/week/month"),
    ] = None,
) -> SearchResponse:
    """Proxy the query to SearxNG and return normalized results."""
    parsed_categories = _parse_categories(categories)
    try:
        results = client.search(query=q, categories=parsed_categories, time_range=time_range)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    except UpstreamError:
        raise
    response_items: List[SearchResultModel] = [
        SearchResultModel(
            title=item.title,
            url=item.url,
            snippet=item.snippet,
            source=item.source,
            score=item.score,
        )
        for item in results
    ]
    return SearchResponse(query=q, categories=parsed_categories, results=response_items)


def _parse_categories(raw: str | None) -> List[str]:
    """Split and clean the comma-separated categories string."""
    if raw is None:
        return []
    parts = [candidate.strip() for candidate in raw.split(",")]
    cleaned = [candidate.lower() for candidate in parts if candidate]
    # Preserve order while removing duplicates.
    seen: set[str] = set()
    unique: List[str] = []
    for category in cleaned:
        if category not in seen:
            seen.add(category)
            unique.append(category)
    return unique
