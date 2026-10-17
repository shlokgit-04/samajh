"""Per-profile recommendations (farmer / government employee / doctor / ...) and
the area centre directory ("where do I have to go to get this done?").

Recommendations are served from the verified knowledge base (schemes.json).
The user's occupation and area come from their profile, so the same endpoint
answers differently for a farmer and a doctor.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from . import config, db, security, tools
from .routes_auth import get_current_user

router = APIRouter(prefix="/api", tags=["recommendations"])

SERVICE_LABELS = {
    "aadhaar": "Aadhaar seva kendra",
    "passport": "Passport Seva Kendra",
    "rto": "RTO / Parivahan office",
    "csc": "Common Service Centre (CSC)",
    "tehsil": "Tehsil / block office",
    "bank": "Bank branch",
    "post": "Post office",
    "hospital": "Government hospital / PHC",
    "agriculture": "Agriculture office / KVK",
    "municipal": "Municipal / nagar palika office",
    "court": "Court / registrar office",
    "electricity": "Electricity board office",
}


def _public_scheme(scheme):
    return {
        "id": scheme.get("id"),
        "name": scheme.get("name"),
        "profiles": scheme.get("profiles", []),
        "summary": scheme.get("summary", ""),
        "benefits": scheme.get("benefits", []),
        "eligibility": scheme.get("eligibility", []),
        "extra_costs": scheme.get("extra_costs", []),
        "where_to_go": scheme.get("where_to_go", {}),
        "forms": scheme.get("forms", []),
        "steps": scheme.get("steps", []),
        "documents": scheme.get("documents", []),
        "warnings": scheme.get("warnings", []),
        "official_url": scheme.get("official_url", ""),
        "needs_verification": scheme.get("needs_verification", True),
    }


@router.get("/recommendations")
async def recommendations(request: Request, role: str = Query(default=""), user=Depends(get_current_user)):
    """Schemes and next steps for the signed-in user's occupation (or ?role=)."""
    role = (role or user.get("role") or "citizen").strip()
    if role not in config.SUPPORTED_ROLES:
        role = "citizen"
    schemes = db.get_schemes()
    mine = [s for s in schemes if role in s.get("profiles", [])]
    general = [s for s in schemes if role not in s.get("profiles", []) and "citizen" in s.get("profiles", [])]
    forms = {f["id"]: f["name"] for f in db.get_forms()}

    def with_form_names(items):
        out = []
        for s in items:
            pub = _public_scheme(s)
            pub["form_names"] = [forms.get(fid, fid) for fid in pub["forms"]]
            out.append(pub)
        return out

    return {
        "role": role,
        "role_name": config.ROLE_NAMES.get(role, role),
        "area": user.get("area", ""),
        "for_you": with_form_names(mine),
        "also_useful": with_form_names(general),
        "role_options": [{"id": r, "name": config.ROLE_NAMES[r]} for r in config.SUPPORTED_ROLES],
    }


@router.get("/forms")
async def list_forms():
    """The verified form list, for suggestions and the tracker dropdown."""
    return {
        "forms": [
            {
                "id": f["id"],
                "name": f["name"],
                "mode": f.get("mode", "partly_home"),
                "where_to_go": (f.get("where_to_go") or {}).get("office", "")
                if isinstance(f.get("where_to_go"), dict) else "",
                "processing_time": f.get("processing_time", ""),
            }
            for f in db.get_forms()
        ]
    }


@router.get("/schemes")
async def list_schemes():
    return {
        "schemes": [
            {"id": s["id"], "name": s["name"], "profiles": s.get("profiles", []), "summary": s.get("summary", "")}
            for s in db.get_schemes()
        ]
    }


@router.get("/schemes/{scheme_id}")
async def get_scheme(scheme_id: str):
    scheme = db.find_scheme(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="That scheme is not in the verified knowledge base.")
    pub = _public_scheme(scheme)
    pub["profile_names"] = [config.ROLE_NAMES.get(p, p) for p in pub["profiles"]]
    return pub


@router.get("/centres")
async def centres(
    request: Request,
    service: str = Query(default="", max_length=60),
    area: str = Query(default="", max_length=100),
    limit: int = Query(default=30, ge=1, le=100),
):
    """Office/centre directory filtered by service and area keywords."""
    if not security.rate_limiter.allow("chat", security.client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests just now. Please wait a minute.")
    all_centres = db.get_centres()
    found = tools.find_centres(all_centres, service=service, area=area)
    if limit < len(found):
        found = found[:limit]
    return {
        "centres": found,
        "count": len(found),
        "services": [{"id": k, "name": v} for k, v in SERVICE_LABELS.items()],
    }


@router.get("/centres/services")
async def centre_services():
    return {"services": [{"id": k, "name": v} for k, v in SERVICE_LABELS.items()]}
