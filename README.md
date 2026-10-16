# Samajh (समझ)

Samajh helps ordinary people in India deal with confusing paperwork. Upload or
photograph a document (a bank or loan notice, electricity bill, rent agreement,
insurance letter, college circular, government letter) and it explains the
document in plain language, in English, Hindi or Marathi. Or ask about a
government form ("I need a passport") and it answers with the documents needed,
the steps in order, whether it can be done from home, and the official link.

**Built with Google's Gemma 4 (`gemma-4-31b-it`) through the Gemini API.**
Remove Gemma and nothing works: every answer on the site comes from the model.

There is no login, no accounts, no storage. Uploaded images are processed in
memory and never saved anywhere.

## How Gemma is used

- **Vision**: `/api/analyze` sends the document image (downscaled to at most
  1600 px with Pillow) to `gemma-4-31b-it`, which reads it and returns a
  structured explanation validated by pydantic: document type, summary,
  key facts, amounts, deadlines (with days left computed server-side),
  numbered actions, red flags, and two honest verdicts (can this be ignored,
  do you need a professional).
- **Structured output**: JSON is enforced by prompt (the schema is spelled out
  in the user turn), parsed defensively (thinking blocks and code fences are
  stripped), and re-requested once when the first reply does not parse.
- **Function calling**: the form guide runs a manual tool loop. Gemma is given
  three tools (`list_supported_forms`, `get_form_requirements`, `days_until`);
  when it wants one, the backend executes it against the verified knowledge
  base and feeds the result back until Gemma writes the final form sheet.
  Gemma on the Gemini API does not expose a native function-calling mode, so
  the loop is prompt-protocol based and enforced server-side.

## Multi-key failover

`GEMINI_API_KEYS` holds comma-separated keys. A thread-safe `KeyPool` in
`app/gemini_client.py` rotates them on every request:

- HTTP 429 / quota errors: the key is cooled down for 60 seconds and the next
  key is used.
- 400/401/403 invalid-key errors: the key is disabled for the rest of the
  session.
- 5xx and timeouts: one retry on the same key, then rotate.
- If every key is exhausted on `gemma-4-31b-it`, the whole key list is retried
  on the fallback model `gemma-4-26b-a4b-it`.
- If everything fails, the user gets a friendly error with a retry hint, never
  a stack trace.

Logs and responses only ever show the key slot number and last 4 characters.
`GET /api/health` reports active and disabled key counts and both model names.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your Gemini API keys into GEMINI_API_KEYS
uvicorn app.main:app --reload # http://localhost:8000
```

Optional Supabase (the app works fine without it):

```bash
# in the Supabase SQL editor: run supabase/schema.sql
python scripts/seed_forms.py  # loads data/forms.json into the forms table
```

With Supabase configured, forms are read from the `forms` table (cached five
minutes) and one `usage_log` row is written per request (kind, doc type,
language, model, key slot, latency, ok). No images, extracted text, or
personal data is ever stored. Without Supabase the app silently falls back to
`data/forms.json` and skips logging.

## Model notes (from scripts/smoke_test.py, run 2026-10-17)

- `gemma-4-31b-it` reads images well (a synthetic bill's amount and due date
  were read correctly), produces parseable JSON from a prompt, follows
  instructions placed in the user turn, and works with the prompt-based tool
  protocol.
- There is no separate system role and no schema-enforced JSON mode for Gemma
  on the Gemini API, so instructions are prepended to the user turn and JSON
  is enforced by prompt with a parse-and-retry step.
- Responses are slow (tens of seconds) and the endpoint intermittently returns
  500/503 "high demand" errors. The key pool absorbs these: same-key retry,
  rotation, and a final pass on the fallback model. During the smoke run the
  fallback model `gemma-4-26b-a4b-it` also returned 500s on several checks but
  succeeded on later live calls; expect flakiness and design for it.
- `scripts/smoke_test.py` tests both configured models for plain text, image
  input, JSON output, instruction following and the tool protocol, and exits
  with a clear message when no key is configured.

## Privacy

Images are processed in memory and never stored: no file system writes, no
database rows, no logs. A production version could self-host the open-weight
Gemma model so documents never leave the deployer's own machine.

## Known limits

- The five knowledge-base entries were written conservatively and each is
  marked `needs_verification: true`; fees are never stated. Verify every entry
  against the official portal before relying on it in a demo.
- The free Gemma endpoints are rate-limited and occasionally error; with one
  key the failover ladder has little to rotate through. Add more free keys
  from https://aistudio.google.com for a smoother demo.
- Long or very low-resolution documents read worse than clear photos.
- Answers explain documents; they are not legal or financial advice.

## What you must do by hand

1. Paste your API keys into `.env` (`GEMINI_API_KEYS=key1,key2`).
2. To use Supabase: run `supabase/schema.sql` in the Supabase SQL editor, then
   `python scripts/seed_forms.py`.
3. Verify every entry in `data/forms.json` against the official portal.
4. Test Marathi output on a real document photo before the demo.

Built with AI-assisted coding (OpenCode).
