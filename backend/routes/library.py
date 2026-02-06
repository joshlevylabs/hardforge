"""Library routes — driver database, impedance curves, topologies."""

import csv
import io
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File

from backend.models import DriverInfo, DriverListResponse, ImpedanceResponse
from engine.impedance import calculate_impedance, generate_frequencies, parse_impedance_csv
from engine.topology import list_topologies as get_all_topologies_list

router = APIRouter()


@router.get("/library/drivers", response_model=DriverListResponse)
async def list_drivers(
    request: Request,
    q: Optional[str] = Query(None, description="Search query"),
    manufacturer: Optional[str] = Query(None),
    driver_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Search and list loudspeaker drivers with TS parameters."""
    db = request.app.state.driver_db
    drivers = db.search(query=q, manufacturer=manufacturer, driver_type=driver_type)

    # Paginate
    total = len(drivers)
    drivers = drivers[offset:offset + limit]

    driver_infos = [
        DriverInfo(
            id=d.get("id", ""),
            manufacturer=d["manufacturer"],
            model=d["model"],
            driver_type=d.get("driver_type", "woofer"),
            re=d["re"],
            le=d.get("le"),
            fs=d["fs"],
            qms=d["qms"],
            qes=d["qes"],
            qts=d["qts"],
            vas=d.get("vas"),
            bl=d.get("bl"),
            mms=d.get("mms"),
            nominal_impedance=d.get("nominal_impedance", 8.0),
            power_rating=d.get("power_rating"),
            sensitivity=d.get("sensitivity"),
        )
        for d in drivers
    ]

    return DriverListResponse(drivers=driver_infos, total=total)


@router.get("/library/drivers/{driver_id}")
async def get_driver(request: Request, driver_id: str):
    """Get a specific driver's details and calculated impedance curve."""
    db = request.app.state.driver_db
    driver = db.get_by_id(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Calculate impedance curve
    freqs = generate_frequencies(20.0, 20000.0, 500)
    z_complex = calculate_impedance(driver, freqs)

    import numpy as np
    impedance = ImpedanceResponse(
        frequency=freqs.tolist(),
        magnitude=np.abs(z_complex).tolist(),
        phase=np.degrees(np.angle(z_complex)).tolist(),
    )

    return {
        "driver": DriverInfo(
            id=driver.get("id", ""),
            manufacturer=driver["manufacturer"],
            model=driver["model"],
            driver_type=driver.get("driver_type", "woofer"),
            re=driver["re"],
            le=driver.get("le"),
            fs=driver["fs"],
            qms=driver["qms"],
            qes=driver["qes"],
            qts=driver["qts"],
            vas=driver.get("vas"),
            bl=driver.get("bl"),
            mms=driver.get("mms"),
            nominal_impedance=driver.get("nominal_impedance", 8.0),
            power_rating=driver.get("power_rating"),
            sensitivity=driver.get("sensitivity"),
        ),
        "impedance": impedance,
    }


@router.post("/library/impedance-curves")
async def upload_impedance_curve(file: UploadFile = File(...)):
    """Upload a measured impedance curve CSV file.

    Expected CSV format: frequency(Hz), magnitude(Ohms), phase(degrees)
    Maximum 50,000 rows, 5MB file size.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    # Read file in chunks to prevent memory exhaustion (S-3)
    max_size = 5 * 1024 * 1024  # 5MB
    chunks = []
    total_size = 0
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(status_code=413, detail="File too large. Maximum 5MB.")
        chunks.append(chunk)
    contents = b"".join(chunks)

    try:
        csv_text = contents.decode("utf-8")
        frequencies, magnitudes, phases = parse_impedance_csv(csv_text)

        # Enforce row limit
        if len(frequencies) > 50000:
            raise HTTPException(
                status_code=400,
                detail="Too many data points. Maximum 50,000 rows."
            )

        return ImpedanceResponse(
            frequency=frequencies.tolist(),
            magnitude=magnitudes.tolist(),
            phase=phases.tolist() if phases is not None else [],
        )
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid CSV format. Expected columns: frequency, magnitude, phase (optional).")
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to parse impedance CSV. Check file format.")


@router.get("/library/topologies")
async def list_topologies():
    """List all available circuit topologies."""
    topologies = get_all_topologies_list()
    return {
        "topologies": [
            {
                "name": t["name"],
                "description": t["description"],
                "category": t["category"],
                "use_cases": t["use_cases"],
                "component_slots": t.get("component_slots", []),
            }
            for t in topologies
        ]
    }
