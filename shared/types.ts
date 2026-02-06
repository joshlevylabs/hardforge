/**
 * Shared TypeScript types for HardForge API contracts.
 * These types mirror the Pydantic models in backend/models.py.
 */

export type ProjectType =
  | 'impedance_correction'
  | 'passive_crossover'
  | 'filter'
  | 'amplifier'
  | 'power_supply'
  | 'custom';

export type SubscriptionTier = 'free' | 'pro' | 'team';

export type ComponentType =
  | 'resistor'
  | 'capacitor'
  | 'inductor'
  | 'driver'
  | 'opamp'
  | 'transistor'
  | 'diode';

export interface TSParams {
  re: number;
  le?: number;
  fs: number;
  qms: number;
  qes: number;
  qts: number;
  vas?: number;
  bl?: number;
  mms?: number;
  cms?: number;
  rms?: number;
  sd?: number;
  xmax?: number;
}

export interface DriverReference {
  manufacturer?: string;
  model?: string;
  ts_params?: TSParams;
}

export interface TargetSpecs {
  driver?: DriverReference;
  impedance_target?: number;
  crossover_freq?: number;
  crossover_type?: string;
  crossover_order?: number;
  filter_type?: string;
  filter_freq?: number;
  nominal_impedance?: number;
}

export interface DesignConstraints {
  budget?: number;
  form_factor?: 'smd' | 'through_hole' | 'mixed';
  max_power?: number;
}

export interface DesignIntent {
  project_type: ProjectType;
  target_specs: TargetSpecs;
  constraints: DesignConstraints;
  components_mentioned: string[];
  ambiguities: string[];
  raw_description: string;
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
  footprint?: string;
  power_rating?: number;
  tolerance?: string;
  e_series_snapped?: ESeriesSnap;
  description?: string;
}

export interface Connection {
  from_pin: string;
  to_pin: string;
  net: string;
}

export interface CircuitDesign {
  topology: string;
  components: CircuitComponent[];
  connections: Connection[];
  subcircuits?: { name: string; type: string; components: string[] }[];
  warnings: string[];
  simulation_results?: Record<string, unknown>;
}

export interface DesignOption {
  name: string;
  description: string;
  topology: string;
  pros: string[];
  cons: string[];
  estimated_components: number;
  estimated_cost?: number;
}

export interface FeasibilityReport {
  feasible: boolean;
  summary: string;
  challenges: string[];
  design_options: DesignOption[];
  power_concerns: string[];
  safety_notes: string[];
}

export interface ImpedanceData {
  frequency: number[];
  magnitude: number[];
  phase: number[];
}

export interface CorrectionResult {
  zobel?: Record<string, unknown>;
  notch?: Record<string, unknown>;
  components: CircuitComponent[];
  corrected_impedance: ImpedanceData;
}

export interface BOMEntry {
  ref: string;
  value: string;
  description: string;
  footprint: string;
  quantity: number;
  estimated_price?: number;
}

export interface DriverInfo {
  id: string;
  manufacturer: string;
  model: string;
  driver_type: string;
  re: number;
  le?: number;
  fs: number;
  qms: number;
  qes: number;
  qts: number;
  vas?: number;
  bl?: number;
  mms?: number;
  nominal_impedance: number;
  power_rating?: number;
  sensitivity?: number;
}
