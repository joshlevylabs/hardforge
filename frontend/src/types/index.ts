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

export interface CircuitDesign {
  topology: string;
  components: CircuitComponent[];
  connections: CircuitConnection[];
  subcircuits: Subcircuit[];
  warnings: string[];
  simulation_results?: Record<string, unknown>;
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

export type PipelineStep = "intent" | "feasibility" | "design" | "schematic" | "export";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}
