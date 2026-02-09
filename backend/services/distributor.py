"""
Nexar API integration for real-time component pricing and availability.

Nexar (formerly Octopart) aggregates pricing/stock data from 50+ distributors
(Mouser, Digi-Key, LCSC, Arrow, Newark, etc.) via a single GraphQL API.

Usage:
    client = NexarClient(client_id, client_secret)
    results = await client.search_parts("10kohm resistor 0805")
    enriched = await client.enrich_bom(bom_entries)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Nexar API endpoints
_TOKEN_URL = "https://identity.nexar.com/connect/token"
_GRAPHQL_URL = "https://api.nexar.com/graphql"

# Cache TTL in seconds (1 hour)
_CACHE_TTL = 3600

# Timeout for Nexar API calls (seconds)
_REQUEST_TIMEOUT = 8.0

_SEARCH_QUERY = """
query SearchParts($query: String!, $limit: Int!) {
  supSearchMpn(q: $query, limit: $limit) {
    results {
      part {
        mpn
        manufacturer { name }
        shortDescription
        sellers {
          company { name }
          offers {
            sku
            inventoryLevel
            prices { quantity price currency }
            clickUrl
          }
        }
      }
    }
  }
}
"""


@dataclass
class PriceBreak:
    quantity: int
    unit_price: float


@dataclass
class DistributorOption:
    distributor: str
    sku: str
    unit_price: float
    stock: int
    url: str
    price_breaks: list[PriceBreak] = field(default_factory=list)


@dataclass
class PartResult:
    mpn: str
    manufacturer: str
    description: str
    distributor_options: list[DistributorOption] = field(default_factory=list)


def _build_search_query(bom_entry: dict) -> str:
    """Build a search string from a BOM entry's component attributes."""
    parts = []

    comp_type = bom_entry.get("type", "")
    if comp_type:
        parts.append(comp_type)

    value_display = bom_entry.get("value_display", "")
    if value_display:
        parts.append(value_display)

    footprint = bom_entry.get("footprint", "")
    if footprint:
        parts.append(footprint)

    tolerance = bom_entry.get("tolerance", "")
    if tolerance:
        parts.append(tolerance)

    return " ".join(parts)


class NexarClient:
    """Client for the Nexar (Octopart) component search API."""

    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expires: float = 0.0
        self._cache: dict[str, tuple[list[PartResult], float]] = {}

    async def _get_token(self) -> str:
        """Get OAuth2 bearer token, refreshing if expired."""
        now = time.time()
        if self._token and now < self._token_expires:
            return self._token

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": "supply.domain",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        self._token = data["access_token"]
        # Expire 60s early to avoid edge cases
        self._token_expires = now + data.get("expires_in", 3600) - 60
        return self._token

    async def search_parts(self, query: str, limit: int = 3) -> list[PartResult]:
        """Search Nexar for parts matching a query string."""
        # Check cache
        now = time.time()
        cached = self._cache.get(query)
        if cached:
            results, cached_at = cached
            if now - cached_at < _CACHE_TTL:
                return results

        token = await self._get_token()

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            resp = await client.post(
                _GRAPHQL_URL,
                json={
                    "query": _SEARCH_QUERY,
                    "variables": {"query": query, "limit": limit},
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = self._parse_search_results(data)

        # Cache results
        self._cache[query] = (results, now)

        return results

    def _parse_search_results(self, data: dict) -> list[PartResult]:
        """Parse GraphQL response into PartResult objects."""
        results = []
        search_results = (
            data.get("data", {})
            .get("supSearchMpn", {})
            .get("results", [])
        )

        for sr in search_results:
            part = sr.get("part", {})
            mpn = part.get("mpn", "")
            manufacturer = part.get("manufacturer", {}).get("name", "")
            description = part.get("shortDescription", "")

            dist_options = []
            for seller in part.get("sellers", []):
                distributor_name = seller.get("company", {}).get("name", "")
                for offer in seller.get("offers", []):
                    prices = offer.get("prices", [])
                    # Filter to USD prices
                    usd_prices = [
                        p for p in prices
                        if p.get("currency", "USD") == "USD"
                    ]
                    if not usd_prices:
                        continue

                    price_breaks = [
                        PriceBreak(
                            quantity=int(p.get("quantity", 1)),
                            unit_price=float(p.get("price", 0)),
                        )
                        for p in usd_prices
                    ]
                    # Unit price = price at lowest quantity
                    unit_price = price_breaks[0].unit_price if price_breaks else 0.0

                    dist_options.append(
                        DistributorOption(
                            distributor=distributor_name,
                            sku=offer.get("sku", ""),
                            unit_price=unit_price,
                            stock=int(offer.get("inventoryLevel", 0)),
                            url=offer.get("clickUrl", ""),
                            price_breaks=price_breaks,
                        )
                    )

            results.append(
                PartResult(
                    mpn=mpn,
                    manufacturer=manufacturer,
                    description=description,
                    distributor_options=dist_options,
                )
            )

        return results

    async def enrich_bom(self, bom_entries: list[dict]) -> list[dict]:
        """
        Enrich BOM entries with real distributor data.

        Takes raw BOM entries from engine/bom.py, searches Nexar for each,
        and attaches pricing/stock/links. Falls back gracefully on errors.
        """
        async def _enrich_one(entry: dict) -> dict:
            query = _build_search_query(entry)
            enriched = dict(entry)
            try:
                parts = await self.search_parts(query)
                if parts:
                    best = parts[0]
                    enriched["mpn"] = best.mpn
                    enriched["manufacturer"] = best.manufacturer

                    dist_options = []
                    for opt in best.distributor_options:
                        dist_options.append({
                            "distributor": opt.distributor,
                            "sku": opt.sku,
                            "unit_price": opt.unit_price,
                            "stock": opt.stock,
                            "url": opt.url,
                            "price_breaks": [
                                {"quantity": pb.quantity, "unit_price": pb.unit_price}
                                for pb in opt.price_breaks
                            ],
                        })
                    enriched["distributor_options"] = dist_options

                    # Best price = lowest unit price across all distributor options
                    all_prices = [
                        o.unit_price for o in best.distributor_options
                        if o.unit_price > 0
                    ]
                    enriched["best_price"] = min(all_prices) if all_prices else None
                else:
                    enriched["mpn"] = None
                    enriched["manufacturer"] = None
                    enriched["distributor_options"] = []
                    enriched["best_price"] = None
            except Exception:
                logger.warning("Nexar search failed for: %s", query, exc_info=True)
                enriched["mpn"] = None
                enriched["manufacturer"] = None
                enriched["distributor_options"] = []
                enriched["best_price"] = None

            return enriched

        results = await asyncio.gather(*[_enrich_one(e) for e in bom_entries])
        return list(results)
