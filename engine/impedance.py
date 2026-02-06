"""
Loudspeaker impedance modeling from Thiele-Small parameters.

Uses the standard lumped-parameter equivalent circuit model as described
in Beranek & Mellow (2012) and Small (1972).

Electrical equivalent circuit:
    Z(f) = Re + j·2πf·Le + Zmot(f)

Where Zmot is the motional impedance (parallel RLC):
    Cmes = Mms / BL²       (represents moving mass)
    Lces = BL² · Cms        (represents compliance)
    Res  = BL² / Rms        (represents mechanical losses)
    Zmot = 1 / (1/Res + j·2πf·Cmes + 1/(j·2πf·Lces))

When BL/Mms/Cms/Rms are not available, use Q-factor equivalents:
    Res  = Re · Qms / Qes
    Lces = Qes · Re / (2πfs)
    Cmes = 1 / (2πfs · Qes · Re)
"""

import numpy as np
from typing import Dict, Tuple, Optional
import csv
import io


def generate_frequencies(
    start: float = 20.0,
    end: float = 20000.0,
    num_points: int = 500,
) -> np.ndarray:
    """Generate logarithmically-spaced frequency array (Hz)."""
    return np.logspace(np.log10(start), np.log10(end), num_points)


def _motional_params_from_ts(ts: Dict) -> Tuple[float, float, float]:
    """
    Derive motional impedance parameters from TS parameters.

    If BL, Mms, Cms, Rms are available, use direct formulas.
    Otherwise, derive from Re, fs, Qms, Qes.

    Returns (Res, Lces, Cmes) in SI units (Ohms, Henries, Farads).
    """
    Re = ts['re']
    fs = ts['fs']

    if all(k in ts and ts[k] is not None for k in ('bl', 'mms', 'cms', 'rms')):
        BL = ts['bl']               # T·m
        Mms = ts['mms'] * 1e-3      # grams → kg
        Cms = ts['cms'] * 1e-3      # mm/N → m/N
        Rms = ts['rms']             # kg/s (mechanical Ohms)

        Cmes = Mms / (BL ** 2)
        Lces = (BL ** 2) * Cms
        Res = (BL ** 2) / Rms
    else:
        Qms = ts['qms']
        Qes = ts['qes']

        Res = Re * Qms / Qes
        Lces = Qes * Re / (2 * np.pi * fs)
        Cmes = 1.0 / (2 * np.pi * fs * Qes * Re)

    return Res, Lces, Cmes


def calculate_impedance(
    ts_params: Dict,
    frequencies: np.ndarray,
) -> np.ndarray:
    """
    Calculate complex impedance of a loudspeaker from Thiele-Small parameters.

    Args:
        ts_params: Dict with keys: re, fs, qms, qes, and optionally le, bl, mms, cms, rms.
                   re in Ohms, le in mH, fs in Hz, bl in T·m, mms in grams,
                   cms in mm/N, rms in kg/s.
        frequencies: Array of frequencies in Hz.

    Returns:
        Complex impedance array (Ohms). Use np.abs() for magnitude, np.angle() for phase.
    """
    Re = ts_params['re']
    Le = ts_params.get('le', 0.0)
    if Le is None:
        Le = 0.0
    Le_si = Le * 1e-3  # mH → H

    omega = 2 * np.pi * frequencies
    Res, Lces, Cmes = _motional_params_from_ts(ts_params)

    # Voice coil impedance: Re + jωLe
    Z_vc = Re + 1j * omega * Le_si

    # Motional impedance: parallel RLC
    # Y_mot = 1/Res + jωCmes + 1/(jωLces)
    Y_mot = (1.0 / Res) + 1j * omega * Cmes + 1.0 / (1j * omega * Lces)
    Z_mot = 1.0 / Y_mot

    return Z_vc + Z_mot


def impedance_magnitude(ts_params: Dict, frequencies: np.ndarray) -> np.ndarray:
    """Return impedance magnitude in Ohms."""
    return np.abs(calculate_impedance(ts_params, frequencies))


def impedance_phase(ts_params: Dict, frequencies: np.ndarray) -> np.ndarray:
    """Return impedance phase in degrees."""
    return np.degrees(np.angle(calculate_impedance(ts_params, frequencies)))


def verify_impedance_model(ts_params: Dict) -> Dict:
    """
    Run sanity checks on the impedance model for the given TS params.

    Checks:
    1. Peak impedance at fs ≈ Re * (1 + Qms/Qes)
    2. Qts = Qms*Qes / (Qms + Qes)
    3. DC impedance → Re
    4. High-frequency impedance rises with Le

    Returns dict of check results.
    """
    Re = ts_params['re']
    fs = ts_params['fs']
    Qms = ts_params['qms']
    Qes = ts_params['qes']

    Qts_expected = (Qms * Qes) / (Qms + Qes)
    Qts_given = ts_params.get('qts')
    qts_ok = Qts_given is None or abs(Qts_expected - Qts_given) / Qts_expected < 0.05

    # Calculate peak at fs
    Z_at_fs = calculate_impedance(ts_params, np.array([fs]))
    Z_peak = np.abs(Z_at_fs[0])
    Z_peak_expected = Re * (1 + Qms / Qes)
    peak_error = abs(Z_peak - Z_peak_expected) / Z_peak_expected

    # DC check (very low frequency ≈ Re)
    Z_dc = calculate_impedance(ts_params, np.array([0.1]))
    Z_dc_mag = np.abs(Z_dc[0])

    return {
        'qts_expected': round(Qts_expected, 4),
        'qts_given': Qts_given,
        'qts_consistent': qts_ok,
        'peak_impedance': round(Z_peak, 2),
        'peak_impedance_expected': round(Z_peak_expected, 2),
        'peak_error_pct': round(peak_error * 100, 2),
        'dc_impedance': round(Z_dc_mag, 2),
        're': Re,
    }


def parse_impedance_csv(csv_content: str) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """
    Parse a CSV of measured impedance data.

    Expects columns: frequency (Hz), magnitude (Ohms), [phase (degrees)]
    Header row is auto-detected. Supports comma and tab delimiters.

    Returns (frequencies, magnitudes, phases_or_None)
    """
    # Try to detect delimiter
    delimiter = ',' if ',' in csv_content else '\t'

    reader = csv.reader(io.StringIO(csv_content), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        raise ValueError("Empty CSV content")

    # Skip header if first row contains non-numeric data
    start = 0
    try:
        float(rows[0][0])
    except (ValueError, IndexError):
        start = 1

    freqs = []
    mags = []
    phases = []
    has_phase = len(rows[start]) >= 3

    for row in rows[start:]:
        if len(row) < 2:
            continue
        try:
            f = float(row[0])
            m = float(row[1])
            if f <= 0 or m <= 0:
                continue
            freqs.append(f)
            mags.append(m)
            if has_phase and len(row) >= 3:
                phases.append(float(row[2]))
        except (ValueError, IndexError):
            continue

    if len(freqs) < 2:
        raise ValueError("CSV must contain at least 2 valid data points")

    freq_arr = np.array(freqs)
    mag_arr = np.array(mags)
    phase_arr = np.array(phases) if phases and len(phases) == len(freqs) else None

    return freq_arr, mag_arr, phase_arr


def interpolate_impedance(
    freq: np.ndarray,
    mag: np.ndarray,
    phase: Optional[np.ndarray],
    target_freqs: np.ndarray,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Interpolate measured impedance data to a new set of frequencies.

    Uses log-frequency interpolation for smooth results on log-scale plots.

    Args:
        freq: Original frequency points (Hz)
        mag: Original magnitude points (Ohms)
        phase: Original phase points (degrees), or None
        target_freqs: Desired output frequencies (Hz)

    Returns:
        (interpolated_magnitudes, interpolated_phases_or_None)
    """
    log_freq = np.log10(freq)
    log_target = np.log10(target_freqs)

    # Interpolate magnitude in log-log space for smoother results
    log_mag = np.log10(mag)
    interp_log_mag = np.interp(log_target, log_freq, log_mag)
    interp_mag = 10 ** interp_log_mag

    interp_phase = None
    if phase is not None:
        # Phase interpolated in log-freq / linear-phase space
        interp_phase = np.interp(log_target, log_freq, phase)

    return interp_mag, interp_phase
