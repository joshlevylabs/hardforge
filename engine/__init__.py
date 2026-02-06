"""
HardForge Compute Engine

Core computation library for loudspeaker impedance modeling,
correction network design, and circuit generation.

All math is deterministic — no AI in the loop for numerical calculations.
"""

from engine.components import snap_to_e_series, engineering_notation
from engine.impedance import calculate_impedance, parse_impedance_csv, interpolate_impedance, generate_frequencies
from engine.correction import zobel_network, notch_filter, full_correction, calculate_corrected_impedance
from engine.topology import TopologyDefinition, get_topology, list_topologies
from engine.simulation import ac_analysis, impedance_analysis
from engine.bom import generate_bom, export_csv, export_json
from engine.ts_database import search_drivers, get_driver
from engine.kicad_export import generate_schematic_svg, generate_kicad_schematic, generate_kicad_project
from engine.skidl_gen import generate_skidl_code, generate_netlist

__version__ = "0.1.0"
