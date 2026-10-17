"""Document analysis and the form-guide chat (the Gemma-powered core)."""
import asyncio
import datetime
import io
import json
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from PIL import Image, UnidentifiedImageError

from . import config, db, prompts, security, tools
from .gemini_client import extract_json
from .routes_auth import optional_user
from .schemas import AnalysisResult, ChatRequest, FormSheet, TextReply

router = APIRouter(prefix="/api", tags=["docs"])


def get_client(request: Request):
    return request.app.state.client


def _prepare_image(raw: bytes):
    """Downscale to MAX_IMAGE_SIDE on the longest side; return JPEG bytes."""
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    img.thumbnail((config.MAX_IMAGE_SIDE, config.MAX_IMAGE_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _days_left(deadlines):
    today = datetime.date.today()
    for d in deadlines:
        date_iso = d.get("date_iso") if isinstance(d, dict) else None
        if date_iso:
            try:
                d["days_left"] = (datetime.date.fromisoformat(str(date_iso)[:10]) - today).days
            except ValueError:
                d["days_left"] = None
        else:
            d["days_left"] = None
    return deadlines


def run_analysis(request: Request, jpeg: bytes, lang: str):
    """Call Gemma on prepared JPEG bytes; returns an AnalysisResult payload or raises HTTPException."""
    from google.genai import types

    client = get_client(request)
    contents = [
        types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
        prompts.analyze_prompt(config.LANG_NAMES[lang]),
    ]
    data, text, trace = client.generate_json(contents)
    if data is None:
        raise HTTPException(status_code=502, detail="The model returned something unreadable. Please try again.")
    if "error" in data and data["error"] == "unreadable":
        raise HTTPException(
            status_code=422,
            detail="We could not read this image as a document. Try a brighter, straight-on photo where the text is sharp.",
        )

    try:
        result = AnalysisResult(**data)
    except Exception:  # noqa: BLE001 - model missed the schema; retry once, stricter
        retry_contents = list(contents) + [
            "IMPORTANT: your previous reply did not match the required JSON shape. Reply again with ONLY one "
            "valid JSON object in exactly the required shape. Use \"not visible in the document\" for anything unclear."
        ]
        data, text, trace = client.generate_json(retry_contents)
        if data is None or "error" in data:
            raise HTTPException(status_code=502, detail="The model returned something unreadable. Please try again.")
        try:
            result = AnalysisResult(**data)
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=502, detail="The model returned an unreadable reading. Please try again.")

    payload = result.model_dump()
    payload["deadlines"] = _days_left(payload["deadlines"])
    payload["trace"] = trace
    return payload


@router.post("/analyze")
async def analyze(
    request: Request,
    image: UploadFile = File(...),
    lang: str = Form("en"),
    save: str = Form("0"),
    label: str = Form(""),
    user=Depends(optional_user),
):
    ip = security.client_ip(request)
    if not security.rate_limiter.allow("analyze", ip):
        raise HTTPException(status_code=429, detail="Too many requests just now. Please wait a minute and try again.")
    if lang not in config.SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail=f"lang must be one of {', '.join(config.SUPPORTED_LANGS)}")

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="No image received. Choose or photograph a document.")
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That file is over 8 MB. Use a smaller photo or scan.")

    try:
        jpeg = _prepare_image(raw)
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="That file could not be read as an image. Upload a JPG, PNG or WebP photo of the document.",
        )

    payload = await asyncio.to_thread(run_analysis, request, jpeg, lang)
    trace = payload.get("trace", {})
    db.log_usage(kind="analyze", doc_type=payload.get("document_type"), lang=lang,
                 model=trace.get("model"), key_slot=trace.get("key_slot"),
                 latency_ms=trace.get("latency_ms"), ok=True)

    payload["saved_scan_id"] = None
    if str(save).lower() in ("1", "true", "on") and user:
        import hashlib

        from . import store

        if store.count_scans(user["id"]) >= config.MAX_SCANS_PER_USER:
            raise HTTPException(
                status_code=409,
                detail=f"Your vault holds the maximum of {config.MAX_SCANS_PER_USER} scans. Delete one to save more.",
            )
        label_text = (label or payload.get("document_type") or "Scan").strip()[:120]
        meta = {
            "label": label_text,
            "doc_type": payload.get("document_type", ""),
            "summary": payload.get("summary", ""),
        }
        blob_enc = security.encrypt_for_user(user["id"], jpeg)
        label_enc = security.encrypt_for_user(user["id"], json.dumps(meta).encode("utf-8"))
        analysis_enc = security.encrypt_for_user(user["id"], json.dumps(payload).encode("utf-8"))
        scan_id = store.create_scan(
            user["id"],
            blob_enc,
            label_enc=label_enc,
            analysis_enc=analysis_enc,
            lang=lang,
            mime="image/jpeg",
            sha256=hashlib.sha256(jpeg).hexdigest(),
        )
        payload["saved_scan_id"] = scan_id

    return payload


@router.post("/chat")
async def chat(req: ChatRequest, request: Request, user=Depends(optional_user)):
    ip = security.client_ip(request)
    if not security.rate_limiter.allow("chat", ip):
        raise HTTPException(status_code=429, detail="Too many requests just now. Please wait a minute and try again.")

    client = get_client(request)
    forms = db.get_forms()
    schemes = db.get_schemes()
    centres = db.get_centres()
    lang_hint = ""
    if req.lang and req.lang in config.SUPPORTED_LANGS:
        lang_hint = f"\nThe user prefers answers in {config.LANG_NAMES[req.lang]}. Answer in that language."
    area_hint = ""
    if user and user.get("area"):
        area_hint = f"\nThe user's area is: {user['area']}. Use it when suggesting where to go."
    elif user:
        area_hint = ""
    contents = [prompts.CHAT_SYSTEM, "USER: " + req.message + lang_hint + area_hint]
    trace_tool_calls = []
    last_trace = None
    total_latency = 0
    started = time.monotonic()

    for _round in range(4):
        if _round and time.monotonic() - started > 45:
            break
        remaining = 45 - (time.monotonic() - started)
        try:
            text, trace = await asyncio.wait_for(
                asyncio.to_thread(client.call, contents), timeout=max(6, remaining)
            )
        except asyncio.TimeoutError:
            payload = {
                "type": "text",
                "text": "The AI service is briefly overloaded. Please try again in a minute.",
                "trace": {**(last_trace or {}), "latency_ms": total_latency, "tool_calls": trace_tool_calls},
            }
            db.log_usage(kind="chat", lang=req.lang, model=(last_trace or {}).get("model"),
                         key_slot=(last_trace or {}).get("key_slot"),
                         latency_ms=total_latency, ok=False)
            return payload
        last_trace = trace
        total_latency += trace.get("latency_ms", 0)
        data = extract_json(text)

        if data is None:
            # The model answered in prose; surface it as a text reply rather than failing.
            if text.strip():
                payload = {"type": "text", "text": text.strip()}
            else:
                payload = {"type": "text", "text": "I could not process that. Please ask again."}
            payload["trace"] = {**last_trace, "latency_ms": total_latency, "tool_calls": trace_tool_calls}
            db.log_usage(kind="chat", lang=req.lang, model=last_trace.get("model"),
                         key_slot=last_trace.get("key_slot"), latency_ms=total_latency, ok=True)
            return payload

        if data.get("action") == "tool_call":
            name = str(data.get("tool", ""))
            result = tools.execute_tool(name, data.get("args", {}), forms, schemes, centres)
            trace_tool_calls.append({"tool": name, "args": data.get("args", {})})
            contents = contents + [
                text,
                tools.tool_result_text(name, result)[:6000],
                "Use the tool result above. Reply with the next JSON object: another tool call, or the final "
                "form_sheet / text answer.",
            ]
            continue

        # Final answer
        if data.get("type") == "form_sheet":
            try:
                sheet = FormSheet(**data)
                payload = sheet.model_dump()
            except Exception:  # noqa: BLE001
                payload = {"type": "text", "text": json.dumps(data, ensure_ascii=False)}
        elif data.get("type") == "text":
            payload = TextReply(text=str(data.get("text", ""))).model_dump()
        else:
            payload = {"type": "text", "text": json.dumps(data, ensure_ascii=False)}

        payload["trace"] = {**last_trace, "latency_ms": total_latency, "tool_calls": trace_tool_calls}
        db.log_usage(kind="chat", lang=req.lang, model=last_trace.get("model"),
                     key_slot=last_trace.get("key_slot"), latency_ms=total_latency, ok=True)
        return payload

    payload = {
        "type": "text",
        "text": "I could not finish that answer. Please rephrase the question and try again.",
        "trace": {**(last_trace or {}), "latency_ms": total_latency, "tool_calls": trace_tool_calls},
    }
    return payload
