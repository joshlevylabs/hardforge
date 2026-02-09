"""Auth routes — local SQLite auth + Stripe subscriptions."""

import os
from typing import Optional

import stripe
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth import hash_password, verify_password, create_access_token, get_current_user
from backend.database import get_db
from backend.models_db import User

router = APIRouter()


# --- Request/Response Models ---

class SignUpRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(default="", max_length=255)


class SignInRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    subscription_tier: str
    designs_this_month: int


class AuthResponse(BaseModel):
    user: UserResponse
    token: str


# --- Auth Endpoints ---

@router.post("/auth/signup", response_model=AuthResponse)
async def signup(body: SignUpRequest, db: Session = Depends(get_db)):
    """Create a new user account."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            subscription_tier=user.subscription_tier,
            designs_this_month=user.designs_this_month,
        ),
        token=token,
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(body: SignInRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            subscription_tier=user.subscription_tier,
            designs_this_month=user.designs_this_month,
        ),
        token=token,
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        subscription_tier=current_user.subscription_tier,
        designs_this_month=current_user.designs_this_month,
    )


# --- Stripe (keep existing, unchanged) ---

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
        raise HTTPException(status_code=500, detail="Stripe error")


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

    # SECURITY WARNING: These webhook handlers are incomplete stubs.
    # Without proper implementation, attackers could send fake webhook events
    # to grant themselves paid subscriptions. Must implement before production:
    # 1. Extract customer email/metadata from event
    # 2. Look up user in database
    # 3. Update user.subscription_tier in database
    # 4. Validate event authenticity via Stripe signature (already done above)
    if event["type"] == "checkout.session.completed":
        pass  # TODO: Upgrade user subscription tier in database
    elif event["type"] == "customer.subscription.deleted":
        pass  # TODO: Downgrade user to free tier in database
    elif event["type"] == "customer.subscription.updated":
        pass  # TODO: Update user subscription tier in database

    return {"status": "ok"}
