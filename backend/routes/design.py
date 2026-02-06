"""Design route — computes circuits using the engine."""

import numpy as np
from fastapi import APIRouter, HTTPException

from backend.models import (
    CircuitComponent,
    CircuitDesign,
    ComponentType,
    Connection,
    CorrectionRequest,
    CorrectionResponse,
    DesignCircuitRequest,
    DesignCircuitResponse,
    ESeriesSnap,
    ImpedanceRequest,
    ImpedanceResponse,
)
from engine.components import snap_to_e_series, engineering_notation
from engine.skidl_gen import _select_footprint
from engine.correction import (
    calculate_corrected_impedance,
    full_correction,
    notch_filter,
    zobel_network,
)
from engine.impedance import calculate_impedance, generate_frequencies

router = APIRouter()


@router.post("/calculate-impedance", response_model=ImpedanceResponse)
async def calculate_impedance_endpoint(request: ImpedanceRequest):
    """Calculate impedance curve from Thiele-Small parameters."""
    try:
        ts = request.ts_params.model_dump()
        freqs = generate_frequencies(request.freq_start, request.freq_end, request.num_points)
        z_complex = calculate_impedance(ts, freqs)

        magnitude = np.abs(z_complex).tolist()
        phase = np.degrees(np.angle(z_complex)).tolist()

        return ImpedanceResponse(
            frequency=freqs.tolist(),
            magnitude=magnitude,
            phase=phase,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Impedance calculation failed. Check that all TS parameters are valid.")


@router.post("/calculate-components", response_model=CorrectionResponse)
async def calculate_correction(request: CorrectionRequest):
    """Calculate impedance correction network components."""
    try:
        ts = request.ts_params.model_dump()
        freqs = generate_frequencies(20.0, 20000.0, 500)

        components = []
        zobel_result = None
        notch_result = None

        if request.include_zobel and (ts.get("le") or 0) > 0:
            # Engine's zobel_network takes Re (Ohms) and Le (mH), returns a dict
            zobel_data = zobel_network(ts["re"], ts["le"])
            rz = zobel_data["Rz"]
            cz = zobel_data["Cz"]

            rz_snapped, rz_err = snap_to_e_series(rz, request.e_series)
            cz_snapped, cz_err = snap_to_e_series(cz, request.e_series)

            zobel_result = {
                "Rz": rz,
                "Rz_snapped": rz_snapped,
                "Rz_unit": "Ohm",
                "Cz": cz,
                "Cz_snapped": cz_snapped,
                "Cz_unit": "F",
                "Cz_display": engineering_notation(cz, "F"),
            }

            rz_footprint = _select_footprint({'type': 'resistor', 'value': rz_snapped, 'power_rating': 10.0})
            cz_footprint = _select_footprint({'type': 'capacitor', 'value': cz_snapped})

            components.extend([
                CircuitComponent(
                    ref="R_Z1",
                    type=ComponentType.RESISTOR,
                    value=rz_snapped,
                    unit="Ohm",
                    footprint=rz_footprint,
                    power_rating=10.0,
                    description="Zobel network resistor",
                    e_series_snapped=ESeriesSnap(target=rz, actual=rz_snapped, error_pct=rz_err),
                ),
                CircuitComponent(
                    ref="C_Z1",
                    type=ComponentType.CAPACITOR,
                    value=cz_snapped,
                    unit="F",
                    footprint=cz_footprint,
                    description="Zobel network capacitor",
                    e_series_snapped=ESeriesSnap(target=cz, actual=cz_snapped, error_pct=cz_err),
                ),
            ])

        if request.include_notch:
            # Engine's notch_filter returns a dict
            notch_data = notch_filter(ts["fs"], ts["qms"], ts["qes"], ts["re"])
            rn = notch_data["R_notch"]
            ln = notch_data["L_notch"]
            cn = notch_data["C_notch"]

            rn_snapped, rn_err = snap_to_e_series(rn, request.e_series)
            ln_snapped, ln_err = snap_to_e_series(ln, request.e_series)
            cn_snapped, cn_err = snap_to_e_series(cn, request.e_series)

            notch_result = {
                "R_notch": rn,
                "R_notch_snapped": rn_snapped,
                "R_notch_unit": "Ohm",
                "L_notch": ln,
                "L_notch_snapped": ln_snapped,
                "L_notch_unit": "H",
                "L_notch_display": engineering_notation(ln, "H"),
                "C_notch": cn,
                "C_notch_snapped": cn_snapped,
                "C_notch_unit": "F",
                "C_notch_display": engineering_notation(cn, "F"),
            }

            rn_footprint = _select_footprint({'type': 'resistor', 'value': rn_snapped, 'power_rating': 10.0})
            ln_footprint = _select_footprint({'type': 'inductor', 'value': ln_snapped})
            cn_footprint = _select_footprint({'type': 'capacitor', 'value': cn_snapped})

            components.extend([
                CircuitComponent(
                    ref="R_N1",
                    type=ComponentType.RESISTOR,
                    value=rn_snapped,
                    unit="Ohm",
                    footprint=rn_footprint,
                    power_rating=10.0,
                    description="Notch filter resistor",
                    e_series_snapped=ESeriesSnap(target=rn, actual=rn_snapped, error_pct=rn_err),
                ),
                CircuitComponent(
                    ref="L_N1",
                    type=ComponentType.INDUCTOR,
                    value=ln_snapped,
                    unit="H",
                    footprint=ln_footprint,
                    description="Notch filter inductor",
                    e_series_snapped=ESeriesSnap(target=ln, actual=ln_snapped, error_pct=ln_err),
                ),
                CircuitComponent(
                    ref="C_N1",
                    type=ComponentType.CAPACITOR,
                    value=cn_snapped,
                    unit="F",
                    footprint=cn_footprint,
                    description="Notch filter capacitor",
                    e_series_snapped=ESeriesSnap(target=cn, actual=cn_snapped, error_pct=cn_err),
                ),
            ])

        # Calculate corrected impedance using engine's full_correction
        correction = full_correction(ts)
        z_corrected = calculate_corrected_impedance(ts, correction, freqs)

        corrected_response = ImpedanceResponse(
            frequency=freqs.tolist(),
            magnitude=np.abs(z_corrected).tolist(),
            phase=np.degrees(np.angle(z_corrected)).tolist(),
        )

        return CorrectionResponse(
            zobel=zobel_result,
            notch=notch_result,
            components=components,
            corrected_impedance=corrected_response,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Correction calculation failed. Check that TS parameters include Re, Le, fs, Qms, and Qes.")


@router.post("/design-circuit", response_model=DesignCircuitResponse)
async def design_circuit(request: DesignCircuitRequest):
    """Design a complete circuit from intent and selected topology."""
    try:
        from engine.topology import get_topology, calculate_topology
        from engine.components import engineering_notation as eng_notation

        intent = request.intent
        topology_name = request.selected_topology
        overrides = request.overrides or {}

        # Validate topology exists
        try:
            topology = get_topology(topology_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Build parameters from intent
        params = {}
        if intent.target_specs.nominal_impedance:
            params["impedance"] = intent.target_specs.nominal_impedance
        if intent.target_specs.crossover_freq:
            params["crossover_freq"] = intent.target_specs.crossover_freq
        if intent.target_specs.crossover_order:
            params["order"] = intent.target_specs.crossover_order
        if intent.target_specs.crossover_type:
            params["alignment"] = intent.target_specs.crossover_type
        if intent.target_specs.filter_freq:
            params["cutoff_freq"] = intent.target_specs.filter_freq
        if intent.target_specs.filter_type:
            params["filter_type"] = intent.target_specs.filter_type
        if intent.target_specs.driver and intent.target_specs.driver.ts_params:
            ts = intent.target_specs.driver.ts_params.model_dump()
            params.update(ts)

        # Apply user overrides
        params.update(overrides)

        # Calculate component values using engine
        comp_values = calculate_topology(topology_name, params)

        # Convert engine output to CircuitComponent list
        components = []
        warnings = []
        for ref, comp_data in comp_values.items():
            if not isinstance(comp_data, dict) or 'value' not in comp_data:
                continue

            comp_type_str = comp_data.get('type', 'resistor')
            try:
                comp_type = ComponentType(comp_type_str)
            except ValueError:
                comp_type = ComponentType.RESISTOR

            value = comp_data['value']
            unit = comp_data.get('unit', '')

            # E-series snap
            snapped_val, snap_err = snap_to_e_series(value, 'E24')
            snap_info = ESeriesSnap(target=value, actual=snapped_val, error_pct=snap_err)

            if abs(snap_err) > 5.0:
                warnings.append(
                    f"{ref}: E24 snap error is {snap_err:.1f}% — consider E48/E96 for tighter tolerance"
                )

            components.append(CircuitComponent(
                ref=ref,
                type=comp_type,
                value=snapped_val,
                unit=unit,
                description=comp_data.get('description', f'{comp_type_str} {eng_notation(value, unit)}'),
                e_series_snapped=snap_info,
            ))

        design = CircuitDesign(
            topology=topology_name,
            components=components,
            connections=[],
            warnings=warnings,
        )

        bom_summary = {
            "total_components": len(components),
            "resistors": sum(1 for c in components if c.type == ComponentType.RESISTOR),
            "capacitors": sum(1 for c in components if c.type == ComponentType.CAPACITOR),
            "inductors": sum(1 for c in components if c.type == ComponentType.INDUCTOR),
        }

        return DesignCircuitResponse(design=design, bom_summary=bom_summary)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Circuit design failed. Check topology name and input parameters.")
