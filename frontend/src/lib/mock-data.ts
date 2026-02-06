import type {
  Driver,
  Project,
  ImpedanceDataPoint,
  ChatMessage,
  CircuitComponent,
  CorrectionNetwork,
} from "@/types";

// Real Thiele-Small parameters for Dayton RS180-8
export const daytonRS180: Driver = {
  id: "dayton-rs180-8",
  manufacturer: "Dayton Audio",
  model: "RS180-8",
  driver_type: "woofer",
  ts_params: {
    re: 6.4,
    le: 0.51,
    fs: 39,
    qms: 4.95,
    qes: 0.47,
    qts: 0.43,
    vas: 30.6,
    bl: 7.6,
    mms: 16.5,
    cms: 1.01,
    rms: 0.815,
    sd: 143,
    xmax: 6.6,
  },
  nominal_impedance: 8,
  power_rating: 60,
  sensitivity: 87.2,
};

export const mockDrivers: Driver[] = [
  daytonRS180,
  {
    id: "sb-sb17nrx",
    manufacturer: "SB Acoustics",
    model: "SB17NRXC35-8",
    driver_type: "midrange",
    ts_params: {
      re: 6.2,
      le: 0.28,
      fs: 46,
      qms: 3.8,
      qes: 0.38,
      qts: 0.35,
      vas: 15.2,
      bl: 6.1,
      mms: 8.5,
      cms: 1.47,
      rms: 0.65,
      sd: 124,
      xmax: 6.0,
    },
    nominal_impedance: 8,
    power_rating: 40,
    sensitivity: 87.5,
  },
  {
    id: "scan-d2604",
    manufacturer: "Scan-Speak",
    model: "D2604/832000",
    driver_type: "tweeter",
    ts_params: {
      re: 5.5,
      le: 0.05,
      fs: 500,
      qms: 2.1,
      qes: 0.78,
      qts: 0.57,
      vas: 0.3,
      bl: 2.8,
      mms: 0.45,
      cms: 0.25,
      rms: 0.67,
      sd: 7.1,
      xmax: 1.0,
    },
    nominal_impedance: 6,
    power_rating: 100,
    sensitivity: 91.0,
  },
  {
    id: "peerless-830869",
    manufacturer: "Peerless",
    model: "830869 SLS-10",
    driver_type: "subwoofer",
    ts_params: {
      re: 6.8,
      le: 1.35,
      fs: 23,
      qms: 6.2,
      qes: 0.42,
      qts: 0.39,
      vas: 82.4,
      bl: 10.2,
      mms: 65,
      cms: 0.73,
      rms: 1.52,
      sd: 346,
      xmax: 10.0,
    },
    nominal_impedance: 8,
    power_rating: 150,
    sensitivity: 86.0,
  },
  {
    id: "tang-band-w4",
    manufacturer: "Tang Band",
    model: "W4-1720",
    driver_type: "full_range",
    ts_params: {
      re: 6.5,
      le: 0.22,
      fs: 68,
      qms: 3.5,
      qes: 0.52,
      qts: 0.45,
      vas: 5.8,
      bl: 4.8,
      mms: 4.2,
      cms: 1.31,
      rms: 0.52,
      sd: 52,
      xmax: 4.0,
    },
    nominal_impedance: 8,
    power_rating: 20,
    sensitivity: 88.5,
  },
];

// Generate impedance curve from TS parameters using the standard lumped-parameter model.
// Z(f) = Re + jωLe + Zmot(f), where Zmot is a parallel RLC (Res, Lces, Cmes).
// Matches engine/impedance.py formulas from Beranek & Mellow (2012) / Small (1972).
export function generateImpedanceCurve(driver: Driver): ImpedanceDataPoint[] {
  const { re, le, fs, qms, qes } = driver.ts_params;
  const points: ImpedanceDataPoint[] = [];

  // Derive motional parameters from Q factors
  const Res = re * qms / qes;
  const omega_s = 2 * Math.PI * fs;
  const Lces = (qes * re) / omega_s;
  const Cmes = 1 / (omega_s * qes * re);

  // Le in henries (input is mH)
  const Le_H = (le ?? 0) / 1000;

  for (let i = 0; i <= 200; i++) {
    const f = 20 * Math.pow(1000, i / 200); // 20Hz to 20kHz log scale
    const omega = 2 * Math.PI * f;

    // Voice coil: jωLe
    const z_le_re = 0;
    const z_le_im = omega * Le_H;

    // Motional impedance: parallel RLC → Y = 1/Res + jωCmes + 1/(jωLces)
    const y_mot_re = 1 / Res;
    const y_mot_im = omega * Cmes - 1 / (omega * Lces);

    // Zmot = 1/Ymot
    const y_mag_sq = y_mot_re * y_mot_re + y_mot_im * y_mot_im;
    const z_mot_re = y_mot_re / y_mag_sq;
    const z_mot_im = -y_mot_im / y_mag_sq;

    // Z_total = Re + jωLe + Zmot
    const z_total_re = re + z_le_re + z_mot_re;
    const z_total_im = z_le_im + z_mot_im;

    const magnitude = Math.sqrt(z_total_re * z_total_re + z_total_im * z_total_im);
    const phase = Math.atan2(z_total_im, z_total_re) * (180 / Math.PI);

    points.push({
      frequency: Math.round(f * 10) / 10,
      magnitude: Math.round(magnitude * 100) / 100,
      phase: Math.round(phase * 100) / 100,
    });
  }

  return points;
}

// Calculate correction network values
// Matches engine/correction.py: Zobel (Rz=Re, Cz=Le/Re²) + Notch (R=Re·Qms/Qes)
export function calculateCorrectionNetwork(driver: Driver): CorrectionNetwork {
  const { re, le, fs, qms, qes } = driver.ts_params;

  // Zobel network: Rz = Re, Cz = Le / Re^2
  const rz = re;
  const cz = (le / 1000) / (re * re); // le in mH → H

  // Resonance notch filter: parallel RLC tuned to fs
  // R_notch = Re * Qms / Qes (NOT Qes/Qms — that was the F-1 bug)
  const r_notch = re * (qms / qes);
  const omega_s = 2 * Math.PI * fs;
  const c_notch = 1 / (omega_s * re * qes);
  const l_notch = (re * qes) / omega_s;

  return {
    zobel: { r: Math.round(rz * 100) / 100, c: cz },
    notch: {
      r: Math.round(r_notch * 100) / 100,
      c: c_notch,
      l: l_notch,
    },
  };
}

// Generate corrected impedance curve using proper parallel impedance model.
// Matches engine/correction.py:calculate_corrected_impedance — Z_total = 1/(1/Z_driver + 1/Z_zobel + 1/Z_notch)
export function generateCorrectedCurve(
  original: ImpedanceDataPoint[],
  network: CorrectionNetwork,
  nominalImpedance: number
): ImpedanceDataPoint[] {
  // We need to recalculate with complex impedances for accurate correction.
  // The original data only has magnitude/phase, so reconstruct complex form.
  return original.map((point) => {
    const omega = 2 * Math.PI * point.frequency;
    const phaseRad = (point.phase * Math.PI) / 180;

    // Reconstruct complex driver impedance from magnitude/phase
    const z_drv_re = point.magnitude * Math.cos(phaseRad);
    const z_drv_im = point.magnitude * Math.sin(phaseRad);

    // Start with driver admittance Y = 1/Z
    const z_drv_mag_sq = z_drv_re * z_drv_re + z_drv_im * z_drv_im;
    let y_total_re = z_drv_re / z_drv_mag_sq;
    let y_total_im = -z_drv_im / z_drv_mag_sq;

    // Zobel network: Z_zobel = Rz + 1/(jωCz) = Rz - j/(ωCz)
    const z_zobel_re = network.zobel.r;
    const z_zobel_im = -1 / (omega * network.zobel.c);
    const z_zobel_mag_sq = z_zobel_re * z_zobel_re + z_zobel_im * z_zobel_im;
    y_total_re += z_zobel_re / z_zobel_mag_sq;
    y_total_im += -z_zobel_im / z_zobel_mag_sq;

    // Notch filter: parallel RLC → Z_notch = 1/(1/R + jωC + 1/(jωL))
    if (network.notch) {
      const y_notch_re = 1 / network.notch.r;
      const y_notch_im = omega * network.notch.c - 1 / (omega * network.notch.l);
      const y_notch_mag_sq = y_notch_re * y_notch_re + y_notch_im * y_notch_im;
      const z_notch_re = y_notch_re / y_notch_mag_sq;
      const z_notch_im = -y_notch_im / y_notch_mag_sq;
      const z_notch_mag_sq = z_notch_re * z_notch_re + z_notch_im * z_notch_im;
      y_total_re += z_notch_re / z_notch_mag_sq;
      y_total_im += -z_notch_im / z_notch_mag_sq;
    }

    // Z_corrected = 1/Y_total
    const y_total_mag_sq = y_total_re * y_total_re + y_total_im * y_total_im;
    const z_corr_re = y_total_re / y_total_mag_sq;
    const z_corr_im = -y_total_im / y_total_mag_sq;
    const corrected_mag = Math.sqrt(z_corr_re * z_corr_re + z_corr_im * z_corr_im);
    const corrected_phase = Math.atan2(z_corr_im, z_corr_re) * (180 / Math.PI);

    return {
      ...point,
      corrected_magnitude: Math.round(corrected_mag * 100) / 100,
      corrected_phase: Math.round(corrected_phase * 100) / 100,
    };
  });
}

export const mockProjects: Project[] = [
  {
    id: "proj-1",
    name: "RS180-8 Impedance Correction",
    description: "Zobel + notch filter for Dayton RS180-8 woofer",
    status: "designing",
    created_at: "2025-01-15T10:30:00Z",
    updated_at: "2025-01-15T14:22:00Z",
  },
  {
    id: "proj-2",
    name: "2-Way Crossover — SB17 + D2604",
    description: "2nd order Linkwitz-Riley crossover at 2.5kHz",
    status: "draft",
    created_at: "2025-01-14T09:00:00Z",
    updated_at: "2025-01-14T09:00:00Z",
  },
  {
    id: "proj-3",
    name: "Subwoofer LPF — Peerless SLS-10",
    description: "4th order Butterworth low-pass at 80Hz",
    status: "complete",
    created_at: "2025-01-10T16:45:00Z",
    updated_at: "2025-01-12T11:30:00Z",
  },
];

export const mockComponents: CircuitComponent[] = [
  { ref: "R1", type: "resistor", value: 6.8, unit: "\u03A9", footprint: "0805", tolerance: "1%", power_rating: 10 },
  { ref: "C1", type: "capacitor", value: 12.5e-6, unit: "F", footprint: "Radial 10mm", tolerance: "5%" },
  { ref: "R2", type: "resistor", value: 67.4, unit: "\u03A9", footprint: "THT Power", tolerance: "1%", power_rating: 10 },
  { ref: "C2", type: "capacitor", value: 330e-6, unit: "F", footprint: "Radial 12.5mm", tolerance: "10%" },
  { ref: "L1", type: "inductor", value: 3.3e-3, unit: "H", footprint: "Toroid 20mm", tolerance: "5%" },
];

export const mockChatMessages: ChatMessage[] = [
  {
    id: "msg-1",
    role: "user",
    content: "Design an impedance correction network for a Dayton RS180-8 woofer",
    timestamp: "2025-01-15T10:30:00Z",
  },
  {
    id: "msg-2",
    role: "assistant",
    content:
      "I'll design an impedance correction network for the Dayton RS180-8. This driver has a nominal impedance of 8\u03A9 with Re=6.4\u03A9, Le=0.51mH, and fs=39Hz.\n\nI recommend a **Zobel network** to flatten the rising impedance from voice coil inductance, combined with a **resonance notch filter** to tame the impedance peak at fs.\n\nLet me calculate the optimal component values...",
    timestamp: "2025-01-15T10:30:05Z",
  },
  {
    id: "msg-3",
    role: "assistant",
    content:
      "Here's the correction network:\n\n**Zobel Network:**\n- R1 = 6.8\u03A9 (E24, target 6.4\u03A9, +6.25% error)\n- C1 = 12.5\u00B5F\n\n**Resonance Notch Filter:**\n- R2 = 68\u03A9 (E24, target 67.4\u03A9)\n- C2 = 330\u00B5F\n- L1 = 3.3mH\n\nThe impedance curve tab now shows the corrected response. The combined impedance stays within \u00B11\u03A9 of 8\u03A9 across the passband.",
    timestamp: "2025-01-15T10:30:15Z",
  },
];
