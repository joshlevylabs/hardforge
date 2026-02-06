"""Export routes — schematic SVG, KiCad files, Gerber, BOM."""

import io
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.models import (
    BOMEntry,
    BOMRequest,
    BOMResponse,
    SchematicRequest,
    SchematicResponse,
)
from engine.bom import generate_bom, export_csv
from engine.kicad_export import generate_schematic_svg, generate_kicad_project
from engine.skidl_gen import generate_skidl_code

router = APIRouter()


@router.post("/generate-schematic", response_model=SchematicResponse)
async def generate_schematic(request: SchematicRequest):
    """Generate schematic SVG and optional KiCad .kicad_sch file."""
    try:
        design_dict = request.design.model_dump()
        svg = generate_schematic_svg(design_dict)
        kicad_sch = None  # KiCad schematic generation is pro-tier

        return SchematicResponse(svg=svg, kicad_sch=kicad_sch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schematic generation failed: {str(e)}")


@router.post("/generate-skidl")
async def generate_skidl(request: SchematicRequest):
    """Generate SKiDL Python source code for the circuit."""
    try:
        design_dict = request.design.model_dump()
        code = generate_skidl_code(design_dict)
        return {"skidl_code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SKiDL generation failed: {str(e)}")


@router.post("/generate-kicad-project")
async def generate_kicad_project_endpoint(request: SchematicRequest):
    """Generate a complete KiCad project as a ZIP file."""
    try:
        design_dict = request.design.model_dump()
        project_files = generate_kicad_project(design_dict)

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, content in project_files.items():
                zf.writestr(f"hardforge_project/{filename}", content)

        zip_buffer.seek(0)
        return Response(
            content=zip_buffer.read(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=hardforge_project.zip"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KiCad project generation failed: {str(e)}")


@router.post("/generate-bom", response_model=BOMResponse)
async def generate_bom_endpoint(request: BOMRequest):
    """Generate Bill of Materials from circuit design."""
    try:
        design_dict = request.design.model_dump()
        bom = generate_bom(design_dict)

        entries = [
            BOMEntry(
                ref=item["ref"],
                value=item["value_display"],
                description=item["description"],
                footprint=item["footprint"],
                quantity=item["quantity"],
                estimated_price=item.get("estimated_price"),
            )
            for item in bom
        ]

        total_cost = sum(e.estimated_price or 0 for e in entries)
        csv_content = export_csv(bom)

        return BOMResponse(entries=entries, total_cost=total_cost, csv=csv_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BOM generation failed: {str(e)}")
