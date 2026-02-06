"""Auth and billing routes — Supabase auth + Stripe subscriptions."""

import os
from typing import Optional

import stripe
from fastapi import APIRouter, HTTPException, Request, Header

router = APIRouter()


@router.post("/auth/signup")
async def signup(request: Request):
    """Create a new user account via Supabase."""
    body = await request.json()
    email = body.get("email")
    password = body.get("password")
    name = body.get("name")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    # In production, this would call Supabase auth
    # For now, return a mock response
    return {
        "user": {
            "id": "mock-user-id",
            "email": email,
            "name": name,
            "subscription_tier": "free",
        },
        "message": "Account created successfully",
    }


@router.post("/auth/login")
async def login(request: Request):
    """Login via Supabase."""
    body = await request.json()
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    return {
        "user": {
            "id": "mock-user-id",
            "email": email,
            "subscription_tier": "free",
        },
        "token": "mock-jwt-token",
    }


@router.post("/checkout")
async def create_checkout_session(request: Request):
    """Create a Stripe checkout session for subscription upgrade."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = stripe_key
    body = await request.json()
    tier = body.get("tier", "pro")

    price_ids = {
        "pro": os.getenv("STRIPE_PRO_PRICE_ID", "price_pro_placeholder"),
        "team": os.getenv("STRIPE_TEAM_PRICE_ID", "price_team_placeholder"),
    }

    if tier not in price_ids:
        raise HTTPException(status_code=400, detail="Invalid tier")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_ids[tier], "quantity": 1}],
            mode="subscription",
            success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard?success=true",
            cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard?canceled=true",
        )
        return {"checkout_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
):
    """Handle Stripe webhook events."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not stripe_key or not webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = stripe_key
    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle subscription events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Update user subscription tier in database
        # customer_id = session.get("customer")
        # subscription_id = session.get("subscription")
        pass

    elif event["type"] == "customer.subscription.deleted":
        # Downgrade user to free tier
        pass

    elif event["type"] == "customer.subscription.updated":
        # Update subscription status
        pass

    return {"status": "ok"}
