"""
Impedance correction network design.

Implements Zobel networks (voice coil inductance compensation) and
resonance notch filters for loudspeaker impedance linearization.

References:
- Dickason, "Loudspeaker Design Cookbook" (7th ed.)
- Small, "Direct-Radiator Loudspeaker System Analysis" (JAES, 1972)
"""

import numpy as np
from typing import Dict, Tuple, Optional
from engine.impedance import calculate_impedance, _motional_params_from_ts


def zobel_network(Re: float, Le: float, margin: float = 1.0) -> Dict:
    """
    Calculate Zobel (impedance compensation) network for voice coil inductance.

    A Zobel network is a series RC connected in parallel with the driver.
    It compensates the rising impedance caused by voice coil inductance Le.

    At high frequencies, the driver impedance rises as Z ≈ j·2πf·Le.
    The Zobel network provides a shunt path that cancels this rise.

    Args:
        Re: DC resistance of the driver (Ohms)
        Le: Voice coil inductance (mH)
        margin: Multiplier for Rz (1.0 = exact, 1.25 = conservative margin)

    Returns:
        Dict with Rz (Ohms), Cz (Farads), and power rating recommendation.
    """
    if Le <= 0:
        raise ValueError("Le must be positive for Zobel compensation")

    Le_si = Le * 1e-3  # mH → H

    Rz = Re * margin
    Cz = Le_si / (Re ** 2)

    # Power rating: Zobel resistor should handle at least the program power
    # divided by the impedance ratio. Conservative estimate: same as Re power.
    return {
        'Rz': round(Rz, 3),
        'Cz': Cz,  # Keep full precision for Farads (small values)
        'Rz_unit': 'Ω',
        'Cz_unit': 'F',
        'description': f'Zobel network: {Rz:.1f}Ω in series with {Cz*1e6:.2f}µF, connected across driver terminals',
    }


def notch_filter(fs: float, Qms: float, Qes: float, Re: float) -> Dict:
    """
    Calculate a parallel RLC notch filter to flatten the resonance peak.

    The notch filter is connected in parallel with the driver and has the
    same resonant frequency as the driver. It absorbs the resonance peak
    energy, flattening the impedance curve around fs.

    The notch filter components mirror the driver's motional impedance:
        R_notch = Res = Re · Qms/Qes
        L_notch = Lces = Qes · Re / (2πfs)
        C_notch = Cmes = 1 / (2πfs · Qes · Re)

    Args:
        fs: Driver resonance frequency (Hz)
        Qms: Mechanical Q factor
        Qes: Electrical Q factor
        Re: DC resistance (Ohms)

    Returns:
        Dict with R_notch (Ω), L_notch (H), C_notch (F).
    """
    R_notch = Re * Qms / Qes
    L_notch = Qes * Re / (2 * np.pi * fs)
    C_notch = 1.0 / (2 * np.pi * fs * Qes * Re)

    # Verify: resonant frequency of the notch should equal fs
    f_check = 1.0 / (2 * np.pi * np.sqrt(L_notch * C_notch))

    return {
        'R_notch': round(R_notch, 3),
        'L_notch': L_notch,
        'C_notch': C_notch,
        'R_notch_unit': 'Ω',
        'L_notch_unit': 'H',
        'C_notch_unit': 'F',
        'resonant_freq_check': round(f_check, 2),
        'description': (
            f'Parallel RLC notch: {R_notch:.1f}Ω, {L_notch*1e3:.2f}mH, '
            f'{C_notch*1e6:.2f}µF in series, connected across driver terminals'
        ),
    }


def full_correction(
    ts_params: Dict,
    target_impedance: Optional[float] = None,
) -> Dict:
    """
    Design a complete impedance correction network.

    Combines:
    1. Zobel network for high-frequency inductance compensation
    2. Notch filter for resonance peak suppression

    The result is a network that flattens the driver impedance to
    approximately Re (or target_impedance if specified).

    Args:
        ts_params: Thiele-Small parameters dict (re, le, fs, qms, qes, ...)
        target_impedance: Desired flat impedance (Ohms). Defaults to Re.

    Returns:
        Dict with zobel and notch components, plus power ratings.
    """
    Re = ts_params['re']
    Le = ts_params.get('le', 0.0) or 0.0
    fs = ts_params['fs']
    Qms = ts_params['qms']
    Qes = ts_params['qes']

    if target_impedance is None:
        target_impedance = Re

    result = {
        'target_impedance': target_impedance,
        'components': [],
    }

    # Zobel network (only if Le > 0)
    if Le > 0:
        zobel = zobel_network(Re, Le, margin=1.0)
        zobel['type'] = 'zobel'
        zobel['power_rating'] = _estimate_zobel_power(Re, ts_params.get('power_rating', 50))
        result['components'].append(zobel)
        result['zobel'] = zobel

    # Notch filter
    notch = notch_filter(fs, Qms, Qes, Re)
    notch['type'] = 'notch'
    notch['power_rating'] = _estimate_notch_power(Re, Qms, Qes, ts_params.get('power_rating', 50))
    result['components'].append(notch)
    result['notch'] = notch

    return result


def _estimate_zobel_power(Re: float, driver_power: float) -> Dict:
    """Estimate power dissipation in Zobel components."""
    # At the frequency where Le = Re (the crossover point),
    # the Zobel resistor dissipates roughly half the power that Re does.
    # Conservative: rate at 25% of driver power rating.
    power = driver_power * 0.25
    return {
        'resistor_watts': round(power, 1),
        'capacitor_voltage': round(np.sqrt(power * Re) * 2, 1),  # V = sqrt(P*R), with margin
        'note': 'Use non-inductive resistor (metal film or wirewound non-inductive)',
    }


def _estimate_notch_power(Re: float, Qms: float, Qes: float, driver_power: float) -> Dict:
    """Estimate power dissipation in notch filter components."""
    # The notch resistor dissipates power near resonance.
    # Maximum power in R_notch ≈ driver_power * Re / R_notch
    R_notch = Re * Qms / Qes
    power_r = driver_power * Re / R_notch
    return {
        'resistor_watts': round(max(power_r, 5), 1),
        'inductor_current': round(np.sqrt(driver_power / Re), 2),
        'capacitor_voltage': round(np.sqrt(driver_power * R_notch), 1),
        'note': 'Use air-core inductor for L_notch to avoid saturation',
    }


def calculate_corrected_impedance(
    ts_params: Dict,
    correction: Dict,
    frequencies: np.ndarray,
) -> np.ndarray:
    """
    Calculate the impedance of driver + correction network.

    The correction networks are in parallel with the driver, so:
        Z_total = 1 / (1/Z_driver + 1/Z_zobel + 1/Z_notch)

    Args:
        ts_params: Thiele-Small parameters
        correction: Output from full_correction()
        frequencies: Frequency array (Hz)

    Returns:
        Complex impedance array of the corrected system.
    """
    omega = 2 * np.pi * frequencies
    Z_driver = calculate_impedance(ts_params, frequencies)

    # Start with driver admittance
    Y_total = 1.0 / Z_driver

    # Add Zobel network admittance (series RC)
    if 'zobel' in correction:
        z = correction['zobel']
        Rz = z['Rz']
        Cz = z['Cz']
        # Zobel is Rz in series with Cz: Z_zobel = Rz + 1/(jωCz)
        Z_zobel = Rz + 1.0 / (1j * omega * Cz)
        Y_total += 1.0 / Z_zobel

    # Add notch filter admittance (series RLC)
    if 'notch' in correction:
        n = correction['notch']
        R_n = n['R_notch']
        L_n = n['L_notch']
        C_n = n['C_notch']
        # Notch is series RLC: Z_notch = R + jωL + 1/(jωC)
        Z_notch = R_n + 1j * omega * L_n + 1.0 / (1j * omega * C_n)
        Y_total += 1.0 / Z_notch

    return 1.0 / Y_total
