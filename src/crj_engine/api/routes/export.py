"""POST /api/v1/export/pdf — render an analysis result to a printable PDF report."""

from __future__ import annotations

import io

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from pydantic import BaseModel

router = APIRouter()


class ExportPdfRequest(BaseModel):
    """Mirror of AnalysisResponse plus an export_script override.

    All fields default so partial payloads from older clients still work.
    """

    duration_s: float = 0.0
    reference_sa_hz: float = 261.63
    algorithm: str = ""
    script: str = "iast"
    unique_swaras: list[str] = []
    swara_sequence: list[str] = []
    notation_iast: str = ""
    notation_compact: str = ""
    notation_requested: str = ""
    phrases: list[dict] = []
    gamakas: list[dict] = []
    raga_candidates: list[dict] = []
    export_script: str = "iast"


def _safe_latin(text: str) -> str:
    """fpdf2 with built-in fonts only handles latin-1.

    Strip / approximate everything else so the PDF doesn't error on Devanagari etc.
    The IAST notation is mostly latin-1 already (with diacritics).
    """
    return text.encode("latin-1", "replace").decode("latin-1")


def _section_title(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 7, _safe_latin(text), ln=True)


def _info_row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(38, 5, _safe_latin(label), ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 5, _safe_latin(value), ln=True)


def _build_pdf(req: ExportPdfRequest) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(180, 130, 50)
    pdf.cell(0, 10, "CRJ SoundScape", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "Audio Analysis Report", ln=True, align="C")
    pdf.ln(4)

    # Summary
    _section_title(pdf, "Summary")
    pdf.ln(1)
    _info_row(pdf, "Duration", f"{req.duration_s:.2f} seconds")
    _info_row(pdf, "Algorithm", req.algorithm.upper() or "-")
    _info_row(pdf, "Reference Sa", f"{req.reference_sa_hz} Hz")
    _info_row(pdf, "Script", req.script)
    _info_row(pdf, "Unique Swaras", str(len(req.unique_swaras)))
    if req.unique_swaras:
        _info_row(pdf, "Swaras Detected", ", ".join(req.unique_swaras))
    pdf.ln(3)

    # Notation — Compact
    _section_title(pdf, "Notation (Compact)")
    pdf.set_font("Courier", "", 9)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 5, _safe_latin(req.notation_compact or "-"))
    pdf.ln(2)

    # Notation — IAST
    _section_title(pdf, "Notation (IAST)")
    pdf.set_font("Courier", "", 9)
    pdf.multi_cell(0, 5, _safe_latin(req.notation_iast or "-"))
    pdf.ln(2)

    # Notation — Requested script (if different)
    if req.notation_requested and req.notation_requested != req.notation_iast:
        _section_title(
            pdf, f"Notation ({(req.export_script or req.script).upper()})"
        )
        pdf.set_font("Courier", "", 9)
        pdf.multi_cell(0, 5, _safe_latin(req.notation_requested))
        pdf.ln(2)

    # Raga candidates
    if req.raga_candidates:
        _section_title(pdf, "Raga Candidates")
        pdf.ln(1)
        for rc in req.raga_candidates[:5]:
            name = rc.get("raga_name", "?")
            number = rc.get("raga_number", "")
            conf = rc.get("confidence", 0.0)
            line = f"  {name}"
            if number:
                line = f"  {number}. {name}"
            line += f"   {conf * 100:.1f}%"
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(20, 20, 20)
            pdf.cell(0, 5, _safe_latin(line), ln=True)

            arohana = rc.get("arohana") or []
            avarohana = rc.get("avarohana") or []
            if arohana or avarohana:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(110, 110, 110)
                if arohana:
                    pdf.cell(
                        0,
                        4,
                        _safe_latin(f"      Arohana:   {' '.join(arohana)}"),
                        ln=True,
                    )
                if avarohana:
                    pdf.cell(
                        0,
                        4,
                        _safe_latin(f"      Avarohana: {' '.join(avarohana)}"),
                        ln=True,
                    )
            pdf.ln(1)

    # Gamakas summary
    if req.gamakas:
        gamaka_groups: dict[str, int] = {}
        for g in req.gamakas:
            gtype = g.get("gamaka_type", "unknown")
            gamaka_groups[gtype] = gamaka_groups.get(gtype, 0) + 1
        pdf.ln(2)
        _section_title(pdf, "Gamakas Detected")
        pdf.ln(1)
        for gtype, count in sorted(
            gamaka_groups.items(), key=lambda x: -x[1]
        ):
            _info_row(pdf, gtype, f"{count} occurrences")

    # Footer note
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(
        0,
        4,
        "Generated by CRJ SoundScape - vedavishtaram.in/crj",
        ln=True,
        align="C",
    )

    out = pdf.output(dest="S")
    # fpdf2 returns bytearray; older fpdf returns str. Normalise to bytes.
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


@router.post("/export/pdf")
async def export_pdf(req: ExportPdfRequest) -> StreamingResponse:
    """Render the analysis result to a single-page PDF report."""
    pdf_bytes = _build_pdf(req)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=crj-analysis.pdf"
        },
    )
