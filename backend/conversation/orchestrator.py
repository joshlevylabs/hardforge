import json
import os
import re
import logging
from typing import Optional
from datetime import datetime

from anthropic import Anthropic
from fastapi import HTTPException

from backend.conversation.models import (
    ConversationPhase,
    ConversationSession,
    GatheredSpec,
    Message,
)
from backend.conversation.session_store import InMemorySessionStore
from backend.ai.prompts import build_orchestrator_messages, build_spec_confirmation_messages, CIRCUIT_DESIGNER_SYSTEM

logger = logging.getLogger(__name__)

# Required fields per project type for completeness check
REQUIRED_FIELDS = {
    "impedance_correction": ["project_type", "driver_or_ts_params"],
    "passive_crossover": ["project_type", "crossover_freq", "nominal_impedance"],
    "filter": ["project_type", "filter_type", "filter_freq", "nominal_impedance"],
    "amplifier": ["project_type"],
    "power_supply": ["project_type"],
    "custom": ["project_type"],
}

MAX_GATHERING_EXCHANGES = 10


class Orchestrator:
    def __init__(self, session_store: InMemorySessionStore):
        self.session_store = session_store
        self._client: Optional[Anthropic] = None

    def _get_client(self) -> Anthropic:
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
            self._client = Anthropic(api_key=api_key)
        return self._client

    async def handle_message(
        self, session: ConversationSession, user_content: str
    ) -> Message:
        """Route a user message based on current phase and return assistant response."""

        # Add user message to session
        user_msg = Message(role="user", content=user_content)
        session.messages.append(user_msg)

        if session.phase in (ConversationPhase.GATHERING, ConversationPhase.CLARIFYING):
            response = await self._handle_gathering(session, user_content)
        elif session.phase == ConversationPhase.CONFIRMING:
            response = await self._handle_confirming(session, user_content)
        elif session.phase == ConversationPhase.DESIGNING:
            response = await self._handle_designing(session)
        elif session.phase == ConversationPhase.REVIEWING:
            response = await self._handle_reviewing(session, user_content)
        elif session.phase == ConversationPhase.COMPLETE:
            response = Message(
                role="assistant",
                content="This design is complete. Start a new conversation to create another design.",
            )
        else:
            response = Message(role="assistant", content="Unexpected state. Please start a new conversation.")

        session.messages.append(response)
        await self.session_store.update_session(session)
        return response

    async def _handle_gathering(
        self, session: ConversationSession, user_content: str
    ) -> Message:
        """GATHERING/CLARIFYING phase: extract specs, ask clarifying questions."""

        # Build conversation history for context
        history = [
            {"role": m.role, "content": m.content}
            for m in session.messages[:-1]  # exclude the just-added user message
            if m.role in ("user", "assistant")
        ]

        system_prompt, messages = build_orchestrator_messages(
            user_message=user_content,
            phase=session.phase.value,
            gathered_spec=session.gathered_spec.model_dump(),
            conversation_history=history,
        )

        client = self._get_client()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=system_prompt,
            messages=messages,
            temperature=0.4,
        )

        response_text = response.content[0].text

        # Extract spec updates from <spec_update> blocks
        spec_updates = re.findall(r"<spec_update>\s*(.*?)\s*</spec_update>", response_text, re.DOTALL)
        for update_json in spec_updates:
            try:
                updates = json.loads(update_json)
                self._apply_spec_updates(session.gathered_spec, updates)
            except json.JSONDecodeError:
                logger.warning("Failed to parse spec_update JSON")

        # Remove <spec_update> blocks from the visible response
        clean_response = re.sub(r"<spec_update>.*?</spec_update>", "", response_text, flags=re.DOTALL).strip()

        # Check if spec is complete enough to move to CONFIRMING
        if self._is_spec_complete(session.gathered_spec):
            session.phase = ConversationPhase.CONFIRMING
            # Generate confirmation summary
            confirm_msg = await self._generate_confirmation(session)
            clean_response = confirm_msg
        else:
            session.phase = ConversationPhase.CLARIFYING

        # Safety: force transition after too many exchanges
        user_msg_count = sum(1 for m in session.messages if m.role == "user")
        if user_msg_count >= MAX_GATHERING_EXCHANGES and session.phase != ConversationPhase.CONFIRMING:
            session.phase = ConversationPhase.CONFIRMING
            confirm_msg = await self._generate_confirmation(session)
            clean_response += "\n\n" + confirm_msg

        return Message(role="assistant", content=clean_response)

    def _apply_spec_updates(self, spec: GatheredSpec, updates: dict) -> None:
        """Merge extracted spec updates into the gathered spec."""
        if "project_type" in updates:
            spec.project_type = updates["project_type"]
        if "driver" in updates:
            if spec.driver is None:
                spec.driver = {}
            spec.driver.update(updates["driver"])
        if "target_specs" in updates:
            spec.target_specs.update(updates["target_specs"])
        if "constraints" in updates:
            spec.constraints.update(updates["constraints"])
        if "firmware_requirements" in updates:
            spec.firmware_requirements = updates["firmware_requirements"]
        if "additional_notes" in updates:
            if isinstance(updates["additional_notes"], list):
                spec.additional_notes.extend(updates["additional_notes"])
            else:
                spec.additional_notes.append(str(updates["additional_notes"]))

    def _is_spec_complete(self, spec: GatheredSpec) -> bool:
        """Deterministic completeness check based on project type."""
        if not spec.project_type:
            return False

        required = REQUIRED_FIELDS.get(spec.project_type, ["project_type"])

        for field in required:
            if field == "project_type":
                continue  # already checked
            elif field == "driver_or_ts_params":
                has_driver = spec.driver and (spec.driver.get("model") or spec.driver.get("ts_params"))
                has_ts = spec.target_specs.get("ts_params") or spec.target_specs.get("re")
                if not has_driver and not has_ts:
                    return False
            elif field == "crossover_freq":
                if not spec.target_specs.get("crossover_freq"):
                    return False
            elif field == "nominal_impedance":
                if not spec.target_specs.get("nominal_impedance"):
                    return False
            elif field == "filter_type":
                if not spec.target_specs.get("filter_type"):
                    return False
            elif field == "filter_freq":
                if not spec.target_specs.get("filter_freq"):
                    return False

        return True

    async def _generate_confirmation(self, session: ConversationSession) -> str:
        """Generate a spec confirmation summary using Claude."""
        system, messages = build_spec_confirmation_messages(
            session.gathered_spec.model_dump()
        )

        client = self._get_client()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            system=system,
            messages=messages,
            temperature=0.2,
        )

        return response.content[0].text

    async def _handle_confirming(
        self, session: ConversationSession, user_content: str
    ) -> Message:
        """CONFIRMING phase: parse user's confirmation or corrections."""
        content_lower = user_content.lower().strip()

        # Check for confirmation signals
        confirm_signals = ["yes", "confirm", "looks good", "correct", "go ahead", "proceed", "lgtm", "ok", "okay", "that's right", "yep", "sure"]
        is_confirmed = any(signal in content_lower for signal in confirm_signals)

        if is_confirmed:
            session.phase = ConversationPhase.DESIGNING
            # Immediately run design
            return await self._handle_designing(session)
        else:
            # User wants to correct something — go back to gathering
            session.phase = ConversationPhase.GATHERING
            return await self._handle_gathering(session, user_content)

    async def _handle_designing(self, session: ConversationSession) -> Message:
        """DESIGNING phase: convert spec to DesignIntent, run feasibility, calculate circuit."""
        spec = session.gathered_spec
        project_type = spec.project_type or "custom"
        topology_name = self._select_topology(project_type, spec)

        # Check if we can do engine-based calculation (need a calculable topology + params)
        can_calculate = topology_name is not None and self._has_required_params(topology_name, spec)

        if can_calculate:
            return await self._run_engine_design(session, topology_name, spec)
        else:
            return await self._run_ai_design(session, spec)

    def _has_required_params(self, topology_name: str, spec: GatheredSpec) -> bool:
        """Check if we have the parameters needed for engine calculation."""
        has_driver = spec.driver and spec.driver.get("model")
        has_ts = spec.target_specs.get("re") or spec.target_specs.get("ts_params")

        if topology_name == "zobel":
            return has_driver or has_ts
        elif topology_name == "passive_crossover":
            return bool(spec.target_specs.get("crossover_freq") and spec.target_specs.get("nominal_impedance"))
        elif topology_name in ("rc_filter", "rl_filter", "rlc_filter"):
            return bool(spec.target_specs.get("filter_freq") and spec.target_specs.get("nominal_impedance"))
        return False

    async def _run_engine_design(self, session: ConversationSession, topology_name: str, spec: GatheredSpec) -> Message:
        """Run deterministic engine calculation for supported topologies."""
        try:
            from engine.topology import calculate_topology
            from engine.components import snap_to_e_series, engineering_notation
            from engine.ts_database import DriverDatabase

            # Look up driver if referenced by name
            ts_params_dict = None
            if spec.driver and spec.driver.get("model"):
                db = DriverDatabase()
                results = db.search(query=spec.driver["model"])
                if results:
                    driver_data = results[0]
                    ts_params_dict = {
                        "re": driver_data["re"],
                        "le": driver_data.get("le", 0),
                        "fs": driver_data["fs"],
                        "qms": driver_data["qms"],
                        "qes": driver_data["qes"],
                        "qts": driver_data["qts"],
                        "vas": driver_data.get("vas"),
                        "bl": driver_data.get("bl"),
                        "mms": driver_data.get("mms"),
                    }

            # Build params for engine
            params = {}
            if ts_params_dict:
                params.update(ts_params_dict)
            if spec.target_specs.get("nominal_impedance"):
                params["impedance"] = spec.target_specs["nominal_impedance"]
            if spec.target_specs.get("crossover_freq"):
                params["crossover_freq"] = spec.target_specs["crossover_freq"]
            if spec.target_specs.get("crossover_type"):
                params["alignment"] = spec.target_specs["crossover_type"]
            if spec.target_specs.get("crossover_order"):
                params["order"] = spec.target_specs["crossover_order"]
            if spec.target_specs.get("filter_freq"):
                params["cutoff_freq"] = spec.target_specs["filter_freq"]
            if spec.target_specs.get("filter_type"):
                params["filter_type"] = spec.target_specs["filter_type"]

            # Calculate component values
            comp_values = calculate_topology(topology_name, params)

            # Build CircuitComponent list
            components = []
            warnings = []
            for ref, comp_data in comp_values.items():
                if not isinstance(comp_data, dict) or "value" not in comp_data:
                    continue

                comp_type_str = comp_data.get("type", "resistor")
                value = comp_data["value"]
                unit = comp_data.get("unit", "")
                snapped_val, snap_err = snap_to_e_series(value, "E24")
                snap_info = {"target": value, "actual": snapped_val, "error_pct": snap_err}

                if abs(snap_err) > 5.0:
                    warnings.append(f"{ref}: E24 snap error is {snap_err:.1f}% — consider E48/E96")

                components.append({
                    "ref": ref,
                    "type": comp_type_str,
                    "value": snapped_val,
                    "unit": unit,
                    "description": comp_data.get("description", f"{comp_type_str} {engineering_notation(value, unit)}"),
                    "e_series_snapped": snap_info,
                })

            # Store design result
            session.circuit_design = {
                "topology": topology_name,
                "components": components,
                "connections": [],
                "warnings": warnings,
            }
            session.selected_topology = topology_name
            session.phase = ConversationPhase.REVIEWING

            # Format response
            comp_summary = "\n".join(
                f"  - **{c['ref']}**: {engineering_notation(c['value'], c['unit'])} ({c['description']})"
                for c in components
            )

            response_text = f"""Design complete! Here's your **{topology_name.replace('_', ' ').title()}** circuit:

**Components:**
{comp_summary}

**Topology:** {topology_name}
"""
            if warnings:
                response_text += "\n**Warnings:**\n" + "\n".join(f"  - {w}" for w in warnings)

            response_text += "\n\nWould you like to:\n- **Export** the schematic or BOM\n- **Modify** any component values\n- **Start over** with different parameters"

            return Message(role="assistant", content=response_text)

        except Exception as e:
            logger.error(f"Engine design calculation failed: {e}", exc_info=True)
            # Fall back to AI-based design recommendation
            return await self._run_ai_design(session, session.gathered_spec)

    async def _run_ai_design(self, session: ConversationSession, spec: GatheredSpec) -> Message:
        """Use Claude to generate a design recommendation for projects the engine can't calculate directly."""
        history = [
            {"role": m.role, "content": m.content}
            for m in session.messages
            if m.role in ("user", "assistant")
        ]

        system_prompt = f"""{CIRCUIT_DESIGNER_SYSTEM}

The user has confirmed these specifications:
{json.dumps(spec.model_dump(), indent=2)}

This project type falls outside the deterministic engine's supported topologies (zobel, notch, crossover, basic filters). Provide a detailed design recommendation including:
1. Recommended architecture and block diagram
2. Key components and subsystems
3. Design considerations and trade-offs
4. Suggested next steps for implementation

Be specific and actionable. Use standard engineering terminology."""

        client = self._get_client()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=3000,
            system=system_prompt,
            messages=history[-10:] + [{"role": "user", "content": "Generate the design recommendation based on the confirmed specifications."}],
            temperature=0.3,
        )

        response_text = response.content[0].text

        # Store as design (no components, but captures the recommendation)
        session.circuit_design = {
            "topology": "custom",
            "components": [],
            "connections": [],
            "warnings": ["This is an AI-generated design recommendation — component values require manual verification."],
        }
        session.phase = ConversationPhase.REVIEWING

        return Message(role="assistant", content=response_text)

    def _select_topology(self, project_type: str, spec: GatheredSpec) -> Optional[str]:
        """Select the best topology based on project type and specs. Returns None if no engine topology applies."""
        if project_type == "impedance_correction":
            return "zobel"
        elif project_type == "passive_crossover":
            return "passive_crossover"
        elif project_type == "filter":
            return "rc_filter"
        else:
            return None  # Custom/amplifier/power_supply — use AI design

    async def _handle_reviewing(
        self, session: ConversationSession, user_content: str
    ) -> Message:
        """REVIEWING phase: answer questions about the design or accept modifications."""
        content_lower = user_content.lower().strip()

        # Check for completion signals
        done_signals = ["done", "accept", "export", "finish", "complete", "ship it", "looks good"]
        if any(signal in content_lower for signal in done_signals):
            session.phase = ConversationPhase.COMPLETE
            return Message(
                role="assistant",
                content="Design finalized! You can export the schematic, BOM, or KiCad project from the export panel. Start a new conversation anytime to create another design.",
            )

        # Check if user wants to modify (go back to gathering)
        modify_signals = ["change", "modify", "update", "different", "start over", "redo"]
        if any(signal in content_lower for signal in modify_signals):
            session.phase = ConversationPhase.GATHERING
            return await self._handle_gathering(session, user_content)

        # Otherwise, use Claude to answer questions about the design
        history = [
            {"role": m.role, "content": m.content}
            for m in session.messages[:-1]
            if m.role in ("user", "assistant")
        ]

        system_prompt, messages = build_orchestrator_messages(
            user_message=user_content,
            phase="reviewing",
            gathered_spec=session.gathered_spec.model_dump(),
            conversation_history=history,
        )

        client = self._get_client()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=system_prompt,
            messages=messages,
            temperature=0.3,
        )

        clean_response = re.sub(
            r"<spec_update>.*?</spec_update>", "", response.content[0].text, flags=re.DOTALL
        ).strip()

        return Message(role="assistant", content=clean_response)
