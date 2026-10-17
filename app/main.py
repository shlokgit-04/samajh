"""Samajh: read a document, ask about a form. FastAPI backend."""
import datetime
import io
import json
import os
import time

import asyncio

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from . import config, db, prompts, tools
from .gemini_client import GemmaClient, PoolExhausted, extract_json
from .schemas import AnalysisResult, ChatRequest, FormSheet, TextReply

app = FastAPI(title="Samajh", docs_url=None, redoc_url=None)
client = GemmaClient()

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@app.exception_handler(PoolExhausted)
async def pool_exhausted_handler(request, exc):
    return JSONResponse(status_code=503, content={"error": str(exc)})


@app.exception_handler(Exception)
async def unhandled_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong on our side. Please try again."},
    )


@app.get("/api/health")
async def health():
    snap = client.pool.snapshot()
    return {
        "ok": snap["total"] > 0,
        "keys": snap,
        "model": config.GEMMA_MODEL,
        "fallback_model": config.GEMMA_FALLBACK_MODEL,
        "db": "supabase" if (config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY) else "local file",
    }


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


@app.post("/api/analyze")
async def analyze(image: UploadFile = File(...), lang: str = Form("en")):
    if lang not in config.SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="lang must be one of en, hi, mr")

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="No image received. Choose or photograph a document.")
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That file is over 8 MB. Use a smaller photo or scan.")

    try:
        jpeg = _prepare_image(raw)
    except Exception:  # noqa: BLE001 - not a decodable image
        raise HTTPException(
            status_code=400,
            detail="That file could not be read as an image. Upload a JPG, PNG or WebP photo of the document.",
        )

    from google.genai import types

    contents = [
        types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
        prompts.analyze_prompt(config.LANG_NAMES[lang]),
    ]
    data, text, trace = await asyncio.to_thread(client.generate_json, contents)
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
    db.log_usage(kind="analyze", doc_type=result.document_type, lang=lang,
                 model=trace.get("model"), key_slot=trace.get("key_slot"),
                 latency_ms=trace.get("latency_ms"), ok=True)
    return payload


@app.post("/api/chat")
async def chat(req: ChatRequest):
    forms = db.get_forms()
    contents = [prompts.CHAT_SYSTEM, "USER: " + req.message]
    trace_tool_calls = []
    last_trace = None
    total_latency = 0
    started = time.monotonic()

    for _round in range(4):
        if _round and time.monotonic() - started > 70:
            break
        text, trace = await asyncio.to_thread(client.call, contents)
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
            db.log_usage(kind="chat", lang=None, model=last_trace.get("model"),
                         key_slot=last_trace.get("key_slot"), latency_ms=total_latency, ok=True)
            return payload

        if data.get("action") == "tool_call":
            name = str(data.get("tool", ""))
            result = tools.execute_tool(name, data.get("args", {}), forms)
            trace_tool_calls.append({"tool": name, "args": data.get("args", {})})
            contents = contents + [
                text,
                tools.tool_result_text(name, result)[:4000],
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
        db.log_usage(kind="chat", lang=None, model=last_trace.get("model"),
                     key_slot=last_trace.get("key_slot"), latency_ms=total_latency, ok=True)
        return payload

    payload = {
        "type": "text",
        "text": "I could not finish that answer. Please rephrase the question and try again.",
        "trace": {**(last_trace or {}), "latency_ms": total_latency, "tool_calls": trace_tool_calls},
    }
    return payload


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
