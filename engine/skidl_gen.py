"""
SKiDL circuit generation.

Generates SKiDL Python source code and KiCad netlists from CircuitDesign JSON.
SKiDL is not required at runtime — we generate the Python code as a string
that users can run independently with SKiDL installed.
"""

from typing import Dict, List


# KiCad footprint assignments based on component type and value
RESISTOR_FOOTPRINTS = {
    'smd_0402': 'Resistor_SMD:R_0402_1005Metric',
    'smd_0603': 'Resistor_SMD:R_0603_1608Metric',
    'smd_0805': 'Resistor_SMD:R_0805_2012Metric',
    'smd_1206': 'Resistor_SMD:R_1206_3216Metric',
    'smd_2512': 'Resistor_SMD:R_2512_6332Metric',
    'through_hole': 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    'through_hole_power': 'Resistor_THT:R_Axial_DIN0617_L17.0mm_D6.0mm_P20.32mm_Horizontal',
}

CAPACITOR_FOOTPRINTS = {
    'smd_0402': 'Capacitor_SMD:C_0402_1005Metric',
    'smd_0603': 'Capacitor_SMD:C_0603_1608Metric',
    'smd_0805': 'Capacitor_SMD:C_0805_2012Metric',
    'smd_1206': 'Capacitor_SMD:C_1206_3216Metric',
    'film': 'Capacitor_THT:C_Rect_L18.0mm_W6.0mm_P15.00mm_FKS3_FKP3',
    'electrolytic': 'Capacitor_THT:CP_Radial_D10.0mm_P5.00mm',
    'electrolytic_large': 'Capacitor_THT:CP_Radial_D16.0mm_P7.50mm',
}

INDUCTOR_FOOTPRINTS = {
    'smd_small': 'Inductor_SMD:L_0805_2012Metric',
    'smd_medium': 'Inductor_SMD:L_1210_3225Metric',
    'air_core': 'Inductor_THT:L_Axial_L12.0mm_D5.0mm_P15.24mm_Horizontal',
    'air_core_large': 'Inductor_THT:L_Toroid_Horizontal_D14.0mm_P5.08mm',
}


def _select_footprint(comp: Dict) -> str:
    """Select appropriate footprint based on component type, value, and power rating."""
    comp_type = comp['type']
    value = comp.get('value', 0)
    power = comp.get('power_rating', 0.25)
    form_factor = comp.get('form_factor', 'through_hole')

    if comp_type == 'resistor':
        if form_factor == 'smd':
            if power <= 0.1:
                return RESISTOR_FOOTPRINTS['smd_0603']
            elif power <= 0.25:
                return RESISTOR_FOOTPRINTS['smd_0805']
            elif power <= 0.5:
                return RESISTOR_FOOTPRINTS['smd_1206']
            else:
                return RESISTOR_FOOTPRINTS['smd_2512']
        else:
            if power > 5:
                return RESISTOR_FOOTPRINTS['through_hole_power']
            return RESISTOR_FOOTPRINTS['through_hole']

    elif comp_type == 'capacitor':
        if form_factor == 'smd':
            if value < 1e-6:
                return CAPACITOR_FOOTPRINTS['smd_0805']
            return CAPACITOR_FOOTPRINTS['smd_1206']
        else:
            if value >= 100e-6:
                return CAPACITOR_FOOTPRINTS['electrolytic_large']
            elif value >= 1e-6:
                return CAPACITOR_FOOTPRINTS['electrolytic']
            return CAPACITOR_FOOTPRINTS['film']

    elif comp_type == 'inductor':
        if form_factor == 'smd':
            return INDUCTOR_FOOTPRINTS['smd_medium']
        else:
            if value >= 1e-3:
                return INDUCTOR_FOOTPRINTS['air_core_large']
            return INDUCTOR_FOOTPRINTS['air_core']

    return ''


def _format_value_for_skidl(comp: Dict) -> str:
    """Format a component value for SKiDL code."""
    value = comp['value']
    unit = comp.get('unit', '')

    if comp['type'] == 'resistor':
        if value >= 1e6:
            return f"'{value/1e6:.3g}M'"
        elif value >= 1e3:
            return f"'{value/1e3:.3g}k'"
        else:
            return f"'{value:.3g}'"

    elif comp['type'] == 'capacitor':
        if unit == 'F':
            if value >= 1e-3:
                return f"'{value*1e3:.3g}mF'"
            elif value >= 1e-6:
                return f"'{value*1e6:.3g}uF'"
            elif value >= 1e-9:
                return f"'{value*1e9:.3g}nF'"
            else:
                return f"'{value*1e12:.3g}pF'"
        return f"'{value:.3g}{unit}'"

    elif comp['type'] == 'inductor':
        if unit == 'H':
            if value >= 1:
                return f"'{value:.3g}H'"
            elif value >= 1e-3:
                return f"'{value*1e3:.3g}mH'"
            else:
                return f"'{value*1e6:.3g}uH'"
        return f"'{value:.3g}{unit}'"

    return f"'{value}'"


def generate_skidl_code(circuit_design: Dict) -> str:
    """
    Generate executable SKiDL Python code from a CircuitDesign JSON structure.

    The generated code can be run with SKiDL installed to produce a KiCad netlist.
    """
    lines = [
        '"""',
        f'HardForge Generated Circuit: {circuit_design.get("topology", "custom")}',
        'Run this with SKiDL installed: pip install skidl',
        '"""',
        '',
        'from skidl import *',
        '',
        '# Set default tool to KiCad',
        'set_default_tool(KICAD8)',
        '',
        '# Component definitions',
    ]

    components = circuit_design.get('components', [])
    connections = circuit_design.get('connections', [])

    # Generate component declarations
    for comp in components:
        ref = comp['ref']
        footprint = comp.get('footprint', _select_footprint(comp))
        value_str = _format_value_for_skidl(comp)

        if comp['type'] == 'resistor':
            lib_part = 'Device:R'
        elif comp['type'] == 'capacitor':
            lib_part = 'Device:C'
        elif comp['type'] == 'inductor':
            lib_part = 'Device:L'
        elif comp['type'] == 'driver':
            # Loudspeaker symbol
            lib_part = 'Device:Speaker'
        else:
            lib_part = f'Device:{comp["type"].upper()}'

        lines.append(
            f'{ref} = Part("{lib_part}", value={value_str}, '
            f'footprint="{footprint}", ref="{ref}")'
        )

    lines.append('')
    lines.append('# Net definitions and connections')

    # Collect unique nets
    nets = set()
    for conn in connections:
        nets.add(conn['net'])

    for net_name in sorted(nets):
        lines.append(f'net_{net_name} = Net("{net_name}")')

    lines.append('')

    # Generate connections
    for conn in connections:
        from_ref, from_pin = _parse_pin(conn['from'])
        to_ref, to_pin = _parse_pin(conn['to'])
        net_name = conn['net']

        lines.append(f'net_{net_name} += {from_ref}[{from_pin}], {to_ref}[{to_pin}]')

    lines.append('')
    lines.append('# Generate netlist')
    lines.append('generate_netlist()')
    lines.append('')

    return '\n'.join(lines)


def _parse_pin(pin_str: str):
    """Parse a pin reference like 'R1.1' into ('R1', '1')."""
    if '.' in pin_str:
        ref, pin = pin_str.rsplit('.', 1)
        return ref, pin
    # Default: assume it's just a ref, pin 1
    return pin_str, '1'


def generate_netlist(circuit_design: Dict) -> str:
    """
    Generate a KiCad-format netlist string directly (without SKiDL).

    This produces a minimal .net file that KiCad can import.
    """
    components = circuit_design.get('components', [])
    connections = circuit_design.get('connections', [])
    topology = circuit_design.get('topology', 'HardForge Circuit')

    lines = [
        '(export (version "E")',
        '  (design',
        f'    (source "HardForge: {topology}")',
        '    (date "")',
        '    (tool "HardForge Engine")',
        '  )',
        '  (components',
    ]

    for comp in components:
        ref = comp['ref']
        value = comp.get('value', '')
        footprint = comp.get('footprint', _select_footprint(comp))

        if comp['type'] == 'resistor':
            lib = 'Device:R'
        elif comp['type'] == 'capacitor':
            lib = 'Device:C'
        elif comp['type'] == 'inductor':
            lib = 'Device:L'
        else:
            lib = f'Device:{comp["type"]}'

        lines.append(f'    (comp (ref "{ref}")')
        lines.append(f'      (value "{value}")')
        lines.append(f'      (footprint "{footprint}")')
        lines.append(f'      (libsource (lib "Device") (part "{lib.split(":")[1]}"))')
        lines.append(f'    )')

    lines.append('  )')

    # Nets
    lines.append('  (nets')

    net_map = {}
    for conn in connections:
        net_name = conn['net']
        if net_name not in net_map:
            net_map[net_name] = []
        net_map[net_name].append(conn['from'])
        net_map[net_name].append(conn['to'])

    for i, (net_name, pins) in enumerate(net_map.items(), 1):
        lines.append(f'    (net (code "{i}") (name "{net_name}")')
        for pin_str in sorted(set(pins)):
            ref, pin = _parse_pin(pin_str)
            lines.append(f'      (node (ref "{ref}") (pin "{pin}"))')
        lines.append('    )')

    lines.append('  )')
    lines.append(')')
    lines.append('')

    return '\n'.join(lines)
