"""Pydantic models for HardForge API requests and responses."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums ---

class ProjectType(str, Enum):
    IMPEDANCE_CORRECTION = "impedance_correction"
    PASSIVE_CROSSOVER = "passive_crossover"
    FILTER = "filter"
    AMPLIFIER = "amplifier"
    POWER_SUPPLY = "power_supply"
    CUSTOM = "custom"


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class ComponentType(str, Enum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DRIVER = "driver"
    OPAMP = "opamp"
    TRANSISTOR = "transistor"
    DIODE = "diode"


# --- TS Parameters ---

class TSParams(BaseModel):
    """Thiele-Small parameters for a loudspeaker driver."""
    re: float = Field(..., gt=0, description="DC resistance (Ohms)")
    le: float = Field(0.0, ge=0, description="Voice coil inductance (mH)")
    fs: float = Field(..., gt=0, description="Resonance frequency (Hz)")
    qms: float = Field(..., gt=0, description="Mechanical Q factor")
    qes: float = Field(..., gt=0, description="Electrical Q factor")
    qts: float = Field(..., gt=0, description="Total Q factor")
    vas: Optional[float] = Field(None, ge=0, description="Equivalent compliance volume (liters)")
    bl: Optional[float] = Field(None, ge=0, description="Force factor (T·m)")
    mms: Optional[float] = Field(None, ge=0, description="Moving mass (grams)")
    cms: Optional[float] = Field(None, ge=0, description="Compliance (mm/N)")
    rms: Optional[float] = Field(None, ge=0, description="Mechanical resistance (kg/s)")
    sd: Optional[float] = Field(None, ge=0, description="Effective piston area (cm²)")
    xmax: Optional[float] = Field(None, ge=0, description="Maximum excursion (mm)")


# --- Design Intent ---

class DriverReference(BaseModel):
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    ts_params: Optional[TSParams] = None


class TargetSpecs(BaseModel):
    driver: Optional[DriverReference] = None
    impedance_target: Optional[float] = Field(None, description="Target impedance (Ohms)")
    crossover_freq: Optional[float] = Field(None, description="Crossover frequency (Hz)")
    crossover_type: Optional[str] = Field(None, description="Crossover type (butterworth, linkwitz_riley, bessel)")
    crossover_order: Optional[int] = Field(None, ge=1, le=4, description="Crossover order (1-4)")
    filter_type: Optional[str] = Field(None, description="Filter type (lowpass, highpass, bandpass, bandstop)")
    filter_freq: Optional[float] = Field(None, description="Filter frequency (Hz)")
    nominal_impedance: Optional[float] = Field(None, description="System nominal impedance (Ohms)")


class DesignConstraints(BaseModel):
    budget: Optional[float] = None
    form_factor: Optional[str] = Field(None, description="smd, through_hole, or mixed")
    max_power: Optional[float] = Field(None, description="Maximum power (Watts)")


class DesignIntent(BaseModel):
    """Structured output from intent parsing."""
    project_type: ProjectType
    target_specs: TargetSpecs
    constraints: DesignConstraints = DesignConstraints()
    components_mentioned: list[str] = []
    ambiguities: list[str] = []
    raw_description: str = ""


# --- Circuit Design ---

class ESeriesSnap(BaseModel):
    target: float
    actual: float
    error_pct: float


class CircuitComponent(BaseModel):
    ref: str = Field(..., description="Reference designator (R1, C1, L1)")
    type: ComponentType
    value: float
    unit: str
    footprint: str = ""
    power_rating: Optional[float] = None
    tolerance: Optional[str] = None
    e_series_snapped: Optional[ESeriesSnap] = None
    description: str = ""


class Connection(BaseModel):
    from_pin: str
    to_pin: str
    net: str


class Subcircuit(BaseModel):
    name: str
    type: str
    components: list[str]


class CircuitDesign(BaseModel):
    """Complete circuit design with components and connections."""
    topology: str
    components: list[CircuitComponent]
    connections: list[Connection]
    subcircuits: list[Subcircuit] = []
    warnings: list[str] = []
    simulation_results: Optional[dict] = None


# --- API Request/Response Models ---

class ParseIntentRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=5000)
    context: Optional[str] = None


class ParseIntentResponse(BaseModel):
    intent: DesignIntent
    confidence: float = Field(..., ge=0, le=1)
    suggestions: list[str] = []


class FeasibilityRequest(BaseModel):
    intent: DesignIntent


class DesignOption(BaseModel):
    name: str
    description: str
    topology: str
    pros: list[str]
    cons: list[str]
    estimated_components: int
    estimated_cost: Optional[float] = None


class FeasibilityReport(BaseModel):
    feasible: bool
    summary: str
    challenges: list[str]
    design_options: list[DesignOption]
    power_concerns: list[str] = []
    safety_notes: list[str] = []


class FeasibilityResponse(BaseModel):
    report: FeasibilityReport


class DesignCircuitRequest(BaseModel):
    intent: DesignIntent
    selected_topology: str
    overrides: Optional[dict] = None


class DesignCircuitResponse(BaseModel):
    design: CircuitDesign
    bom_summary: dict = {}


class ImpedanceRequest(BaseModel):
    ts_params: TSParams
    freq_start: float = Field(20.0, gt=0)
    freq_end: float = Field(20000.0, gt=0)
    num_points: int = Field(500, gt=10, le=5000)


class ImpedanceResponse(BaseModel):
    frequency: list[float]
    magnitude: list[float]
    phase: list[float]


class CorrectionRequest(BaseModel):
    ts_params: TSParams
    target_impedance: Optional[float] = None
    include_zobel: bool = True
    include_notch: bool = True
    e_series: str = "E24"


class CorrectionResponse(BaseModel):
    zobel: Optional[dict] = None
    notch: Optional[dict] = None
    components: list[CircuitComponent]
    corrected_impedance: ImpedanceResponse


class SchematicRequest(BaseModel):
    design: CircuitDesign


class SchematicResponse(BaseModel):
    svg: str
    kicad_sch: Optional[str] = None


class BOMRequest(BaseModel):
    design: CircuitDesign


class BOMEntry(BaseModel):
    ref: str
    value: str
    description: str
    footprint: str
    quantity: int = 1
    estimated_price: Optional[float] = None


class BOMResponse(BaseModel):
    entries: list[BOMEntry]
    total_cost: Optional[float] = None
    csv: str


class DriverInfo(BaseModel):
    id: str
    manufacturer: str
    model: str
    driver_type: str
    re: float
    le: Optional[float] = None
    fs: float
    qms: float
    qes: float
    qts: float
    vas: Optional[float] = None
    bl: Optional[float] = None
    mms: Optional[float] = None
    nominal_impedance: float = 8.0
    power_rating: Optional[float] = None
    sensitivity: Optional[float] = None


class DriverListResponse(BaseModel):
    drivers: list[DriverInfo]
    total: int
