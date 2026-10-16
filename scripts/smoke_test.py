"""Real-API smoke test for Gemma 4 through the Gemini API.

Run first: python scripts/smoke_test.py
Tests both configured models for: plain text, image input, JSON output,
instruction following, and the prompt-based tool protocol.

Exits 1 with a clear message when no key is configured.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app import config  # noqa: E402
from app.gemini_client import extract_json  # noqa: E402


def make_test_image():
    """A tiny synthetic 'electricity bill' so we can check real image reading."""
    img = Image.new("RGB", (640, 400), "#F3EEE3")
    d = ImageDraw.Draw(img)
    d.text((30, 30), "MSEDCL  ELECTRICITY BILL", fill="#1C1A17")
    d.text((30, 90), "Consumer No: 1234567890", fill="#1C1A17")
    d.text((30, 130), "Bill Amount Due: Rs 1,240", fill="#1C1A17")
    d.text((30, 170), "Due Date: 2026-11-05", fill="#B8371F")
    d.text((30, 210), "Billing Period: Sep 2026", fill="#1C1A17")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run_model(client, model):
    print(f"\n=== {model} ===")
    notes = {}

    def attempt(label, fn):
        try:
            ok, detail = fn()
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {detail}")
            notes[label] = {"ok": ok, "detail": detail}
        except Exception as exc:  # noqa: BLE001
            print(f"  [FAIL] {label}: {type(exc).__name__}: {str(exc)[:200]}")
            notes[label] = {"ok": False, "detail": f"{type(exc).__name__}: {str(exc)[:200]}"}

    def t_text():
        r = client.models.generate_content(model=model, contents="Reply with exactly: pong")
        return ("pong" in (r.text or "").lower(), (r.text or "")[:80])

    def t_image():
        r = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=make_test_image(), mime_type="image/png"),
                "What amount is due on this bill, and what is the due date? One line.",
            ],
        )
        text = r.text or ""
        return ("1240" in text.replace(",", ""), text[:120])

    def t_json():
        r = client.models.generate_content(
            model=model,
            contents='Return ONLY a JSON object: {"ok": true, "n": 2}. No other text.',
        )
        data = extract_json(r.text or "")
        return (data is not None and data.get("n") == 2, json.dumps(data))

    def t_instructions():
        system = "Always answer in exactly one word. Never explain."
        r = client.models.generate_content(
            model=model,
            contents=f"[INSTRUCTIONS]\n{system}\n\nWhat is the capital of France? One word.",
        )
        text = (r.text or "").strip()
        return ("paris" in text.lower(), text[:80])

    def t_tool_protocol():
        contents = [
            "You are a tool-using helper. Tools: get_weather(args:{city}). "
            "Reply ONLY with JSON. To call a tool: "
            '{"action":"tool_call","tool":"get_weather","args":{"city":"..."}}. '
            "Now: what is the weather in Pune?",
        ]
        r = client.models.generate_content(model=model, contents=contents)
        data = extract_json(r.text or "")
        ok = data is not None and data.get("action") == "tool_call" and data.get("tool") == "get_weather"
        return (ok, json.dumps(data)[:200])

    attempt("plain text", t_text)
    attempt("image input", t_image)
    attempt("json output", t_json)
    attempt("instructions in user turn", t_instructions)
    attempt("tool protocol", t_tool_protocol)
    return notes


def main():
    if not config.GEMINI_API_KEYS:
        print(
            "NO API KEY FOUND.\n"
            "Paste one or more Gemini API keys into .env at the project root:\n"
            '  GEMINI_API_KEYS=key1,key2\n'
            "Get free keys at https://aistudio.google.com"
        )
        sys.exit(1)

    client = genai.Client(
        api_key=config.GEMINI_API_KEYS[0],
        http_options=types.HttpOptions(timeout=120 * 1000),
    )
    all_notes = {}
    for model in [config.GEMMA_MODEL, config.GEMMA_FALLBACK_MODEL]:
        all_notes[model] = run_model(client, model)

    print("\n=== Summary ===")
    for model, notes in all_notes.items():
        failed = [k for k, v in notes.items() if not v["ok"]]
        if failed:
            print(f"{model}: FAIL on {', '.join(failed)}")
        else:
            print(f"{model}: all checks passed")


if __name__ == "__main__":
    main()
