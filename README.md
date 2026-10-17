# Samajh (समझ)

Samajh helps ordinary people in India deal with confusing paperwork — and keeps
the process moving. Upload a document (bank or loan notice, electricity bill,
insurance letter, rent agreement, college circular, government letter) and it
explains it in plain language in any of ten languages. Ask about a government
form, scheme or office and it answers from a verified knowledge base with the
compulsory documents, optional and extra documents, costs, where to go,
processing time, warnings and step-by-step guidance. Track your applications so
the "trusted process" of Indian paperwork is no longer a black box, and get
scheme recommendations tailored to who you are: farmer, government employee,
doctor, student, senior citizen, worker or business owner.

**Built with Google's Gemma 4 (`gemma-4-31b-it`) through the Gemini API.**
Remove Gemma and the reading/chat features stop working; everything else
(accounts, vault, tracker, recommendations, centres, PDFs) runs on its own.

## What is in the box

### Read a document (Gemma 4 vision)
- Upload or photograph a document; Gemma 4 reads it and returns a structured
  explanation validated by pydantic: document type, summary, explanation, key
  facts, amounts, deadlines (days-left computed server-side), numbered actions,
  red flags (scams, OTP requests, threats), two honest verdicts, and confidence.
- **Text to speech** on every answer, in the answer's language, using the
  device voices (Web Speech API). A "read aloud automatically" comfort option.
- **Downloadable PDF** of the reading: actions, deadlines, warnings — printable
  checklist with real checkboxes.
- **Encrypted scan vault**: signed-in users can keep scans; each document is
  encrypted at rest (Fernet with a per-user HKDF-derived key) and auto-deleted
  after 30 days (configurable). Re-read a stored scan in another language,
  download it, or delete it forever with one click.

### Forms & guide (Gemma 4 tool calling)
- A verified knowledge base (`data/forms.json`, 13+ forms: PAN, Aadhaar, voter
  ID, passport, learner's licence, driving licence renewal, ration card, income
  certificate, birth certificate, PM-KISAN, e-Shram, Ayushman card, DigiLocker).
- Every entry separates **compulsory documents** from **optional/extra
  documents**, lists **costs** (including hidden ones like CSC service fees,
  stamp paper, travel), **where to go** (online only / partly / in person, and
  which office), **processing time** and **warnings**.
- The model can only relay what the tools return: it never invents fees,
  documents or URLs.
- One-click **checklist PDF** per form, in your language.

### My paperwork — the process tracker
- Track every application as a small state machine (started → documents
  gathered → submitted → under review → action needed → approved/rejected →
  completed) with a timeline of events, reference numbers, office, target date
  and notes.
- **Alerts and warnings**: overdue targets, approaching deadlines, deadlines
  and red flags found inside your stored scans, plus your own reminders. A bell
  in the header shows what needs attention.

### For you — per-profile recommendations
- Schemes matched to the signed-in user's occupation: farmer (PM-KISAN, PMFBY,
  KCC), government employee (CGHS, UPS/NPS), doctor (NMC registration, PM-JAY
  empanelment), student (NSP scholarships, Vidya Lakshmi), senior citizen
  (old-age pension, CGHS), worker (e-Shram, PM SVANidhi), entrepreneur (Udyam,
  PMEGP), plus universal ones (PM-JAY, DigiLocker).
- Each scheme lists benefits, eligibility, extra costs to plan for, where to
  go, which forms to fill (linked to the form guide) and warnings. PDF per
  scheme.

### Find a centre — "where do I have to go?"
- An office directory (`data/centres.json`) of Passport Seva Kendras, Aadhaar
  centres, RTOs, CSCs, tehsil offices, municipal ward offices, agriculture
  offices, hospitals and more, searchable by service and area, with an
  "Open in Maps" link. Sample data: verify on official portals.

## Accounts, privacy and security

- **Authenticate & authorise**: register/login with bcrypt-hashed passwords and
  JWT sessions in httpOnly, SameSite=Strict cookies. Admin emails (env) get
  admin rights; users can only ever see their own data.
- **Encrypted vault**: scans and their readings are encrypted at rest with a
  per-user key derived from the app secret (HKDF-SHA256 → Fernet). A database
  dump without the secret shows ciphertext only.
- **Data rights**: one-click JSON export (right of access) and full account
  deletion that erases every scan, application and alert (right to erasure).
  Passwords are never stored or logged; the security log records only
  email + action + IP for sign-in events.
- **Privacy by default**: document images are processed in memory; nothing is
  stored unless the user explicitly saves it. Retention auto-deletes old scans.
- **Hardening**: rate limiting on auth/analyze/chat/PDF, origin checks on
  mutating requests, security headers (CSP, X-Frame-Options, no-store on APIs),
  upload size/type limits, and defensive prompts that treat document text as
  data, never instructions.

## Multilingual

Answer language for ten languages: English, Hindi, Marathi, Tamil, Telugu,
Bengali, Gujarati, Kannada, Malayalam, Punjabi (UI chrome in EN/HI/MR with
English fallback; content everywhere). Text-to-speech voices follow the chosen
language; PDFs render the correct Noto script font (Devanagari, Tamil, Telugu,
Bengali, Gujarati, Kannada, Malayalam, Gurmukhi).

## Comfort features

- Text size slider, high-contrast mode, easy-reading spacing, read-aloud
  on/off — all remembered on the device.
- Keyboard-accessible tabs and dialogs, skip link, aria-live regions.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # paste real Gemini API keys into GEMINI_API_KEYS
uvicorn app.main:app --reload # http://localhost:8000
```

Everything except document reading and the chat works with no API keys: the
app starts, accounts work, vault/tracker/recommendations/centres/PDFs work; the
model-backed endpoints answer with a friendly 503 explaining the key is missing.

Optional Supabase (the app works fine without it):

```bash
# in the Supabase SQL editor: run supabase/schema.sql
python scripts/seed_forms.py  # loads data/forms.json into the forms table
```

With Supabase configured, forms are read from the `forms` table (cached five
minutes) and one `usage_log` row is written per model request (kind, doc type,
language, model, key slot, latency, ok). No images, extracted text, or personal
data is ever stored there.

Run the tests:

```bash
.venv/bin/python -m pytest tests/ -q
```

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
`GET /api/health` reports active and disabled key counts, both model names,
supported languages and roles.

## Project layout

```
app/
  main.py           app factory: security headers, handlers, routers, static mount
  config.py         env config: langs, roles, retention, rate limits
  security.py       bcrypt, JWT sessions, per-user Fernet vault, rate limiter
  store.py          SQLite: users, encrypted scans, applications, events, alerts
  gemini_client.py  Gemma 4 client with multi-key/fallback-model failover
  routes_auth.py    register/login/logout/me/password/export/delete
  routes_docs.py    /api/analyze (vision) and /api/chat (tool loop)
  routes_scans.py   encrypted scan vault CRUD + re-analysis
  routes_tracker.py applications, events, alerts and warnings
  routes_reco.py    recommendations, schemes, centres, forms directory
  routes_pdf.py     checklist/scheme/reading PDF downloads
  pdf.py            fpdf2 rendering with Noto script fonts
  prompts.py        analyze + chat system prompts and tool protocol
  tools.py          list/get forms, schemes, centres, days-until
  schemas.py        pydantic request/response models
data/
  forms.json        verified form knowledge base (compulsory/optional/costs/warnings)
  schemes.json      per-profile schemes (farmer, govt employee, doctor, ...)
  centres.json      office directory for "where do I have to go?"
static/             the front-end (vanilla JS, CSP-safe, no framework)
tests/              pytest suite (auth, vault encryption, tracker, reco, PDFs)
```

## Known limits

- The knowledge-base entries are written conservatively and every one is marked
  `needs_verification: true`; fees are never invented. Verify every entry
  against the official portal before relying on it in a demo.
- The centre directory is sample data across major cities; add your district in
  `data/centres.json`.
- The free Gemma endpoints are rate-limited and occasionally error; add several
  keys from https://aistudio.google.com for a smoother demo.
- Long or very low-resolution documents read worse than clear photos.
- Answers explain documents and guide processes; they are not legal or
  financial advice.

## What you must do by hand

1. Paste your API keys into `.env` (`GEMINI_API_KEYS=key1,key2`).
2. Set a long random `APP_SECRET_KEY` for any real deployment (and
   `COOKIE_SECURE=1` behind HTTPS).
3. Optionally add admin emails to `ADMIN_EMAILS`.
4. Verify every entry in `data/forms.json`, `data/schemes.json` and
   `data/centres.json` against official sources.
5. Test a Marathi/Tamil/Telugu PDF and a real document photo before a demo.

Built with AI-assisted coding (OpenCode).
