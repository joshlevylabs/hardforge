"""Subscription tier checking middleware."""

from fastapi import Depends, HTTPException

from backend.auth import get_current_user
from backend.models_db import User

# Routes that require pro tier or above
PRO_ROUTES = [
    "/api/generate-gerber",
    "/api/simulate",
]

# Routes that require any authentication
AUTH_ROUTES = [
    "/api/parse-intent",
    "/api/analyze-feasibility",
    "/api/design-circuit",
    "/api/generate-schematic",
    "/api/generate-bom",
    "/api/generate-skidl",
    "/api/generate-kicad-project",
]

# Free tier monthly design limit
FREE_TIER_MONTHLY_LIMIT = 3

TIER_LEVELS = {"free": 0, "pro": 1, "team": 2}


def require_tier(required_tier: str = "free"):
    """Return a FastAPI dependency that checks subscription tier."""
    async def _check(current_user: User = Depends(get_current_user)):
        user_level = TIER_LEVELS.get(current_user.subscription_tier, 0)
        required_level = TIER_LEVELS.get(required_tier, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires a {required_tier} subscription.",
            )
        return current_user
    return _check


def require_design_limit():
    """Return a FastAPI dependency that checks free tier design limit."""
    async def _check(current_user: User = Depends(get_current_user)):
        if (
            current_user.subscription_tier == "free"
            and current_user.designs_this_month >= FREE_TIER_MONTHLY_LIMIT
        ):
            raise HTTPException(
                status_code=403,
                detail="Free tier limit reached (3 designs/month). Upgrade to Pro for unlimited designs.",
            )
        return current_user
    return _check
