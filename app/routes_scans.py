"""Encrypted scan vault: store, list, re-read, download and delete personal scans.

Every scan is encrypted at rest with a per-user key (security.py). The plain
image never touches the disk: it is decrypted in memory only for the owner.
"""
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from . import config, security, store
from .routes_auth import get_current_user
from .routes_docs import _prepare_image, run_analysis

router = APIRouter(prefix="/api/scans", tags=["scans"])


def _meta(user_id, row):
    """Decrypt the non-sensitive listing fields for the owner."""
    label = {"label": f"Scan #{row['id']}", "doc_type": "", "summary": ""}
    raw = security.safe_decrypt(user_id, row.get("label_enc") or b"")
    if raw:
        try:
            label.update(json.loads(raw))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    analysis = None
    raw_a = security.safe_decrypt(user_id, row.get("analysis_enc") or b"")
    if raw_a:
        try:
            analysis = json.loads(raw_a)
        except (json.JSONDecodeError, UnicodeDecodeError):
            analysis = None
    return {
        "id": row["id"],
        "label": label.get("label", ""),
        "doc_type": label.get("doc_type", ""),
        "summary": label.get("summary", ""),
        "lang": row.get("lang", "en"),
        "size": row.get("size", 0),
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
        "has_analysis": analysis is not None,
    }


@router.get("")
async def list_scans(request: Request, user=Depends(get_current_user)):
    removed = store.cleanup_expired_scans()
    rows = store.list_scans(user["id"])
    return {
        "scans": [_meta(user["id"], r) for r in rows],
        "removed_expired": removed,
        "retention_days": config.SCAN_RETENTION_DAYS,
        "max_scans": config.MAX_SCANS_PER_USER,
    }


@router.post("")
async def upload_scan(
    request: Request,
    image: UploadFile = File(...),
    label: str = Form(""),
    lang: str = Form("en"),
    user=Depends(get_current_user),
):
    ip = security.client_ip(request)
    if not security.rate_limiter.allow("analyze", ip):
        raise HTTPException(status_code=429, detail="Too many uploads just now. Please wait a minute and try again.")
    if store.count_scans(user["id"]) >= config.MAX_SCANS_PER_USER:
        raise HTTPException(
            status_code=409,
            detail=f"Your vault holds the maximum of {config.MAX_SCANS_PER_USER} scans. Delete one to save more.",
        )
    if lang not in config.SUPPORTED_LANGS:
        lang = "en"
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="No image received.")
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That file is over 8 MB. Use a smaller photo or scan.")
    from PIL import UnidentifiedImageError

    try:
        jpeg = _prepare_image(raw)
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="That file could not be read as an image. Upload a JPG, PNG or WebP photo of the document.",
        )
    import hashlib

    meta = {"label": (label or image.filename or "Scan")[:120], "doc_type": "", "summary": ""}
    scan_id = store.create_scan(
        user["id"],
        security.encrypt_for_user(user["id"], jpeg),
        label_enc=security.encrypt_for_user(user["id"], json.dumps(meta).encode("utf-8")),
        lang=lang,
        mime="image/jpeg",
        sha256=hashlib.sha256(jpeg).hexdigest(),
    )
    store.log_security(user["email"], "scan_saved", ip)
    return {"ok": True, "scan": _meta(user["id"], store.get_scan(user["id"], scan_id))}


@router.get("/{scan_id}")
async def get_scan(scan_id: int, user=Depends(get_current_user)):
    row = store.get_scan(user["id"], scan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scan not found in your vault.")
    out = _meta(user["id"], row)
    raw_a = security.safe_decrypt(user["id"], row.get("analysis_enc") or b"")
    out["analysis"] = json.loads(raw_a) if raw_a else None
    return out


@router.get("/{scan_id}/image")
async def get_scan_image(scan_id: int, user=Depends(get_current_user)):
    row = store.get_scan(user["id"], scan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scan not found in your vault.")
    blob = security.safe_decrypt(user["id"], row["blob_enc"])
    if blob is None:
        raise HTTPException(status_code=500, detail="Stored scan could not be decrypted.")
    return Response(
        content=blob,
        media_type=row.get("mime") or "image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{scan_id}/download")
async def download_scan(scan_id: int, user=Depends(get_current_user)):
    row = store.get_scan(user["id"], scan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scan not found in your vault.")
    blob = security.safe_decrypt(user["id"], row["blob_enc"])
    if blob is None:
        raise HTTPException(status_code=500, detail="Stored scan could not be decrypted.")
    return Response(
        content=blob,
        media_type=row.get("mime") or "image/jpeg",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="samajh-scan-{scan_id}.jpg"',
        },
    )


@router.post("/{scan_id}/analyze")
async def analyze_stored(scan_id: int, request: Request, lang: str = Form("en"), user=Depends(get_current_user)):
    ip = security.client_ip(request)
    if not security.rate_limiter.allow("analyze", ip):
        raise HTTPException(status_code=429, detail="Too many requests just now. Please wait a minute and try again.")
    if lang not in config.SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail=f"lang must be one of {', '.join(config.SUPPORTED_LANGS)}")
    row = store.get_scan(user["id"], scan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scan not found in your vault.")
    blob = security.safe_decrypt(user["id"], row["blob_enc"])
    if blob is None:
        raise HTTPException(status_code=500, detail="Stored scan could not be decrypted.")

    import asyncio

    payload = await asyncio.to_thread(run_analysis, request, blob, lang)
    store.update_scan_analysis(
        user["id"], scan_id,
        security.encrypt_for_user(user["id"], json.dumps(payload).encode("utf-8")),
        lang=lang,
    )
    meta = {
        "label": _meta(user["id"], row)["label"],
        "doc_type": payload.get("document_type", ""),
        "summary": payload.get("summary", ""),
    }
    store.update_scan_label(
        user["id"], scan_id,
        security.encrypt_for_user(user["id"], json.dumps(meta).encode("utf-8")),
    )
    return payload


@router.delete("/{scan_id}")
async def delete_scan(scan_id: int, request: Request, user=Depends(get_current_user)):
    if not store.delete_scan(user["id"], scan_id):
        raise HTTPException(status_code=404, detail="Scan not found in your vault.")
    store.log_security(user["email"], "scan_deleted", security.client_ip(request))
    return {"ok": True}


@router.delete("")
async def delete_all(request: Request, user=Depends(get_current_user)):
    n = store.delete_all_scans(user["id"])
    store.log_security(user["email"], "all_scans_deleted", security.client_ip(request))
    return {"ok": True, "deleted": n}
