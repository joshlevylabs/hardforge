export type SubscriptionTier = "free" | "pro" | "team";

export type ProjectStatus = "draft" | "designing" | "complete" | "archived";

export type DriverType = "woofer" | "midrange" | "tweeter" | "full_range" | "subwoofer";

export type ProjectType =
  | "impedance_correction"
  | "passive_crossover"
  | "filter"
  | "amplifier"
  | "power_supply"
  | "custom";

export type ComponentType =
  | "resistor"
  | "capacitor"
  | "inductor"
  | "driver"
  | "opamp"
  | "diode"
  | "transistor";

export type ExportType =
  | "schematic_svg"
  | "kicad_project"
  | "gerber_zip"
  | "bom_csv"
  | "bom_json"
  | "netlist";

export type ImpedanceSource = "calculated" | "measured" | "user_upload";

export interface TSParams {
  re: number;
  le: number;
  fs: number;
  qms: number;
  qes: number;
  qts: number;
  vas: number;
  bl: number;
  mms: number;
  cms: number;
  rms: number;
  sd: number;
  xmax: number;
}

export interface Driver {
  id: string;
  manufacturer: string;
  model: string;
  driver_type: DriverType;
  ts_params: TSParams;
  nominal_impedance: number;
  power_rating: number;
  sensitivity: number;
  source_url?: string;
}

export interface DesignIntent {
  project_type: ProjectType;
  target_specs: {
    driver?: { manufacturer: string; model: string; ts_params: TSParams };
    impedance_target?: number;
    crossover_freq?: number;
    crossover_type?: string;
    filter_type?: string;
    filter_freq?: number;
  };
  constraints: {
    budget?: number;
    form_factor?: "smd" | "through_hole" | "mixed";
    max_power?: number;
  };
  components_mentioned: string[];
  ambiguities: string[];
}

export interface ESeriesSnap {
  target: number;
  actual: number;
  error_pct: number;
}

export interface CircuitComponent {
  ref: string;
  type: ComponentType;
  value: number;
  unit: string;
  footprint: string;
  power_rating?: number;
  tolerance?: string;
  e_series_snapped?: ESeriesSnap;
}

export interface CircuitConnection {
  from: string;
  to: string;
  net: string;
}

export interface Subcircuit {
  name: string;
  type: string;
  components: string[];
}

export interface Block {
  id: string;
  name: string;
  type: string; // "subsystem" | "module" | "interface" | "sensor" | "actuator"
  description: string;
  inputs: string[];
  outputs: string[];
  specs: Record<string, string>;
}

export interface BlockConnection {
  from_block: string;
  to_block: string;
  signal_name: string;
  signal_type: "power" | "data" | "analog" | "digital" | "control";
}

export interface CircuitDesign {
  topology: string;
  components: CircuitComponent[];
  connections: CircuitConnection[];
  subcircuits?: Subcircuit[];
  warnings: string[];
  simulation_results?: Record<string, unknown>;
  blocks?: Block[];
  block_connections?: BlockConnection[];
  design_summary?: string;
}

export interface ImpedanceCurve {
  id: string;
  source: ImpedanceSource;
  frequency: number[];
  magnitude: number[];
  phase: number[];
}

export interface ImpedanceDataPoint {
  frequency: number;
  magnitude: number;
  phase: number;
  corrected_magnitude?: number;
  corrected_phase?: number;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  design_intent?: DesignIntent;
  circuit_design?: CircuitDesign;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  subscription_tier: SubscriptionTier;
  designs_this_month: number;
}

export interface FeasibilityReport {
  feasible: boolean;
  confidence: number;
  reasoning: string;
  suggestions: string[];
  warnings: string[];
}

export interface CorrectionNetwork {
  zobel: { r: number; c: number };
  notch?: { r: number; c: number; l: number };
}

// --- Distributor / Enriched BOM ---

export interface PriceBreak {
  quantity: number;
  unit_price: number;
}

export interface DistributorOption {
  distributor: string;
  sku: string;
  unit_price: number;
  stock: number;
  url: string;
  price_breaks: PriceBreak[];
}

export interface BOMEntry {
  ref: string;
  value: string;
  description: string;
  footprint: string;
  quantity: number;
  estimated_price?: number;
}

export interface EnrichedBOMEntry extends BOMEntry {
  mpn?: string;
  manufacturer?: string;
  distributor_options: DistributorOption[];
  best_price?: number;
}

export interface EnrichedBOMResponse {
  entries: EnrichedBOMEntry[];
  total_cost?: number;
  total_best_price?: number;
  csv: string;
  enrichment_status: "full" | "partial" | "unavailable";
}

export type PipelineStep = "intent" | "feasibility" | "design" | "schematic" | "export";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// --- Conversation Types ---

export type ConversationPhase =
  | "gathering"
  | "clarifying"
  | "confirming"
  | "designing"
  | "reviewing"
  | "complete";

export interface GatheredSpec {
  project_type: string | null;
  driver: { manufacturer?: string; model?: string; ts_params?: TSParams } | null;
  target_specs: Record<string, unknown>;
  constraints: Record<string, unknown>;
  firmware_requirements: string | null;
  additional_notes: string[];
}

export interface ConversationSession {
  id: string;
  phase: ConversationPhase;
  messages: ChatMessage[];
  gathered_spec: GatheredSpec;
  design_intent: Record<string, unknown> | null;
  feasibility_report: Record<string, unknown> | null;
  circuit_design: CircuitDesign | null;
  selected_topology: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationSummary {
  id: string;
  phase: ConversationPhase;
  message_count: number;
  project_type: string | null;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface SendMessageResponse {
  session_id: string;
  message: ChatMessage;
  phase: ConversationPhase;
  gathered_spec: GatheredSpec | null;
  circuit_design: CircuitDesign | null;
}
