"""Tools the model can call in the form-guide chat, run server-side.

Everything a tool returns comes from the verified knowledge base (forms.json,
schemes.json, centres.json) loaded by db.py. The model never answers from its
own memory; it can only relay what these tools return.
"""
import datetime
import json


def days_until(date_iso):
    """Days from today to a date. Past dates return a negative number."""
    target = datetime.date.fromisoformat(date_iso)
    return {"date_iso": date_iso, "days_until": (target - datetime.date.today()).days}


def find_centres(centres, service="", area=""):
    """Filter centres by a service keyword and/or area keyword, case-insensitive."""
    service = (service or "").strip().lower()
    area = (area or "").strip().lower()
    out = []
    for c in centres:
        hay = " ".join([
            c.get("name", ""), c.get("type", ""), c.get("address", ""),
            c.get("area", ""), c.get("district", ""), c.get("state", ""),
            " ".join(c.get("services", [])),
        ]).lower()
        if service and service not in hay:
            continue
        if area and area not in hay:
            continue
        out.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "type": c.get("type"),
            "address": c.get("address"),
            "area": c.get("area"),
            "district": c.get("district"),
            "state": c.get("state"),
            "hours": c.get("hours"),
            "phone": c.get("phone"),
            "services": c.get("services", []),
        })
    return out[:8]


def execute_tool(name, args, forms, schemes=None, centres=None):
    """Run one tool call against the knowledge base. Always returns a dict."""
    schemes = schemes or []
    centres = centres or []
    args = args or {}

    if name == "list_supported_forms":
        return {"forms": [{"id": f["id"], "name": f["name"]} for f in forms]}

    if name == "get_form_requirements":
        form_id = str(args.get("form_id", ""))
        for form in forms:
            if form.get("id") == form_id:
                return form
        return {
            "error": f"Unknown form_id: {form_id}. Supported ids: "
            + ", ".join(f["id"] for f in forms)
        }

    if name == "list_supported_schemes":
        return {
            "schemes": [
                {"id": s["id"], "name": s["name"], "profiles": s.get("profiles", [])}
                for s in schemes
            ]
        }

    if name == "get_scheme_details":
        scheme_id = str(args.get("scheme_id", ""))
        for scheme in schemes:
            if scheme.get("id") == scheme_id:
                return scheme
        return {
            "error": f"Unknown scheme_id: {scheme_id}. Supported ids: "
            + ", ".join(s["id"] for s in schemes)
        }

    if name == "find_centre":
        results = find_centres(centres, args.get("service", ""), args.get("area", ""))
        if not results:
            return {"error": "No centre in the directory matches. Ask for a nearby district or the service name."}
        return {"centres": results}

    if name == "days_until":
        date_iso = str(args.get("date_iso", ""))
        try:
            return days_until(date_iso)
        except ValueError:
            return {"error": f"Could not parse date: {date_iso}"}

    return {"error": f"Unknown tool: {name}"}


def tool_result_text(name, result):
    """Serialise a tool result for feeding back into the model."""
    return f"TOOL_RESULT ({name}): " + json.dumps(result, ensure_ascii=False)
