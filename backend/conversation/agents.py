from dataclasses import dataclass
from enum import Enum


class SubAgent(str, Enum):
    REQUIREMENTS_GATHERER = "requirements_gatherer"
    CIRCUIT_DESIGNER = "circuit_designer"
    FIRMWARE_GENERATOR = "firmware_generator"
    BOM_OPTIMIZER = "bom_optimizer"
    DESIGN_REVIEWER = "design_reviewer"


@dataclass
class AgentConfig:
    system_prompt: str  # Key into prompts module
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 2000
    temperature: float = 0.3


AGENT_CONFIGS: dict[SubAgent, AgentConfig] = {
    SubAgent.REQUIREMENTS_GATHERER: AgentConfig(
        system_prompt="ORCHESTRATOR_SYSTEM",
        max_tokens=2000,
        temperature=0.4,
    ),
    SubAgent.CIRCUIT_DESIGNER: AgentConfig(
        system_prompt="CIRCUIT_DESIGNER_SYSTEM",
        max_tokens=3000,
        temperature=0.2,
    ),
    SubAgent.FIRMWARE_GENERATOR: AgentConfig(
        system_prompt="FIRMWARE_GENERATOR_SYSTEM",
        max_tokens=4000,
        temperature=0.2,
    ),
    SubAgent.BOM_OPTIMIZER: AgentConfig(
        system_prompt="BOM_OPTIMIZER_SYSTEM",
        max_tokens=2000,
        temperature=0.1,
    ),
    SubAgent.DESIGN_REVIEWER: AgentConfig(
        system_prompt="DESIGN_REVIEWER_SYSTEM",
        max_tokens=2000,
        temperature=0.3,
    ),
}
