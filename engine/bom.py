"""
Bill of Materials generation from circuit designs.

Generates BOM in multiple formats (dict, CSV, JSON) with estimated pricing,
E-series snapping, and footprint assignment.
"""

import csv
import io
import json
from typing import Dict, List, Optional

from engine.components import engineering_notation, snap_to_e_series


# Rough cost estimates per component type (USD)
_COST_ESTIMATES = {
    'resistor': {
        'base': 0.05,
        'power_multiplier': {  # per watt above 0.25W
            0.25: 0.05,
            0.5: 0.10,
            1.0: 0.15,
            2.0: 0.30,
            5.0: 0.80,
            10.0: 1.50,
            25.0: 3.00,
        },
    },
    'capacitor': {
        'base': 0.10,
        'value_multiplier': {  # by capacitance range
            1e-12: 0.10,   # pF range
            1e-9: 0.10,    # nF range
            1e-6: 0.20,    # µF range
            1e-3: 1.00,    # mF range (electrolytic)
        },
    },
    'inductor': {
        'base': 0.50,
        'value_multiplier': {  # by inductance range
            1e-6: 0.30,    # µH range
            1e-3: 1.00,    # mH range
            1e-1: 3.00,    # large inductors
        },
    },
}


def _estimate_price(comp_type: str, value: float, power_rating: Optional[float] = None) -> float:
    """Estimate component cost in USD."""
    if comp_type not in _COST_ESTIMATES:
        return 0.25  # Default fallback

    info = _COST_ESTIMATES[comp_type]
    price = info['base']

    if comp_type == 'resistor' and power_rating:
        for threshold, mult in sorted(info['power_multiplier'].items()):
            if power_rating <= threshold:
                price += mult
                break
        else:
            price += 5.00  # Very high power

    elif comp_type in ('capacitor', 'inductor') and value > 0:
        for threshold, mult in sorted(info['value_multiplier'].items()):
            if value <= threshold:
                price += mult
                break
        else:
            price += 2.00

    return round(price, 2)


def generate_bom(circuit_design: Dict, snap_series: str = 'E24') -> List[Dict]:
    """
    Generate a Bill of Materials from a circuit design.

    Snaps component values to nearest E-series standard values,
    assigns footprints, and estimates costs.

    Args:
        circuit_design: Dict with 'components' list, each having:
            ref, type, value, unit, footprint, power_rating, description
        snap_series: E-series to snap to ('E12', 'E24', 'E48', 'E96')

    Returns:
        List of BOM entry dicts with ref, value, value_display, footprint,
        quantity, description, estimated_price, and E-series snap info.
    """
    components = circuit_design.get('components', [])
    bom = []

    for comp in components:
        comp_type = comp.get('type', 'resistor')
        value = comp.get('value', 0)
        unit = comp.get('unit', '')
        power_rating = comp.get('power_rating')

        # Skip drivers — user supplies those
        if comp_type == 'driver':
            continue

        value_display = engineering_notation(value, unit)
        estimated_price = _estimate_price(comp_type, value, power_rating)

        # E-series snapping
        snap_info = None
        if value > 0 and comp_type in ('resistor', 'capacitor', 'inductor'):
            snapped_value, snap_error = snap_to_e_series(value, snap_series)
            snap_info = {
                'target': value,
                'actual': snapped_value,
                'error_pct': snap_error,
                'series': snap_series,
            }

        entry = {
            'ref': comp.get('ref', ''),
            'type': comp_type,
            'value': value,
            'value_display': value_display,
            'unit': unit,
            'footprint': comp.get('footprint', ''),
            'quantity': 1,
            'description': comp.get('description', f'{comp_type} {value_display}'),
            'power_rating': power_rating,
            'tolerance': comp.get('tolerance', '5%'),
            'estimated_price': estimated_price,
            'e_series_snapped': snap_info,
        }
        bom.append(entry)

    return bom


def estimate_cost(bom: List[Dict]) -> Dict:
    """
    Estimate total cost from a BOM.

    Returns cost breakdown and total.
    """
    total = 0.0
    by_type = {}

    for entry in bom:
        cost = entry.get('estimated_price', 0) * entry.get('quantity', 1)
        total += cost
        comp_type = entry.get('type', 'other')
        by_type[comp_type] = by_type.get(comp_type, 0.0) + cost

    return {
        'total_usd': round(total, 2),
        'by_type': {k: round(v, 2) for k, v in by_type.items()},
        'component_count': sum(e.get('quantity', 1) for e in bom),
        'note': 'Rough estimate for budgeting. Actual costs vary by supplier and quantity.',
    }


def total_cost(bom: List[Dict]) -> float:
    """Calculate total estimated cost of a BOM."""
    return round(sum(entry.get('estimated_price', 0) * entry.get('quantity', 1) for entry in bom), 2)


def export_csv(bom: List[Dict]) -> str:
    """Export BOM as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Reference', 'Type', 'Value', 'Footprint', 'Quantity',
        'Description', 'Power Rating', 'Tolerance', 'Est. Price (USD)'
    ])

    for entry in bom:
        writer.writerow([
            entry['ref'],
            entry['type'],
            entry['value_display'],
            entry['footprint'],
            entry['quantity'],
            entry['description'],
            f"{entry['power_rating']}W" if entry.get('power_rating') else '',
            entry.get('tolerance', ''),
            f"${entry.get('estimated_price', 0):.2f}",
        ])

    # Total row
    writer.writerow(['', '', '', '', '', '', '', 'TOTAL:', f"${total_cost(bom):.2f}"])

    return output.getvalue()


def export_json(bom: List[Dict]) -> str:
    """Export BOM as JSON string."""
    export_data = {
        'bom': bom,
        'cost_estimate': estimate_cost(bom),
        'generated_by': 'HardForge Engine',
    }
    return json.dumps(export_data, indent=2)
