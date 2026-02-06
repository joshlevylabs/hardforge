"""Intent parsing route — NL description → structured DesignIntent."""

import json
import os

from anthropic import Anthropic
from fastapi import APIRouter, HTTPException

from backend.ai.prompts import INTENT_PARSING_SYSTEM, build_intent_messages
from backend.models import (
    DesignConstraints,
    DesignIntent,
    DriverReference,
    ParseIntentRequest,
    ParseIntentResponse,
    ProjectType,
    TargetSpecs,
)

router = APIRouter()

client = None


def get_client() -> Anthropic:
    global client
    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY not configured"
            )
        client = Anthropic(api_key=api_key)
    return client


@router.post("/parse-intent", response_model=ParseIntentResponse)
async def parse_intent(request: ParseIntentRequest):
    """Parse a natural language hardware description into structured design intent."""
    try:
        ai_client = get_client()
        messages = build_intent_messages(request.description, request.context)

        response = ai_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=INTENT_PARSING_SYSTEM,
            messages=messages,
        )

        # Extract JSON from response
        response_text = response.content[0].text.strip()
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        parsed = json.loads(response_text)

        # Build DesignIntent from parsed JSON
        driver_ref = None
        if parsed.get("target_specs", {}).get("driver"):
            d = parsed["target_specs"]["driver"]
            driver_ref = DriverReference(
                manufacturer=d.get("manufacturer"),
                model=d.get("model"),
            )

        target_specs = TargetSpecs(
            driver=driver_ref,
            impedance_target=parsed.get("target_specs", {}).get("impedance_target"),
            crossover_freq=parsed.get("target_specs", {}).get("crossover_freq"),
            crossover_type=parsed.get("target_specs", {}).get("crossover_type"),
            crossover_order=parsed.get("target_specs", {}).get("crossover_order"),
            filter_type=parsed.get("target_specs", {}).get("filter_type"),
            filter_freq=parsed.get("target_specs", {}).get("filter_freq"),
            nominal_impedance=parsed.get("target_specs", {}).get("nominal_impedance"),
        )

        constraints = DesignConstraints(
            budget=parsed.get("constraints", {}).get("budget"),
            form_factor=parsed.get("constraints", {}).get("form_factor"),
            max_power=parsed.get("constraints", {}).get("max_power"),
        )

        intent = DesignIntent(
            project_type=ProjectType(parsed["project_type"]),
            target_specs=target_specs,
            constraints=constraints,
            components_mentioned=parsed.get("components_mentioned", []),
            ambiguities=parsed.get("ambiguities", []),
            raw_description=request.description,
        )

        # Confidence based on ambiguity count
        ambiguity_count = len(intent.ambiguities)
        confidence = max(0.3, 1.0 - (ambiguity_count * 0.15))

        suggestions = []
        if ambiguity_count > 0:
            suggestions.append("Consider providing more details to resolve ambiguities")
        if not intent.target_specs.driver and intent.project_type in (
            ProjectType.IMPEDANCE_CORRECTION, ProjectType.PASSIVE_CROSSOVER
        ):
            suggestions.append("Specifying a driver model enables more accurate calculations")

        return ParseIntentResponse(
            intent=intent,
            confidence=confidence,
            suggestions=suggestions,
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="AI response could not be parsed. Please try again."
        )
    except KeyError:
        raise HTTPException(
            status_code=502,
            detail="AI response was missing required fields. Please try again."
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Intent parsing failed. Please try again or simplify your description."
        )
