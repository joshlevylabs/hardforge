"""
E-series standard component values and engineering notation.

Provides lookup and snapping for resistors, capacitors, and inductors
to their nearest standard values in E12, E24, E48, and E96 series.
"""

import math
from typing import Tuple

# E-series base values (multiplied by decades to get full range)
# These are the standard IEC 60063 values per decade (1.0 to <10.0)

E12_BASE = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]

E24_BASE = [
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1,
]

E48_BASE = [
    1.00, 1.05, 1.10, 1.15, 1.21, 1.27, 1.33, 1.40, 1.47, 1.54, 1.62, 1.69,
    1.78, 1.87, 1.96, 2.05, 2.15, 2.26, 2.37, 2.49, 2.61, 2.74, 2.87, 3.01,
    3.16, 3.32, 3.48, 3.65, 3.83, 4.02, 4.22, 4.42, 4.64, 4.87, 5.11, 5.36,
    5.62, 5.90, 6.19, 6.49, 6.81, 7.15, 7.50, 7.87, 8.25, 8.66, 9.09, 9.53,
]

E96_BASE = [
    1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30,
    1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62, 1.65, 1.69, 1.74,
    1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15, 2.21, 2.26, 2.32,
    2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09,
    3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
    4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49,
    5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32,
    7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76,
]

E_SERIES = {
    'E12': E12_BASE,
    'E24': E24_BASE,
    'E48': E48_BASE,
    'E96': E96_BASE,
}

# Standard capacitor values (Farads) commonly available
# Covers pF through mF range
STANDARD_CAPACITOR_VALUES_PF = [
    # pF range
    1, 1.5, 2.2, 3.3, 4.7, 6.8, 10, 15, 22, 33, 47, 68, 100,
    150, 220, 330, 470, 680, 1000,
    # nF range (as pF)
    1500, 2200, 3300, 4700, 6800, 10000, 15000, 22000, 33000, 47000, 68000, 100000,
    # µF range (as pF)
    220000, 330000, 470000, 680000, 1e6, 2.2e6, 3.3e6, 4.7e6, 6.8e6, 10e6,
    22e6, 33e6, 47e6, 68e6, 100e6, 220e6, 330e6, 470e6, 1e9,
]

# Standard inductor values (Henries)
STANDARD_INDUCTOR_VALUES_UH = [
    # µH range
    0.1, 0.15, 0.22, 0.33, 0.47, 0.68, 1.0, 1.5, 2.2, 3.3, 4.7, 6.8,
    10, 15, 22, 33, 47, 68, 100, 150, 220, 330, 470, 680, 1000,
    # mH range (as µH)
    1500, 2200, 3300, 4700, 6800, 10000, 15000, 22000, 33000, 47000,
]

# SI prefix table
_SI_PREFIXES = [
    (1e-15, 'f'),
    (1e-12, 'p'),
    (1e-9,  'n'),
    (1e-6,  'µ'),
    (1e-3,  'm'),
    (1e0,   ''),
    (1e3,   'k'),
    (1e6,   'M'),
    (1e9,   'G'),
]


def snap_to_e_series(value: float, series: str = 'E24') -> Tuple[float, float]:
    """
    Snap a value to the nearest standard E-series value.

    Args:
        value: The target value (any unit — resistors in Ohms, capacitors in F, etc.)
        series: Which E-series to use ('E12', 'E24', 'E48', 'E96')

    Returns:
        Tuple of (snapped_value, error_percentage)
        error_percentage is signed: positive means snapped value is higher.
    """
    if value <= 0:
        raise ValueError(f"Value must be positive, got {value}")

    if series not in E_SERIES:
        raise ValueError(f"Unknown series '{series}'. Must be one of: {list(E_SERIES.keys())}")

    base_values = E_SERIES[series]

    # Find the decade: value = mantissa * 10^decade where 1 <= mantissa < 10
    decade = math.floor(math.log10(value))
    mantissa = value / (10 ** decade)

    # Find closest base value
    best_base = base_values[0]
    best_distance = abs(math.log10(mantissa) - math.log10(base_values[0]))

    for bv in base_values:
        dist = abs(math.log10(mantissa) - math.log10(bv))
        if dist < best_distance:
            best_distance = dist
            best_base = bv

    # Also check the top of the previous decade (values near 1.0)
    # and the bottom of the next decade
    prev_decade_top = base_values[-1] * 0.1  # e.g. 9.1 * 0.1 = 0.91
    dist = abs(math.log10(mantissa) - math.log10(prev_decade_top))
    if dist < best_distance:
        best_distance = dist
        best_base = prev_decade_top
        # Adjust decade since we went to a lower decade value
        snapped = prev_decade_top * (10 ** decade)
        error_pct = ((snapped - value) / value) * 100
        return snapped, round(error_pct, 4)

    next_decade_bottom = base_values[0] * 10  # = 10.0
    dist = abs(math.log10(mantissa) - math.log10(next_decade_bottom))
    if dist < best_distance:
        snapped = next_decade_bottom * (10 ** decade)
        error_pct = ((snapped - value) / value) * 100
        return snapped, round(error_pct, 4)

    snapped = best_base * (10 ** decade)
    error_pct = ((snapped - value) / value) * 100
    return snapped, round(error_pct, 4)


def engineering_notation(value: float, unit: str = '', precision: int = 3) -> str:
    """
    Format a value in engineering notation with SI prefix.

    Examples:
        engineering_notation(1000, 'Ω')     → '1kΩ'
        engineering_notation(0.0001, 'F')    → '100µF'
        engineering_notation(0.047, 'H')     → '47mH'
        engineering_notation(4700, 'Ω')      → '4.7kΩ'
        engineering_notation(0.0000001, 'F') → '100nF'
    """
    if value == 0:
        return f"0{unit}"

    abs_value = abs(value)
    sign = '-' if value < 0 else ''

    for scale, prefix in reversed(_SI_PREFIXES):
        if abs_value >= scale:
            scaled = abs_value / scale
            # Format with appropriate precision, strip trailing zeros
            if scaled == int(scaled):
                formatted = f"{sign}{int(scaled)}{prefix}{unit}"
            else:
                formatted = f"{sign}{scaled:.{precision}g}{prefix}{unit}"
            return formatted

    # Fallback for extremely small values
    return f"{value:.{precision}g}{unit}"


def snap_capacitor(value_f: float, series: str = 'E24') -> Tuple[float, float]:
    """Snap a capacitor value (in Farads) to nearest E-series standard value."""
    return snap_to_e_series(value_f, series)


def snap_inductor(value_h: float, series: str = 'E24') -> Tuple[float, float]:
    """Snap an inductor value (in Henries) to nearest E-series standard value."""
    return snap_to_e_series(value_h, series)


def snap_resistor(value_ohm: float, series: str = 'E24') -> Tuple[float, float]:
    """Snap a resistor value (in Ohms) to nearest E-series standard value."""
    return snap_to_e_series(value_ohm, series)
