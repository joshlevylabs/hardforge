"""
Analytical circuit simulation for passive networks.

No external SPICE required — uses impedance divider analysis
and transfer function calculation for passive LC/RC/RL networks.

For passive filters driving a resistive load, the transfer function
is simply H(f) = Z_load / (Z_series + Z_load) for series elements,
or H(f) = Z_shunt || Z_load / (Z_series + Z_shunt || Z_load).
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


def ac_analysis(
    circuit_design: Dict,
    freq_start: float = 20.0,
    freq_end: float = 20000.0,
    num_points: int = 200,
) -> Dict:
    """
    Perform AC frequency response analysis on a passive circuit.

    Uses analytical solutions based on impedance divider chains.
    Works for series/parallel combinations of R, L, C driving a resistive load.

    Args:
        circuit_design: CircuitDesign JSON with components and topology
        freq_start: Start frequency in Hz
        freq_end: End frequency in Hz
        num_points: Number of frequency points (logarithmically spaced)

    Returns:
        Dict with frequencies, magnitude_db, phase_deg arrays.
    """
    frequencies = np.logspace(np.log10(freq_start), np.log10(freq_end), num_points)
    omega = 2 * np.pi * frequencies

    components = circuit_design.get('components', [])
    topology = circuit_design.get('topology', '')

    # Determine load impedance (look for a driver or assume 8Ω)
    R_load = 8.0
    for comp in components:
        if comp['type'] == 'driver':
            R_load = comp.get('impedance', comp.get('value', 8.0))
            break
        if comp.get('ref', '').startswith('R') and comp.get('description', '').lower().find('load') >= 0:
            R_load = comp['value']
            break

    # Calculate transfer function based on topology
    if topology in ('passive_crossover', 'lowpass', 'highpass', 'bandpass'):
        H = _calc_filter_response(components, omega, R_load)
    elif topology in ('zobel', 'notch_filter', 'impedance_correction'):
        H = _calc_correction_response(components, omega, R_load)
    elif topology == 'lpad':
        H = _calc_lpad_response(components, omega, R_load)
    else:
        # Generic: treat as series impedance chain into load
        H = _calc_generic_series_response(components, omega, R_load)

    magnitude_db = 20 * np.log10(np.maximum(np.abs(H), 1e-10))
    phase_deg = np.degrees(np.angle(H))

    return {
        'frequencies': frequencies.tolist(),
        'magnitude_db': magnitude_db.tolist(),
        'phase_deg': phase_deg.tolist(),
        'num_points': num_points,
    }


def impedance_analysis(
    circuit_design: Dict,
    frequencies: np.ndarray,
) -> np.ndarray:
    """
    Calculate the combined impedance of a circuit as seen from its terminals.

    Args:
        circuit_design: CircuitDesign JSON
        frequencies: Frequency array in Hz

    Returns:
        Complex impedance array.
    """
    omega = 2 * np.pi * frequencies
    components = circuit_design.get('components', [])

    Z_total = np.zeros_like(frequencies, dtype=complex)

    for comp in components:
        Z_comp = _component_impedance(comp, omega)
        # Default: series combination
        Z_total += Z_comp

    return Z_total


def _component_impedance(comp: Dict, omega: np.ndarray) -> np.ndarray:
    """Calculate the impedance of a single component at given frequencies."""
    value = comp['value']
    comp_type = comp['type']
    unit = comp.get('unit', '')

    if comp_type == 'resistor':
        return np.full_like(omega, value, dtype=complex)
    elif comp_type == 'capacitor':
        # Ensure value is in Farads
        C = value
        if unit == 'µF' or unit == 'uF':
            C = value * 1e-6
        elif unit == 'nF':
            C = value * 1e-9
        elif unit == 'pF':
            C = value * 1e-12
        return 1.0 / (1j * omega * C)
    elif comp_type == 'inductor':
        L = value
        if unit == 'mH':
            L = value * 1e-3
        elif unit == 'µH' or unit == 'uH':
            L = value * 1e-6
        return 1j * omega * L
    elif comp_type == 'driver':
        # Simple model: just a resistor at nominal impedance
        return np.full_like(omega, comp.get('impedance', value), dtype=complex)
    else:
        return np.zeros_like(omega, dtype=complex)


def _calc_filter_response(
    components: List[Dict],
    omega: np.ndarray,
    R_load: float,
) -> np.ndarray:
    """
    Calculate transfer function for a passive filter.

    For a low-pass: series L, shunt C into load R.
    H(f) = Z_load / (Z_series_total + Z_load)
    where Z_load includes any shunt elements in parallel.
    """
    Z_series = np.zeros_like(omega, dtype=complex)
    Z_shunt_inv = np.zeros_like(omega, dtype=complex)  # Admittance of shunt elements

    for comp in components:
        if comp['type'] == 'driver':
            continue

        Z_comp = _component_impedance(comp, omega)

        # Heuristic: inductors are typically series, capacitors are typically shunt
        # in loudspeaker crossovers (low-pass: series L, shunt C)
        desc = comp.get('description', '').lower()
        ref = comp.get('ref', '')

        if 'shunt' in desc or 'parallel' in desc:
            Z_shunt_inv += 1.0 / Z_comp
        elif 'series' in desc:
            Z_series += Z_comp
        elif comp['type'] == 'inductor' and 'LP' in ref:
            Z_series += Z_comp
        elif comp['type'] == 'capacitor' and 'LP' in ref:
            Z_shunt_inv += 1.0 / Z_comp
        elif comp['type'] == 'capacitor' and 'HP' in ref:
            Z_series += Z_comp
        elif comp['type'] == 'inductor' and 'HP' in ref:
            Z_shunt_inv += 1.0 / Z_comp
        elif comp['type'] == 'inductor':
            Z_series += Z_comp
        elif comp['type'] == 'capacitor':
            Z_shunt_inv += 1.0 / Z_comp
        else:
            Z_series += Z_comp

    # Load impedance
    Z_load = np.full_like(omega, R_load, dtype=complex)

    # Combined load: shunt elements in parallel with load
    if np.any(Z_shunt_inv != 0):
        Z_load_combined = 1.0 / (1.0 / Z_load + Z_shunt_inv)
    else:
        Z_load_combined = Z_load

    # Transfer function: voltage divider
    H = Z_load_combined / (Z_series + Z_load_combined)

    return H


def _calc_correction_response(
    components: List[Dict],
    omega: np.ndarray,
    R_load: float,
) -> np.ndarray:
    """
    Calculate response of impedance correction network.

    Correction networks are in parallel with the load,
    so they reduce the total impedance seen by the source.
    The "response" here is the impedance ratio: Z_corrected / Z_uncorrected.
    """
    Z_load = np.full_like(omega, R_load, dtype=complex)
    Y_correction = np.zeros_like(omega, dtype=complex)

    for comp in components:
        if comp['type'] == 'driver':
            continue
        Z_comp = _component_impedance(comp, omega)
        Y_correction += 1.0 / Z_comp

    Z_corrected = 1.0 / (1.0 / Z_load + Y_correction)
    H = Z_corrected / Z_load

    return H


def _calc_lpad_response(
    components: List[Dict],
    omega: np.ndarray,
    R_load: float,
) -> np.ndarray:
    """Calculate L-pad attenuation (frequency independent for pure resistors)."""
    R_series = 0.0
    R_shunt = float('inf')

    for comp in components:
        if comp['type'] == 'resistor':
            desc = comp.get('description', '').lower()
            if 'series' in desc or comp.get('ref') == 'R1':
                R_series = comp['value']
            elif 'shunt' in desc or comp.get('ref') == 'R2':
                R_shunt = comp['value']

    Z_parallel = (R_shunt * R_load) / (R_shunt + R_load)
    H_mag = Z_parallel / (R_series + Z_parallel)

    return np.full_like(omega, H_mag, dtype=complex)


def _calc_generic_series_response(
    components: List[Dict],
    omega: np.ndarray,
    R_load: float,
) -> np.ndarray:
    """Generic series impedance divider."""
    Z_series = np.zeros_like(omega, dtype=complex)

    for comp in components:
        if comp['type'] == 'driver':
            continue
        Z_series += _component_impedance(comp, omega)

    Z_load = np.full_like(omega, R_load, dtype=complex)
    H = Z_load / (Z_series + Z_load)

    return H
