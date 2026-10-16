/* Samajh front-end: two modes, one language switch, no framework. */

const $ = (id) => document.getElementById(id);

const state = {
  lang: "en",
  imageFile: null,
  busy: false,
};

/* ---------- tabs ---------- */

function selectTab(which) {
  const doc = which === "doc";
  $("tab-doc").classList.toggle("is-active", doc);
  $("tab-chat").classList.toggle("is-active", !doc);
  $("tab-doc").setAttribute("aria-selected", String(doc));
  $("tab-chat").setAttribute("aria-selected", String(!doc));
  $("panel-doc").classList.toggle("is-active", doc);
  $("panel-doc").hidden = !doc;
  $("panel-chat").hidden = doc;
}
$("tab-doc").addEventListener("click", () => selectTab("doc"));
$("tab-chat").addEventListener("click", () => selectTab("chat"));

/* ---------- language ---------- */

document.querySelectorAll(".lang-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.lang = btn.dataset.lang;
    document.querySelectorAll(".lang-toggle").forEach((b) => {
      const active = b === btn;
      b.classList.toggle("is-active", active);
      b.setAttribute("aria-pressed", String(active));
    });
    document.body.classList.toggle("show-devanagari", state.lang !== "en");
  });
});

/* ---------- upload: drop, click, paste, camera ---------- */

const tray = $("drop-tray");
const fileInput = $("file-input");

function acceptFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    showDocError("That is not an image file. A photo or scan of the document is needed (JPG, PNG or WebP).");
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    showDocError("That file is over 8 MB. A smaller photo works just as well.");
    return;
  }
  clearDocError();
  state.imageFile = file;
  const url = URL.createObjectURL(file);
  $("paper-img").src = url;
  tray.hidden = true;
  $("paper-frame").hidden = false;
  analyze(file);
}

tray.addEventListener("click", () => fileInput.click());
tray.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
});
fileInput.addEventListener("change", () => acceptFile(fileInput.files[0]));

["dragover", "dragenter"].forEach((ev) =>
  tray.addEventListener(ev, (e) => { e.preventDefault(); tray.classList.add("is-dragover"); }));
["dragleave", "drop"].forEach((ev) =>
  tray.addEventListener(ev, (e) => { e.preventDefault(); tray.classList.remove("is-dragover"); }));
tray.addEventListener("drop", (e) => acceptFile(e.dataTransfer.files[0]));

document.addEventListener("paste", (e) => {
  const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
  if (item) { selectTab("doc"); acceptFile(item.getAsFile()); }
});

$("paper-change").addEventListener("click", () => fileInput.click());

/* ---------- document reading ---------- */

function showDocError(text) {
  const el = $("doc-error");
  el.textContent = text;
  el.hidden = false;
}
function clearDocError() { $("doc-error").hidden = true; }

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function analyze(file) {
  if (state.busy) return;
  state.busy = true;
  $("doc-loading").hidden = false;
  $("doc-result").hidden = true;
  clearDocError();
  const started = Date.now();
  try {
    const fd = new FormData();
    fd.append("image", file, file.name || "document.jpg");
    fd.append("lang", state.lang);
    const res = await fetch("/api/analyze", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) {
      showDocError(data.detail || data.error || "Something went wrong. Please try again.");
    } else {
      renderAnalysis(data);
    }
  } catch (err) {
    showDocError("Could not reach the service. Check your connection and try again.");
  } finally {
    $("doc-loading").hidden = true;
    state.busy = false;
  }
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso + "T00:00:00").toLocaleDateString("en-IN",
      { day: "numeric", month: "short", year: "numeric" }).toUpperCase();
  } catch { return iso; }
}

function stampFor(r) {
  const soon = (r.deadlines || []).some((d) => d.days_left !== null && d.days_left <= 14 && d.days_left >= 0);
  const overdue = (r.deadlines || []).some((d) => d.days_left !== null && d.days_left < 0);
  const urgent = (r.actions || []).some((a) => a.urgency === "now");
  const nextDate = (r.deadlines || []).filter((d) => d.date_iso).map((d) => d.date_iso)[0];
  if (overdue) return { text: "OVERDUE", cls: "" };
  if (urgent || soon) return { text: nextDate ? "ACT BY " + fmtDate(nextDate) : "ACT SOON", cls: "" };
  if (r.can_ignore && r.can_ignore.value) return { text: "CAN BE IGNORED", cls: "green" };
  return { text: "ON FILE", cls: "green" };
}

function renderAnalysis(r) {
  const stamp = stampFor(r);
  const facts = [...(r.key_facts || []), ...(r.amounts || [])]
    .slice(0, 8)
    .map((f) => `<div class="fact-cell"><p class="fact-label">${esc(f.label)}</p><p class="fact-value">${esc(f.value)}</p></div>`)
    .join("");

  const urgencyWord = { now: "do now", soon: "do soon", later: "when you can" };
  const actions = (r.actions || []).map((a, i) =>
    `<div class="action-row"><span class="action-num">${i + 1}</span><p class="action-text">${esc(a.text)}</p>
     <span class="action-when ${esc(a.urgency)}">${esc(urgencyWord[a.urgency] || "do soon")}</span></div>`).join("");

  const deadlines = (r.deadlines || []).map((d) => {
    let left = "";
    if (d.days_left !== null && d.days_left !== undefined) {
      if (d.days_left < 0) left = Math.abs(d.days_left) + " days past";
      else if (d.days_left === 0) left = "today";
      else left = d.days_left + " days left";
    }
    const cls = (d.days_left !== null && d.days_left <= 7) ? (d.days_left < 0 ? "overdue" : "soon") : "";
    return `<div class="deadline-row"><span class="deadline-date">${esc(fmtDate(d.date_iso))}</span>
      <span class="deadline-what">${esc(d.what)}</span>
      <span class="deadline-left ${cls}">${esc(left)}</span></div>`;
  }).join("");

  const redflags = (r.red_flags || []).map((t) => `<p class="redflag">${esc(t)}</p>`).join("");

  $("doc-result").innerHTML = `
    <div class="stamp ${stamp.cls}">${esc(stamp.text)}</div>
    <h1 class="doc-type">${esc(r.document_type || "Document")}</h1>
    <p class="doc-issuer">${esc(r.issuer || "")}</p>
    <p class="doc-summary">${esc(r.summary)}</p>
    <p class="doc-explanation">${esc(r.explanation)}</p>
    ${facts ? `<div class="fact-strip">${facts}</div>` : ""}
    ${actions ? `<div class="actions"><p class="section-label">What to do</p>${actions}</div>` : ""}
    ${deadlines ? `<div class="deadlines"><p class="section-label">Deadlines</p>${deadlines}</div>` : ""}
    ${redflags ? `<div class="redflags"><p class="section-label">Watch out for</p>${redflags}</div>` : ""}
    <div class="verdict">
      <p class="section-label">Two honest verdicts</p>
      <p><strong class="${r.can_ignore?.value ? "flag-no" : "flag-yes"}">${r.can_ignore?.value ? "You can set this aside:" : "This needs attention:"}</strong> ${esc(r.can_ignore?.reason || "")}</p>
      <p><strong class="${r.needs_professional?.value ? "flag-yes" : "flag-no"}">${r.needs_professional?.value ? "A professional may help:" : "No professional needed:"}</strong> ${esc(r.needs_professional?.reason || "")}</p>
    </div>
    ${metaBlock(r.trace)}
  `;
  $("doc-result").hidden = false;
}

function metaBlock(trace) {
  if (!trace) return "";
  const lines = [];
  lines.push("model: " + (trace.model || "—"));
  lines.push("key slot: " + (trace.key_slot !== undefined ? trace.key_slot : "—"));
  lines.push("latency: " + (trace.latency_ms || "—") + " ms");
  if (trace.tool_calls && trace.tool_calls.length) {
    lines.push("tool calls:");
    trace.tool_calls.forEach((t) => lines.push("  " + t.tool + " " + JSON.stringify(t.args)));
  }
  return `<details class="answer-meta"><summary>How this was answered</summary><pre>${esc(lines.join("\n"))}</pre></details>`;
}

/* ---------- form chat ---------- */

const transcript = $("transcript");

function addLine(speaker, html, isHtml = false) {
  const row = document.createElement("div");
  row.className = "transcript-row" + (speaker === "YOU" ? " you" : "");
  const who = document.createElement("span");
  who.className = "speaker";
  who.textContent = speaker;
  const body = document.createElement("div");
  body.className = "transcript-text";
  if (isHtml) body.innerHTML = html; else body.textContent = html;
  transcript.appendChild(row);
  row.appendChild(who);
  row.appendChild(body);
  body.scrollIntoView({ behavior: "smooth", block: "end" });
  return body;
}

function renderFormSheet(sheet) {
  const modeText = { home: "CAN BE DONE AT HOME", partly_home: "PARTLY AT HOME", in_person: "IN PERSON ONLY" }[sheet.mode] || sheet.mode;
  const cls = sheet.mode === "in_person" ? "red" : "";
  const docs = (sheet.documents || []).map((d) =>
    `<li><input type="checkbox" tabindex="0" /><span>${esc(d)}</span></li>`).join("");
  const steps = (sheet.steps || []).map((s, i) =>
    `<div class="sheet-step"><span class="sheet-step-num">${i + 1}</span><p>${esc(s)}</p></div>`).join("");
  return `
    <div class="form-sheet">
      <div class="sheet-stamp ${cls}">${esc(modeText)}</div>
      <h2 class="sheet-title">${esc(sheet.form_name)}</h2>
      <p class="sheet-mode-reason">${esc(sheet.mode_reason)}</p>
      ${docs ? `<div class="sheet-checklist-wrap"><p class="section-label">Documents</p><ul class="sheet-checklist">${docs}</ul></div>` : ""}
      ${steps ? `<div class="sheet-steps"><p class="section-label">Steps</p>${steps}</div>` : ""}
      ${sheet.notes ? `<p class="sheet-notes">${esc(sheet.notes)}</p>` : ""}
      ${sheet.official_url ? `<a class="sheet-link" href="${esc(sheet.official_url)}" target="_blank" rel="noopener noreferrer">${esc(sheet.official_url)}</a>` : ""}
      <p class="sheet-verify">Always verify on the official portal before you act.</p>
      ${metaBlock(sheet.trace)}
    </div>`;
}

async function ask(message) {
  if (state.busy) return;
  state.busy = true;
  addLine("YOU", message);
  $("chat-loading").hidden = false;
  $("chat-send").disabled = true;
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    if (!res.ok) {
      addLine("SAMAJH", data.detail || data.error || "Something went wrong. Please try again.");
      return;
    }
    if (data.type === "form_sheet") {
      const holder = addLine("SAMAJH", "", true);
      holder.innerHTML = renderFormSheet(data);
    } else {
      addLine("SAMAJH", data.text || "");
    }
  } catch (err) {
    addLine("SAMAJH", "Could not reach the service. Check your connection and try again.");
  } finally {
    $("chat-loading").hidden = true;
    $("chat-send").disabled = false;
    state.busy = false;
  }
}

$("chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const value = $("chat-input").value.trim();
  if (!value) return;
  $("chat-input").value = "";
  ask(value);
});

/* ---------- suggestions + footer model line ---------- */

const SUGGESTIONS = [
  { id: "pan-new", label: "PAN card" },
  { id: "aadhaar-update", label: "Aadhaar address update" },
  { id: "voter-new", label: "Voter ID (Form 6)" },
  { id: "passport-new", label: "Passport" },
  { id: "learners-licence", label: "Learner's licence" },
];
SUGGESTIONS.forEach((s) => {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = s.label;
  b.addEventListener("click", () => ask(`How do I apply for / do: ${s.label}?`));
  $("suggest").appendChild(b);
});

fetch("/api/health").then((r) => r.json()).then((h) => {
  if (h && h.model) $("footer-model").textContent = `Powered by Gemma 4 · ${h.model} via the Gemini API`;
}).catch(() => {});
