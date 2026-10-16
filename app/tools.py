"""The three tools Gemma can call in the form-guide chat, run server-side."""
import datetime
import json


def days_until(date_iso):
    """Days from today to a date. Past dates return a negative number."""
    target = datetime.date.fromisoformat(date_iso)
    return {"date_iso": date_iso, "days_until": (target - datetime.date.today()).days}


def execute_tool(name, args, forms):
    """Run one tool call against the knowledge base. Always returns a dict."""
    if name == "list_supported_forms":
        return {"forms": [{"id": f["id"], "name": f["name"]} for f in forms]}

    if name == "get_form_requirements":
        form_id = (args or {}).get("form_id", "")
        for form in forms:
            if form.get("id") == form_id:
                return form
        return {
            "error": f"Unknown form_id: {form_id}. Supported ids: "
            + ", ".join(f["id"] for f in forms)
        }

    if name == "days_until":
        date_iso = (args or {}).get("date_iso", "")
        try:
            return days_until(date_iso)
        except ValueError:
            return {"error": f"Could not parse date: {date_iso}"}

    return {"error": f"Unknown tool: {name}"}


def tool_result_text(name, result):
    """Serialise a tool result for feeding back into the model."""
    return f"TOOL_RESULT ({name}): " + json.dumps(result, ensure_ascii=False)
