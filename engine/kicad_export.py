"""
KiCad schematic and SVG export.

Generates:
- SVG schematics with proper EDA symbols (resistor zigzag, capacitor plates, inductor coils)
- KiCad .kicad_sch files
- Complete KiCad project bundles (for ZIP download)
"""

import json
import math
from html import escape as html_escape
from typing import Dict, List, Tuple
from engine.components import engineering_notation


def _safe(text: str) -> str:
    """Escape text for safe SVG embedding (prevent XSS)."""
    return html_escape(str(text), quote=True)


# SVG symbol paths (drawn at origin, to be translated)
# All symbols are 60px wide, centered vertically

def _svg_resistor(x: float, y: float, ref: str, value_str: str, horizontal: bool = True) -> str:
    """Generate SVG for a resistor symbol (zigzag)."""
    if horizontal:
        # Zigzag pattern
        points = [
            (x - 30, y), (x - 20, y), (x - 17, y - 8), (x - 11, y + 8),
            (x - 5, y - 8), (x + 1, y + 8), (x + 7, y - 8), (x + 13, y + 8),
            (x + 17, y - 8), (x + 20, y), (x + 30, y),
        ]
        path_d = ' '.join(f"{'M' if i == 0 else 'L'} {px} {py}" for i, (px, py) in enumerate(points))
        label_y = y - 15
        value_y = y + 20
    else:
        points = [
            (x, y - 30), (x, y - 20), (x - 8, y - 17), (x + 8, y - 11),
            (x - 8, y - 5), (x + 8, y + 1), (x - 8, y + 7), (x + 8, y + 13),
            (x - 8, y + 17), (x, y + 20), (x, y + 30),
        ]
        path_d = ' '.join(f"{'M' if i == 0 else 'L'} {px} {py}" for i, (px, py) in enumerate(points))
        label_y = y
        value_y = y + 15

    return f'''  <g class="component resistor">
    <path d="{path_d}" fill="none" stroke="#e2e8f0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="{x}" y="{label_y}" text-anchor="middle" fill="#3B82F6" font-size="11" font-family="monospace">{_safe(ref)}</text>
    <text x="{x}" y="{value_y}" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="monospace">{_safe(value_str)}</text>
  </g>'''


def _svg_capacitor(x: float, y: float, ref: str, value_str: str, horizontal: bool = True) -> str:
    """Generate SVG for a capacitor symbol (two parallel plates)."""
    if horizontal:
        svg = f'''  <g class="component capacitor">
    <line x1="{x-30}" y1="{y}" x2="{x-4}" y2="{y}" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="{x-4}" y1="{y-12}" x2="{x-4}" y2="{y+12}" stroke="#e2e8f0" stroke-width="2.5"/>
    <line x1="{x+4}" y1="{y-12}" x2="{x+4}" y2="{y+12}" stroke="#e2e8f0" stroke-width="2.5"/>
    <line x1="{x+4}" y1="{y}" x2="{x+30}" y2="{y}" stroke="#e2e8f0" stroke-width="2"/>
    <text x="{x}" y="{y-18}" text-anchor="middle" fill="#3B82F6" font-size="11" font-family="monospace">{_safe(ref)}</text>
    <text x="{x}" y="{y+25}" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="monospace">{_safe(value_str)}</text>
  </g>'''
    else:
        svg = f'''  <g class="component capacitor">
    <line x1="{x}" y1="{y-30}" x2="{x}" y2="{y-4}" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="{x-12}" y1="{y-4}" x2="{x+12}" y2="{y-4}" stroke="#e2e8f0" stroke-width="2.5"/>
    <line x1="{x-12}" y1="{y+4}" x2="{x+12}" y2="{y+4}" stroke="#e2e8f0" stroke-width="2.5"/>
    <line x1="{x}" y1="{y+4}" x2="{x}" y2="{y+30}" stroke="#e2e8f0" stroke-width="2"/>
    <text x="{x+20}" y="{y-5}" text-anchor="start" fill="#3B82F6" font-size="11" font-family="monospace">{_safe(ref)}</text>
    <text x="{x+20}" y="{y+10}" text-anchor="start" fill="#94a3b8" font-size="10" font-family="monospace">{_safe(value_str)}</text>
  </g>'''
    return svg


def _svg_inductor(x: float, y: float, ref: str, value_str: str, horizontal: bool = True) -> str:
    """Generate SVG for an inductor symbol (coil arcs)."""
    if horizontal:
        # Four humps
        arcs = (
            f'M {x-30} {y} L {x-20} {y} '
            f'A 5 5 0 0 1 {x-10} {y} '
            f'A 5 5 0 0 1 {x} {y} '
            f'A 5 5 0 0 1 {x+10} {y} '
            f'A 5 5 0 0 1 {x+20} {y} '
            f'L {x+30} {y}'
        )
        label_y = y - 15
        value_y = y + 20
    else:
        arcs = (
            f'M {x} {y-30} L {x} {y-20} '
            f'A 5 5 0 0 1 {x} {y-10} '
            f'A 5 5 0 0 1 {x} {y} '
            f'A 5 5 0 0 1 {x} {y+10} '
            f'A 5 5 0 0 1 {x} {y+20} '
            f'L {x} {y+30}'
        )
        label_y = y
        value_y = y + 15

    return f'''  <g class="component inductor">
    <path d="{arcs}" fill="none" stroke="#e2e8f0" stroke-width="2" stroke-linecap="round"/>
    <text x="{x}" y="{label_y}" text-anchor="middle" fill="#3B82F6" font-size="11" font-family="monospace">{_safe(ref)}</text>
    <text x="{x}" y="{value_y}" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="monospace">{_safe(value_str)}</text>
  </g>'''


def _svg_driver(x: float, y: float, ref: str = 'SPK') -> str:
    """Generate SVG for a loudspeaker/driver symbol."""
    return f'''  <g class="component driver">
    <rect x="{x-8}" y="{y-15}" width="16" height="30" fill="none" stroke="#e2e8f0" stroke-width="2"/>
    <polygon points="{x+8},{y-15} {x+22},{y-25} {x+22},{y+25} {x+8},{y+15}" fill="none" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="{x-8}" y1="{y-8}" x2="{x-25}" y2="{y-8}" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="{x-8}" y1="{y+8}" x2="{x-25}" y2="{y+8}" stroke="#e2e8f0" stroke-width="2"/>
    <text x="{x}" y="{y+40}" text-anchor="middle" fill="#3B82F6" font-size="11" font-family="monospace">{_safe(ref)}</text>
  </g>'''


def _svg_ground(x: float, y: float) -> str:
    """Generate SVG for a ground symbol."""
    return f'''  <g class="symbol ground">
    <line x1="{x}" y1="{y}" x2="{x}" y2="{y+8}" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="{x-12}" y1="{y+8}" x2="{x+12}" y2="{y+8}" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="{x-8}" y1="{y+13}" x2="{x+8}" y2="{y+13}" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="{x-4}" y1="{y+18}" x2="{x+4}" y2="{y+18}" stroke="#e2e8f0" stroke-width="2"/>
  </g>'''


def _svg_wire(x1: float, y1: float, x2: float, y2: float) -> str:
    """Generate SVG for a wire."""
    return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#e2e8f0" stroke-width="2"/>'


def _svg_junction(x: float, y: float) -> str:
    """Generate SVG for a wire junction dot."""
    return f'  <circle cx="{x}" cy="{y}" r="3" fill="#3B82F6"/>'


def _svg_terminal(x: float, y: float, label: str) -> str:
    """Generate SVG for an input/output terminal."""
    return f'''  <g class="terminal">
    <circle cx="{x}" cy="{y}" r="4" fill="none" stroke="#3B82F6" stroke-width="2"/>
    <text x="{x}" y="{y-10}" text-anchor="middle" fill="#3B82F6" font-size="10" font-family="monospace">{label}</text>
  </g>'''


def _value_display(comp: Dict) -> str:
    """Format component value for display."""
    value = comp.get('value', 0)
    unit = comp.get('unit', '')
    comp_type = comp.get('type', '')

    unit_map = {
        'resistor': 'Ω',
        'capacitor': 'F',
        'inductor': 'H',
    }
    display_unit = unit if unit else unit_map.get(comp_type, '')
    return engineering_notation(value, display_unit)


def generate_schematic_svg(circuit_design: Dict) -> str:
    """
    Generate an SVG schematic from a CircuitDesign JSON structure.

    Lays out components in a readable horizontal arrangement with
    proper EDA symbols and wire connections.
    """
    components = circuit_design.get('components', [])
    topology = circuit_design.get('topology', 'circuit')

    if not components:
        return _empty_svg(topology)

    # Layout strategy: place components in a horizontal chain
    # with parallel branches stacked vertically
    margin = 60
    comp_spacing = 120
    branch_spacing = 80
    width = margin * 2 + max(len(components), 3) * comp_spacing
    height = 300

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">',
        f'  <rect width="{width}" height="{height}" fill="#0f172a" rx="8"/>',
        f'  <text x="{width/2}" y="25" text-anchor="middle" fill="#64748b" '
        f'font-size="13" font-family="monospace">{topology}</text>',
    ]

    # Classify components into series and parallel groups
    series_comps = []
    parallel_groups = _group_parallel_components(components, circuit_design.get('subcircuits', []))

    if not parallel_groups:
        # Simple series layout
        y_center = height // 2
        x_start = margin + 30

        # Input terminal
        svg_parts.append(_svg_terminal(margin, y_center, 'IN+'))

        for i, comp in enumerate(components):
            x = x_start + i * comp_spacing
            val_str = _value_display(comp)

            # Wire from previous
            if i == 0:
                svg_parts.append(_svg_wire(margin + 4, y_center, x - 30, y_center))
            else:
                prev_x = x_start + (i - 1) * comp_spacing
                svg_parts.append(_svg_wire(prev_x + 30, y_center, x - 30, y_center))

            # Component symbol
            if comp['type'] == 'resistor':
                svg_parts.append(_svg_resistor(x, y_center, comp['ref'], val_str))
            elif comp['type'] == 'capacitor':
                svg_parts.append(_svg_capacitor(x, y_center, comp['ref'], val_str))
            elif comp['type'] == 'inductor':
                svg_parts.append(_svg_inductor(x, y_center, comp['ref'], val_str))
            elif comp['type'] == 'driver':
                svg_parts.append(_svg_driver(x, y_center, comp['ref']))

        # Output terminal
        last_x = x_start + (len(components) - 1) * comp_spacing
        svg_parts.append(_svg_wire(last_x + 30, y_center, width - margin - 4, y_center))
        svg_parts.append(_svg_terminal(width - margin, y_center, 'OUT+'))

        # Ground rail
        svg_parts.append(_svg_wire(margin, y_center + 60, width - margin, y_center + 60))
        svg_parts.append(_svg_ground(width // 2, y_center + 60))
        svg_parts.append(_svg_terminal(margin, y_center + 60, 'IN-'))
        svg_parts.append(_svg_terminal(width - margin, y_center + 60, 'OUT-'))
    else:
        # Layout with parallel branches
        y_center = height // 2
        x_start = margin + 30

        svg_parts.append(_svg_terminal(margin, y_center, 'IN+'))
        svg_parts.append(_svg_wire(margin + 4, y_center, x_start - 30, y_center))

        x_current = x_start
        for group in parallel_groups:
            if isinstance(group, dict):
                # Single series component
                val_str = _value_display(group)
                if group['type'] == 'resistor':
                    svg_parts.append(_svg_resistor(x_current, y_center, group['ref'], val_str))
                elif group['type'] == 'capacitor':
                    svg_parts.append(_svg_capacitor(x_current, y_center, group['ref'], val_str))
                elif group['type'] == 'inductor':
                    svg_parts.append(_svg_inductor(x_current, y_center, group['ref'], val_str))
                x_current += comp_spacing
            elif isinstance(group, list):
                # Parallel branch — stack vertically
                for j, comp in enumerate(group):
                    y_pos = y_center - 40 + j * branch_spacing
                    val_str = _value_display(comp)
                    if comp['type'] == 'resistor':
                        svg_parts.append(_svg_resistor(x_current, y_pos, comp['ref'], val_str))
                    elif comp['type'] == 'capacitor':
                        svg_parts.append(_svg_capacitor(x_current, y_pos, comp['ref'], val_str))
                    elif comp['type'] == 'inductor':
                        svg_parts.append(_svg_inductor(x_current, y_pos, comp['ref'], val_str))
                x_current += comp_spacing

        svg_parts.append(_svg_terminal(width - margin, y_center, 'OUT+'))
        svg_parts.append(_svg_wire(margin, y_center + 80, width - margin, y_center + 80))
        svg_parts.append(_svg_ground(width // 2, y_center + 80))

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def _empty_svg(title: str) -> str:
    """Return an empty schematic SVG with just a title."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200">'
        '<rect width="400" height="200" fill="#0f172a" rx="8"/>'
        f'<text x="200" y="100" text-anchor="middle" fill="#64748b" '
        f'font-size="14" font-family="monospace">No components in {title}</text>'
        '</svg>'
    )


def _group_parallel_components(components: List[Dict], subcircuits: List[Dict]) -> List:
    """
    Group components into series/parallel layout groups based on subcircuit info.
    Returns a flat list — each element is either a component dict (series)
    or a list of component dicts (parallel group).
    """
    if not subcircuits:
        return []  # Fall back to simple series layout

    # Build mapping of ref → component
    comp_map = {c['ref']: c for c in components}
    used_refs = set()
    groups = []

    for sc in subcircuits:
        refs = sc.get('components', [])
        group_comps = [comp_map[r] for r in refs if r in comp_map]
        if len(group_comps) > 1:
            groups.append(group_comps)
        elif len(group_comps) == 1:
            groups.append(group_comps[0])
        used_refs.update(refs)

    # Add remaining components as series
    for comp in components:
        if comp['ref'] not in used_refs:
            groups.append(comp)

    return groups


def generate_kicad_schematic(circuit_design: Dict) -> str:
    """
    Generate a KiCad 7+ .kicad_sch file content string.

    This is a minimal but valid schematic that KiCad can open.
    """
    components = circuit_design.get('components', [])
    topology = circuit_design.get('topology', 'HardForge Circuit')

    # KiCad schematic header
    sch = {
        'version': 20230121,
        'generator': 'hardforge',
        'uuid': _pseudo_uuid('sch-root'),
        'paper': 'A4',
    }

    lines = [
        '(kicad_sch (version 20230121) (generator "hardforge")',
        f'  (uuid "{sch["uuid"]}")',
        '  (paper "A4")',
        '',
        '  (lib_symbols',
    ]

    # Add library symbols for each component type used
    comp_types_used = set(c['type'] for c in components)
    if 'resistor' in comp_types_used:
        lines.append(_kicad_lib_symbol_resistor())
    if 'capacitor' in comp_types_used:
        lines.append(_kicad_lib_symbol_capacitor())
    if 'inductor' in comp_types_used:
        lines.append(_kicad_lib_symbol_inductor())

    lines.append('  )')
    lines.append('')

    # Place components
    x_start = 50.0
    y_center = 100.0
    spacing = 30.0

    for i, comp in enumerate(components):
        x = x_start + i * spacing
        ref = comp['ref']
        val_str = _value_display(comp)
        uuid = _pseudo_uuid(f'comp-{ref}')

        kicad_type = {'resistor': 'R', 'capacitor': 'C', 'inductor': 'L'}.get(comp['type'], 'R')

        lines.append(f'  (symbol')
        lines.append(f'    (lib_id "Device:{kicad_type}")')
        lines.append(f'    (at {x:.2f} {y_center:.2f} 0)')
        lines.append(f'    (uuid "{uuid}")')
        lines.append(f'    (property "Reference" "{ref}" (at {x:.2f} {y_center - 5:.2f} 0)')
        lines.append(f'      (effects (font (size 1.27 1.27)))')
        lines.append(f'    )')
        lines.append(f'    (property "Value" "{val_str}" (at {x:.2f} {y_center + 5:.2f} 0)')
        lines.append(f'      (effects (font (size 1.27 1.27)))')
        lines.append(f'    )')
        lines.append(f'  )')
        lines.append('')

    lines.append(')')
    lines.append('')

    return '\n'.join(lines)


def generate_kicad_project(circuit_design: Dict) -> Dict[str, str]:
    """
    Generate a complete KiCad project as a dict of {filename: content}.

    Can be zipped for download.
    """
    topology = circuit_design.get('topology', 'hardforge_circuit')
    safe_name = topology.replace(' ', '_').lower()

    schematic = generate_kicad_schematic(circuit_design)

    # Minimal KiCad project file
    project_json = json.dumps({
        'meta': {
            'filename': f'{safe_name}.kicad_pro',
            'version': 1,
        },
        'schematic': {
            'drawing': {'default_line_thickness': 6.0},
        },
    }, indent=2)

    return {
        f'{safe_name}.kicad_sch': schematic,
        f'{safe_name}.kicad_pro': project_json,
    }


def _pseudo_uuid(seed: str) -> str:
    """Generate a deterministic UUID-like string from a seed (for reproducibility)."""
    import hashlib
    h = hashlib.sha256(seed.encode()).hexdigest()
    return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}'


def _kicad_lib_symbol_resistor() -> str:
    return '''    (symbol "Device:R" (pin_numbers hide) (pin_names hide)
      (in_bom yes) (on_board yes)
      (property "Reference" "R" (at 2.032 0 90) (effects (font (size 1.27 1.27))))
      (property "Value" "R" (at -2.032 0 90) (effects (font (size 1.27 1.27))))
      (symbol "R_0_1"
        (rectangle (start -1.016 -2.54) (end 1.016 2.54) (stroke (width 0.254)) (fill (type none)))
      )
      (symbol "R_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )'''


def _kicad_lib_symbol_capacitor() -> str:
    return '''    (symbol "Device:C" (pin_numbers hide) (pin_names hide)
      (in_bom yes) (on_board yes)
      (property "Reference" "C" (at 2.032 0 90) (effects (font (size 1.27 1.27))))
      (property "Value" "C" (at -2.032 0 90) (effects (font (size 1.27 1.27))))
      (symbol "C_0_1"
        (polyline (pts (xy -1.524 -0.508) (xy 1.524 -0.508)) (stroke (width 0.3048)) (fill (type none)))
        (polyline (pts (xy -1.524 0.508) (xy 1.524 0.508)) (stroke (width 0.3048)) (fill (type none)))
      )
      (symbol "C_1_1"
        (pin passive line (at 0 2.54 270) (length 2.032) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -2.54 90) (length 2.032) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )'''


def _kicad_lib_symbol_inductor() -> str:
    return '''    (symbol "Device:L" (pin_numbers hide) (pin_names hide)
      (in_bom yes) (on_board yes)
      (property "Reference" "L" (at 1.524 0 90) (effects (font (size 1.27 1.27))))
      (property "Value" "L" (at -1.524 0 90) (effects (font (size 1.27 1.27))))
      (symbol "L_0_1"
        (arc (start 0 -2.54) (mid 0.635 -1.905) (end 0 -1.27) (stroke (width 0.254)) (fill (type none)))
        (arc (start 0 -1.27) (mid 0.635 -0.635) (end 0 0) (stroke (width 0.254)) (fill (type none)))
        (arc (start 0 0) (mid 0.635 0.635) (end 0 1.27) (stroke (width 0.254)) (fill (type none)))
        (arc (start 0 1.27) (mid 0.635 1.905) (end 0 2.54) (stroke (width 0.254)) (fill (type none)))
      )
      (symbol "L_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )'''
