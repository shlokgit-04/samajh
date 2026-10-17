"""PDF downloads: form checklists, scheme summaries and custom checklists."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from . import config, db, pdf, security
from .routes_auth import optional_user
from .schemas import ChecklistPdfRequest

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

FILENAME_SAFE = str.maketrans({" ": "-", "/": "-", "\\": "-"})


def _pdf_response(data, filename):
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _form_sections(form, lang):
    """Turn one knowledge-base form entry into printable checklist sections."""
    mandatory = form.get("compulsory_documents") or form.get("documents") or []
    optional = form.get("optional_documents") or []
    extra = form.get("extra_documents") or []
    sections = [
        {"heading": "Compulsory documents", "items": mandatory},
    ]
    if optional or extra:
        sections.append({"heading": "Optional / extra documents", "items": list(optional) + list(extra)})
    costs = form.get("costs") or []
    if costs:
        sections.append({
            "heading": "Costs involved",
            "items": [f"{c.get('label', '')}: {c.get('value', '')}".strip(": ") for c in costs],
        })
    steps = form.get("steps") or []
    if steps:
        sections.append({"heading": "Steps in order", "items": [f"{i + 1}. {s}" for i, s in enumerate(steps)]})
    warnings = form.get("warnings") or []
    if warnings:
        sections.append({"heading": "Warnings", "items": warnings})
    if form.get("processing_time") or form.get("mode_reason"):
        sections.append({
            "heading": "Good to know",
            "items": [x for x in [form.get("processing_time", ""), form.get("mode_reason", "")] if x],
        })
    return sections


@router.get("/form/{form_id}")
async def form_checklist(form_id: str, lang: str = "en", user=Depends(optional_user)):
    if lang not in config.SUPPORTED_LANGS:
        lang = "en"
    form = db.find_form(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="That form is not in the verified knowledge base.")
    where = form.get("where_to_go") or {}
    subtitle = ""
    if isinstance(where, dict) and where.get("office"):
        subtitle = f"Where to go: {where['office']}"
        if where.get("note"):
            subtitle += f" — {where['note']}"
    data = pdf.build_checklist_pdf(
        title=form.get("name", form_id),
        subtitle=subtitle,
        sections=_form_sections(form, lang),
        lang=lang,
        notes=" ".join(filter(None, [form.get("fee_note", ""), form.get("extra_info", "")])),
        official_url=form.get("official_url", ""),
    )
    name = form_id.translate(FILENAME_SAFE)
    return _pdf_response(data, f"samajh-{name}-checklist.pdf")


@router.get("/scheme/{scheme_id}")
async def scheme_pdf(scheme_id: str, lang: str = "en", user=Depends(optional_user)):
    if lang not in config.SUPPORTED_LANGS:
        lang = "en"
    scheme = db.find_scheme(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="That scheme is not in the verified knowledge base.")
    where = scheme.get("where_to_go") or {}
    subtitle = where.get("office", "") if isinstance(where, dict) else ""
    sections = [
        {"heading": "What you get", "items": scheme.get("benefits", [])},
        {"heading": "Who can apply", "items": scheme.get("eligibility", [])},
        {"heading": "Documents to keep ready", "items": scheme.get("documents", [])},
        {"heading": "Extra costs to plan for", "items": scheme.get("extra_costs", [])},
        {"heading": "Forms to fill", "items": scheme.get("forms", [])},
        {"heading": "Steps in order", "items": [f"{i + 1}. {s}" for i, s in enumerate(scheme.get("steps", []))]},
        {"heading": "Warnings", "items": scheme.get("warnings", [])},
    ]
    sections = [s for s in sections if s["items"]]
    data = pdf.build_checklist_pdf(
        title=scheme.get("name", scheme_id),
        subtitle=(scheme.get("summary", "") + (f" | Where to go: {where}" if isinstance(where, str) else "")),
        sections=sections,
        lang=lang,
        notes="Verify eligibility and current benefits on the official portal.",
        official_url=scheme.get("official_url", ""),
    )
    name = scheme_id.translate(FILENAME_SAFE)
    return _pdf_response(data, f"samajh-{name}.pdf")


@router.post("/checklist")
async def custom_checklist(req: ChecklistPdfRequest, request: Request, user=Depends(optional_user)):
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    if not security.rate_limiter.allow("pdf", security.client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many downloads just now. Please wait a minute.")
    lang = req.lang if req.lang in config.SUPPORTED_LANGS else "en"
    data = pdf.build_checklist_pdf(
        title=req.title,
        subtitle=req.subtitle,
        sections=[s.model_dump() for s in req.sections],
        lang=lang,
        notes=req.notes,
    )
    return _pdf_response(data, "samajh-checklist.pdf")
