"""Export routes — schematic SVG, KiCad files, Gerber, BOM."""

import io
import logging
import os
import zipfile

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.models import (
    BOMEntry,
    BOMRequest,
    BOMResponse,
    DistributorOptionModel,
    EnrichedBOMEntry,
    EnrichedBOMResponse,
    PriceBreakModel,
    SchematicRequest,
    SchematicResponse,
)
from backend.services.distributor import NexarClient
from engine.bom import generate_bom, export_csv
from engine.kicad_export import generate_schematic_svg, generate_kicad_project
from engine.skidl_gen import generate_skidl_code

logger = logging.getLogger(__name__)

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


@router.post("/generate-bom")
async def generate_bom_endpoint(
    request: BOMRequest,
    enrich: bool = Query(default=True, description="Attempt distributor enrichment"),
):
    """Generate Bill of Materials from circuit design.

    If Nexar API credentials are configured and enrich=true, returns an
    EnrichedBOMResponse with real distributor pricing and availability.
    Otherwise falls back to BOMResponse with estimated pricing.
    """
    try:
        design_dict = request.design.model_dump()
        bom = generate_bom(design_dict)
        csv_content = export_csv(bom)

        nexar_id = os.getenv("NEXAR_CLIENT_ID")
        nexar_secret = os.getenv("NEXAR_CLIENT_SECRET")

        if enrich and nexar_id and nexar_secret:
            return await _enriched_bom_response(bom, csv_content, nexar_id, nexar_secret)

        # Fallback: return standard BOM with estimated pricing
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
        return BOMResponse(entries=entries, total_cost=total_cost, csv=csv_content)

    except Exception as e:
        raise HTTPException(status_code=500, detail="BOM generation failed")


async def _enriched_bom_response(
    bom: list[dict],
    csv_content: str,
    nexar_id: str,
    nexar_secret: str,
) -> EnrichedBOMResponse:
    """Try Nexar enrichment; fall back to estimated pricing on failure."""
    client = NexarClient(nexar_id, nexar_secret)

    try:
        enriched_items = await client.enrich_bom(bom)
    except Exception:
        logger.warning("Nexar enrichment failed, returning estimates", exc_info=True)
        entries = [
            EnrichedBOMEntry(
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
        return EnrichedBOMResponse(
            entries=entries,
            total_cost=total_cost,
            csv=csv_content,
            enrichment_status="unavailable",
        )

    entries = []
    has_any_enrichment = False
    all_enriched = True

    for item in enriched_items:
        dist_options = [
            DistributorOptionModel(
                distributor=opt["distributor"],
                sku=opt["sku"],
                unit_price=opt["unit_price"],
                stock=opt["stock"],
                url=opt["url"],
                price_breaks=[
                    PriceBreakModel(quantity=pb["quantity"], unit_price=pb["unit_price"])
                    for pb in opt.get("price_breaks", [])
                ],
            )
            for opt in item.get("distributor_options", [])
        ]

        if dist_options:
            has_any_enrichment = True
        else:
            all_enriched = False

        entries.append(
            EnrichedBOMEntry(
                ref=item["ref"],
                value=item["value_display"],
                description=item["description"],
                footprint=item["footprint"],
                quantity=item["quantity"],
                estimated_price=item.get("estimated_price"),
                mpn=item.get("mpn"),
                manufacturer=item.get("manufacturer"),
                distributor_options=dist_options,
                best_price=item.get("best_price"),
            )
        )

    total_cost = sum(e.estimated_price or 0 for e in entries)
    total_best = sum(e.best_price or e.estimated_price or 0 for e in entries)

    if has_any_enrichment and all_enriched:
        status = "full"
    elif has_any_enrichment:
        status = "partial"
    else:
        status = "unavailable"

    return EnrichedBOMResponse(
        entries=entries,
        total_cost=total_cost,
        total_best_price=total_best if has_any_enrichment else None,
        csv=csv_content,
        enrichment_status=status,
    )
