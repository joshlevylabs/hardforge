"""
Circuit topology definitions and design equations.

Each topology defines a circuit architecture with named component slots
and calculation functions that compute component values from specifications.

Filter coefficients from Zverev "Handbook of Filter Synthesis" and
Butterworth/Linkwitz-Riley/Bessel standard tables.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional


# Normalized filter coefficients [stage1, stage2, ...]
# For 2nd-order sections: each entry is (a_i, b_i) from s² + a_i·s + b_i
BUTTERWORTH_Q = {
    1: [],  # 1st order has no Q
    2: [0.7071],  # 1/√2
    3: [1.0],  # 3rd order = 1st-order section + 2nd-order section with Q=1.0
    4: [0.5412, 1.3065],
}

# Linkwitz-Riley is two cascaded Butterworth of half the order
# LR2 = two 1st-order Butterworth, LR4 = two 2nd-order Butterworth
LINKWITZ_RILEY_Q = {
    2: [0.5],           # Q=0.5 for each section (critically damped)
    4: [0.7071, 0.7071],  # Two Butterworth 2nd-order sections
}

BESSEL_Q = {
    2: [0.5773],
    3: [0.6910],  # 3rd order = 1st-order section + 2nd-order section with Q=0.691
    4: [0.5219, 0.8055],
}

ALIGNMENT_Q = {
    'butterworth': BUTTERWORTH_Q,
    'linkwitz-riley': LINKWITZ_RILEY_Q,
    'bessel': BESSEL_Q,
}


@dataclass
class ComponentSlot:
    """A named slot for a component in a topology."""
    ref: str           # e.g. 'R1', 'C1', 'L1'
    comp_type: str     # 'resistor', 'capacitor', 'inductor'
    description: str   # e.g. 'Zobel resistor'


@dataclass
class TopologyDefinition:
    """Complete definition of a circuit topology."""
    name: str
    description: str
    component_slots: List[ComponentSlot]
    use_cases: List[str]
    calculate: Callable  # Function(params) → Dict of component values
    category: str = 'general'


def _calc_zobel(params: Dict) -> Dict:
    """Zobel network: series RC across driver."""
    Re = params['re']
    Le = params['le'] * 1e-3  # mH → H
    Rz = Re
    Cz = Le / (Re ** 2)
    return {
        'R1': {'value': Rz, 'unit': 'Ω', 'type': 'resistor'},
        'C1': {'value': Cz, 'unit': 'F', 'type': 'capacitor'},
    }


def _calc_notch(params: Dict) -> Dict:
    """Resonance notch filter: series RLC across driver."""
    Re = params['re']
    fs = params['fs']
    Qms = params['qms']
    Qes = params['qes']

    R_notch = Re * Qms / Qes
    L_notch = Qes * Re / (2 * np.pi * fs)
    C_notch = 1.0 / (2 * np.pi * fs * Qes * Re)

    return {
        'R1': {'value': R_notch, 'unit': 'Ω', 'type': 'resistor'},
        'L1': {'value': L_notch, 'unit': 'H', 'type': 'inductor'},
        'C1': {'value': C_notch, 'unit': 'F', 'type': 'capacitor'},
    }


def _calc_lpad(params: Dict) -> Dict:
    """
    L-pad attenuator for level matching between drivers.

    R1 in series, R2 in parallel. Load impedance = Zload.
    Attenuation in dB.
    """
    Zload = params['impedance']  # Driver impedance (Ohms)
    atten_db = params['attenuation_db']

    # Voltage ratio
    ratio = 10 ** (atten_db / 20.0)

    R1 = Zload * (ratio - 1) / ratio
    R2 = Zload * ratio / (ratio - 1)

    return {
        'R1': {'value': R1, 'unit': 'Ω', 'type': 'resistor', 'description': 'Series resistor'},
        'R2': {'value': R2, 'unit': 'Ω', 'type': 'resistor', 'description': 'Shunt resistor'},
    }


def _calc_crossover(params: Dict) -> Dict:
    """
    Passive crossover filter calculator.

    Supports 1st through 4th order, Butterworth/Linkwitz-Riley/Bessel alignments.
    Uses normalized prototype coefficients scaled to target frequency and impedance.

    Standard formulas (1st order, impedance R):
        LP: L = R / (2πfc)           HP: C = 1 / (2πfcR)

    2nd order (single section, quality factor Q):
        LP: L = R / (2πfc·Q·2)... no, let's use the standard form.

    For a 2nd-order low-pass Butterworth (Q = 1/√2):
        L = R / (2πfc) · √2          (series inductor)
        C = 1 / (2πfc·R) · 1/√2      (shunt capacitor)... wait.

    Correct normalized 2nd-order LP prototype: L₁ = 2Q, C₁ = 1/(2Q)
    Denormalized: L = L₁·R/(2πfc), C = C₁/(2πfc·R)

    So for Butterworth (Q=0.7071):
        L = √2 · R/(2πfc)
        C = 1/(√2 · 2πfc · R)
    """
    fc = params['crossover_freq']       # Hz
    R = params['impedance']             # Ohms (nominal driver impedance)
    order = params.get('order', 2)
    alignment = params.get('alignment', 'butterworth')
    filter_type = params.get('filter_type', 'lowpass')  # 'lowpass', 'highpass', 'bandpass'

    components = {}
    wc = 2 * np.pi * fc

    if order == 1:
        if filter_type in ('lowpass', 'both'):
            components['L_LP'] = {'value': R / wc, 'unit': 'H', 'type': 'inductor',
                                  'description': '1st-order LP series inductor'}
        if filter_type in ('highpass', 'both'):
            components['C_HP'] = {'value': 1.0 / (wc * R), 'unit': 'F', 'type': 'capacitor',
                                  'description': '1st-order HP series capacitor'}

    elif order == 2:
        Q_values = ALIGNMENT_Q.get(alignment, BUTTERWORTH_Q)
        if order not in Q_values:
            raise ValueError(f"Order {order} not available for {alignment}")
        Q = Q_values[order][0]

        # Normalized prototype values for 2nd-order section:
        # LP prototype: series L, shunt C
        # L_norm = 2*Q,  C_norm = 1/(2*Q)...
        # Actually: for a standard 2nd-order LP with quality factor Q:
        #   H(s) = 1 / (s² + s/Q + 1)
        # Realized as series L, shunt C into load R:
        #   L_norm = 1/Q,  C_norm = Q
        # Denormalized: L = L_norm * R/ωc, C = C_norm / (ωc*R)
        #
        # Let's verify with Butterworth Q=0.7071:
        #   L = (1/0.7071) * R/ωc = √2 * R/ωc  ✓
        #   C = 0.7071 / (ωc*R) = 1/(√2·ωc·R)  ✓

        L_norm = 1.0 / Q
        C_norm = Q

        if filter_type in ('lowpass', 'both'):
            components['L_LP'] = {'value': L_norm * R / wc, 'unit': 'H', 'type': 'inductor',
                                  'description': f'{order}nd-order {alignment} LP inductor'}
            components['C_LP'] = {'value': C_norm / (wc * R), 'unit': 'F', 'type': 'capacitor',
                                  'description': f'{order}nd-order {alignment} LP capacitor'}
        if filter_type in ('highpass', 'both'):
            # HP is dual of LP: swap L↔C roles
            components['C_HP'] = {'value': 1.0 / (L_norm * R * wc), 'unit': 'F', 'type': 'capacitor',
                                  'description': f'{order}nd-order {alignment} HP capacitor'}
            components['L_HP'] = {'value': R / (C_norm * wc), 'unit': 'H', 'type': 'inductor',
                                  'description': f'{order}nd-order {alignment} HP inductor'}

    elif order == 3:
        Q_values = ALIGNMENT_Q.get(alignment, BUTTERWORTH_Q)
        if order not in Q_values:
            raise ValueError(f"Order {order} not available for {alignment}")

        # 3rd order = 1st order section + 2nd order section
        Q = Q_values[order][0]

        if filter_type in ('lowpass', 'both'):
            # 1st section: series inductor
            components['L1_LP'] = {'value': R / wc, 'unit': 'H', 'type': 'inductor',
                                   'description': '3rd-order LP 1st inductor'}
            # 2nd section: series L, shunt C
            L_norm = 1.0 / Q
            C_norm = Q
            components['L2_LP'] = {'value': L_norm * R / wc, 'unit': 'H', 'type': 'inductor',
                                   'description': '3rd-order LP 2nd inductor'}
            components['C1_LP'] = {'value': C_norm / (wc * R), 'unit': 'F', 'type': 'capacitor',
                                   'description': '3rd-order LP capacitor'}

        if filter_type in ('highpass', 'both'):
            components['C1_HP'] = {'value': 1.0 / (wc * R), 'unit': 'F', 'type': 'capacitor',
                                   'description': '3rd-order HP 1st capacitor'}
            L_norm = 1.0 / Q
            C_norm = Q
            components['C2_HP'] = {'value': 1.0 / (L_norm * R * wc), 'unit': 'F', 'type': 'capacitor',
                                   'description': '3rd-order HP 2nd capacitor'}
            components['L1_HP'] = {'value': R / (C_norm * wc), 'unit': 'H', 'type': 'inductor',
                                   'description': '3rd-order HP inductor'}

    elif order == 4:
        Q_values = ALIGNMENT_Q.get(alignment, BUTTERWORTH_Q)
        if order not in Q_values:
            raise ValueError(f"Order {order} not available for {alignment}")

        Qs = Q_values[order]

        if filter_type in ('lowpass', 'both'):
            for i, Q in enumerate(Qs):
                L_norm = 1.0 / Q
                C_norm = Q
                suffix = i + 1
                components[f'L{suffix}_LP'] = {
                    'value': L_norm * R / wc, 'unit': 'H', 'type': 'inductor',
                    'description': f'4th-order {alignment} LP inductor (section {suffix})',
                }
                components[f'C{suffix}_LP'] = {
                    'value': C_norm / (wc * R), 'unit': 'F', 'type': 'capacitor',
                    'description': f'4th-order {alignment} LP capacitor (section {suffix})',
                }

        if filter_type in ('highpass', 'both'):
            for i, Q in enumerate(Qs):
                L_norm = 1.0 / Q
                C_norm = Q
                suffix = i + 1
                components[f'C{suffix}_HP'] = {
                    'value': 1.0 / (L_norm * R * wc), 'unit': 'F', 'type': 'capacitor',
                    'description': f'4th-order {alignment} HP capacitor (section {suffix})',
                }
                components[f'L{suffix}_HP'] = {
                    'value': R / (C_norm * wc), 'unit': 'H', 'type': 'inductor',
                    'description': f'4th-order {alignment} HP inductor (section {suffix})',
                }

    else:
        raise ValueError(f"Order {order} not supported (use 1-4)")

    return components


def _calc_baffle_step(params: Dict) -> Dict:
    """
    Baffle step compensation network.

    Compensates the ~6dB rise in response when wavelength becomes smaller
    than baffle dimensions. Typically a series RL shunt.

    f_step ≈ 115 / baffle_width_m (rough estimate)
    """
    R_driver = params['impedance']
    f_step = params.get('baffle_step_freq', 400)  # Hz

    wc = 2 * np.pi * f_step

    # Series RL across driver: R in series with L
    # R controls the amount of compensation (typically R = R_driver)
    # L sets the frequency: L = R / (2πf_step)
    R1 = R_driver
    L1 = R_driver / wc

    return {
        'R1': {'value': R1, 'unit': 'Ω', 'type': 'resistor',
               'description': 'Baffle step compensation resistor'},
        'L1': {'value': L1, 'unit': 'H', 'type': 'inductor',
               'description': 'Baffle step compensation inductor'},
    }


def _calc_voltage_divider(params: Dict) -> Dict:
    """Simple resistive voltage divider."""
    Vin = params.get('vin', 1.0)
    Vout = params.get('vout', 0.5)
    R_total = params.get('r_total', 10000)  # Ohms

    ratio = Vout / Vin
    R2 = R_total * ratio
    R1 = R_total - R2

    return {
        'R1': {'value': R1, 'unit': 'Ω', 'type': 'resistor', 'description': 'Top resistor'},
        'R2': {'value': R2, 'unit': 'Ω', 'type': 'resistor', 'description': 'Bottom resistor'},
    }


def _calc_rc_filter(params: Dict) -> Dict:
    """1st-order RC low-pass or high-pass filter."""
    fc = params['cutoff_freq']
    R = params.get('resistance', 10000)
    filter_type = params.get('filter_type', 'lowpass')

    C = 1.0 / (2 * np.pi * fc * R)

    return {
        'R1': {'value': R, 'unit': 'Ω', 'type': 'resistor'},
        'C1': {'value': C, 'unit': 'F', 'type': 'capacitor'},
        'topology': 'RC low-pass' if filter_type == 'lowpass' else 'RC high-pass',
    }


def _calc_rl_filter(params: Dict) -> Dict:
    """1st-order RL low-pass or high-pass filter."""
    fc = params['cutoff_freq']
    R = params.get('resistance', 8)

    L = R / (2 * np.pi * fc)

    return {
        'R1': {'value': R, 'unit': 'Ω', 'type': 'resistor'},
        'L1': {'value': L, 'unit': 'H', 'type': 'inductor'},
    }


def _calc_rlc_filter(params: Dict) -> Dict:
    """2nd-order RLC filter."""
    fc = params['cutoff_freq']
    R = params.get('resistance', 8)
    Q = params.get('q_factor', 0.7071)

    wc = 2 * np.pi * fc
    L = R / (wc * Q * 2)  # Approximate for series RLC
    C = 1.0 / (wc ** 2 * L)

    return {
        'R1': {'value': R, 'unit': 'Ω', 'type': 'resistor'},
        'L1': {'value': L, 'unit': 'H', 'type': 'inductor'},
        'C1': {'value': C, 'unit': 'F', 'type': 'capacitor'},
    }


# Registry of all topologies
TOPOLOGIES: Dict[str, TopologyDefinition] = {
    'zobel': TopologyDefinition(
        name='zobel',
        description='Zobel network for voice coil inductance compensation (series RC across driver)',
        component_slots=[
            ComponentSlot('R1', 'resistor', 'Zobel resistor (≈ Re)'),
            ComponentSlot('C1', 'capacitor', 'Zobel capacitor (Le/Re²)'),
        ],
        use_cases=['Impedance linearization', 'Passive crossover pre-conditioning'],
        calculate=_calc_zobel,
        category='impedance_correction',
    ),
    'notch_filter': TopologyDefinition(
        name='notch_filter',
        description='Resonance notch filter (series RLC across driver to flatten fs peak)',
        component_slots=[
            ComponentSlot('R1', 'resistor', 'Notch damping resistor'),
            ComponentSlot('L1', 'inductor', 'Notch inductor'),
            ComponentSlot('C1', 'capacitor', 'Notch capacitor'),
        ],
        use_cases=['Impedance linearization at resonance', 'Crossover pre-conditioning'],
        calculate=_calc_notch,
        category='impedance_correction',
    ),
    'lpad': TopologyDefinition(
        name='lpad',
        description='L-pad attenuator for level matching between drivers',
        component_slots=[
            ComponentSlot('R1', 'resistor', 'Series resistor'),
            ComponentSlot('R2', 'resistor', 'Shunt resistor'),
        ],
        use_cases=['Tweeter level matching', 'Driver sensitivity alignment'],
        calculate=_calc_lpad,
        category='attenuator',
    ),
    'passive_crossover': TopologyDefinition(
        name='passive_crossover',
        description='Passive crossover filter (1st-4th order, Butterworth/LR/Bessel)',
        component_slots=[],  # Dynamic based on order
        use_cases=['2-way crossover', '3-way crossover', 'Subwoofer/satellite split'],
        calculate=_calc_crossover,
        category='crossover',
    ),
    'baffle_step_comp': TopologyDefinition(
        name='baffle_step_comp',
        description='Baffle step compensation (series RL shunt)',
        component_slots=[
            ComponentSlot('R1', 'resistor', 'Compensation resistor'),
            ComponentSlot('L1', 'inductor', 'Compensation inductor'),
        ],
        use_cases=['Baffle diffraction compensation', 'Low-frequency response shaping'],
        calculate=_calc_baffle_step,
        category='compensation',
    ),
    'voltage_divider': TopologyDefinition(
        name='voltage_divider',
        description='Resistive voltage divider',
        component_slots=[
            ComponentSlot('R1', 'resistor', 'Top resistor'),
            ComponentSlot('R2', 'resistor', 'Bottom resistor'),
        ],
        use_cases=['Signal attenuation', 'Bias network'],
        calculate=_calc_voltage_divider,
        category='general',
    ),
    'rc_filter': TopologyDefinition(
        name='rc_filter',
        description='1st-order RC filter (low-pass or high-pass)',
        component_slots=[
            ComponentSlot('R1', 'resistor', 'Filter resistor'),
            ComponentSlot('C1', 'capacitor', 'Filter capacitor'),
        ],
        use_cases=['Signal filtering', 'DC blocking'],
        calculate=_calc_rc_filter,
        category='filter',
    ),
    'rl_filter': TopologyDefinition(
        name='rl_filter',
        description='1st-order RL filter',
        component_slots=[
            ComponentSlot('R1', 'resistor', 'Filter resistor'),
            ComponentSlot('L1', 'inductor', 'Filter inductor'),
        ],
        use_cases=['Power filtering', 'Speaker crossover element'],
        calculate=_calc_rl_filter,
        category='filter',
    ),
    'rlc_filter': TopologyDefinition(
        name='rlc_filter',
        description='2nd-order RLC filter',
        component_slots=[
            ComponentSlot('R1', 'resistor', 'Damping resistor'),
            ComponentSlot('L1', 'inductor', 'Filter inductor'),
            ComponentSlot('C1', 'capacitor', 'Filter capacitor'),
        ],
        use_cases=['Band-pass filtering', 'Resonant circuit'],
        calculate=_calc_rlc_filter,
        category='filter',
    ),
}


def get_topology(name: str) -> TopologyDefinition:
    """Get a topology definition by name."""
    if name not in TOPOLOGIES:
        raise ValueError(f"Unknown topology '{name}'. Available: {list(TOPOLOGIES.keys())}")
    return TOPOLOGIES[name]


def list_topologies(category: Optional[str] = None) -> List[Dict]:
    """List all available topologies, optionally filtered by category."""
    result = []
    for name, topo in TOPOLOGIES.items():
        if category and topo.category != category:
            continue
        result.append({
            'name': topo.name,
            'description': topo.description,
            'category': topo.category,
            'use_cases': topo.use_cases,
            'component_slots': [
                {'ref': s.ref, 'type': s.comp_type, 'description': s.description}
                for s in topo.component_slots
            ],
        })
    return result


def calculate_topology(name: str, params: Dict) -> Dict:
    """Calculate component values for a given topology and parameters."""
    topo = get_topology(name)
    return topo.calculate(params)
