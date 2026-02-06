"""Feasibility analysis route — DesignIntent → FeasibilityReport."""

import json
import os

from anthropic import Anthropic
from fastapi import APIRouter, HTTPException

from backend.ai.prompts import FEASIBILITY_SYSTEM, build_feasibility_messages
from backend.models import (
    DesignOption,
    FeasibilityReport,
    FeasibilityRequest,
    FeasibilityResponse,
)

router = APIRouter()

client = None


def get_client() -> Anthropic:
    global client
    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
        client = Anthropic(api_key=api_key)
    return client


@router.post("/analyze-feasibility", response_model=FeasibilityResponse)
async def analyze_feasibility(request: FeasibilityRequest):
    """Analyze feasibility of a design intent and suggest topology options."""
    try:
        ai_client = get_client()
        intent_json = request.intent.model_dump_json()
        messages = build_feasibility_messages(intent_json)

        response = ai_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=3000,
            system=FEASIBILITY_SYSTEM,
            messages=messages,
        )

        response_text = response.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        parsed = json.loads(response_text)

        design_options = [
            DesignOption(
                name=opt["name"],
                description=opt["description"],
                topology=opt["topology"],
                pros=opt.get("pros", []),
                cons=opt.get("cons", []),
                estimated_components=opt.get("estimated_components", 0),
                estimated_cost=opt.get("estimated_cost"),
            )
            for opt in parsed.get("design_options", [])
        ]

        report = FeasibilityReport(
            feasible=parsed.get("feasible", True),
            summary=parsed.get("summary", ""),
            challenges=parsed.get("challenges", []),
            design_options=design_options,
            power_concerns=parsed.get("power_concerns", []),
            safety_notes=parsed.get("safety_notes", []),
        )

        return FeasibilityResponse(report=report)

    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI response could not be parsed. Please try again.")
    except KeyError:
        raise HTTPException(status_code=502, detail="AI response was missing required fields. Please try again.")
    except Exception:
        raise HTTPException(status_code=500, detail="Feasibility analysis failed. Please try again.")
