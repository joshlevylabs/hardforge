"""Subscription tier checking middleware."""

from fastapi import HTTPException, Request

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


def check_tier(request: Request, required_tier: str = "free"):
    """Check if the current user has the required subscription tier.

    In production, this reads from the JWT token / Supabase session.
    For now, this is a placeholder that allows all requests.
    """
    # TODO: Implement actual tier checking from JWT claims
    # user_tier = request.state.user.subscription_tier
    # tier_levels = {"free": 0, "pro": 1, "team": 2}
    # if tier_levels.get(user_tier, 0) < tier_levels.get(required_tier, 0):
    #     raise HTTPException(
    #         status_code=403,
    #         detail=f"This feature requires a {required_tier} subscription."
    #     )
    pass


def check_design_limit(request: Request):
    """Check if free tier user has exceeded their monthly design limit.

    In production, this queries the database for the user's design count.
    """
    # TODO: Implement actual limit checking
    # user = request.state.user
    # if user.subscription_tier == "free" and user.designs_this_month >= FREE_TIER_MONTHLY_LIMIT:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Free tier limit reached (3 designs/month). Upgrade to Pro for unlimited designs."
    #     )
    pass
