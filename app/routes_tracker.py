"""The paperwork process tracker: keep every ongoing application honest.

An application is a small state machine (started -> documents_gathered ->
submitted -> under_review -> approved/rejected -> completed) with a timeline of
events, a target date, the office where things are stuck, and computed alerts:
overdue targets, upcoming target dates, and deadlines found inside stored scan
readings.
"""
import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Request

from . import db, security, store
from .routes_auth import get_current_user
from .schemas import AlertCreate, AlertRead, ApplicationCreate, ApplicationUpdate, EventCreate

router = APIRouter(prefix="/api", tags=["tracker"])

STATUS_LABELS = {
    "started": "Started",
    "documents_gathered": "Documents gathered",
    "submitted": "Submitted",
    "under_review": "Under review",
    "action_needed": "Action needed from you",
    "approved": "Approved",
    "rejected": "Rejected",
    "completed": "Completed",
}


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _days_to(value):
    d = _parse_date(value)
    if d is None:
        return None
    return (d - datetime.date.today()).days


def _compute_alerts(user):
    """Deadlines the user should be warned about, computed fresh each call."""
    alerts = []
    for app in store.list_applications(user["id"]):
        days = _days_to(app.get("target_date"))
        if days is None:
            continue
        if days < 0 and app["status"] not in ("approved", "completed"):
            alerts.append({
                "kind": "warning",
                "title": f"{app['form_name']}: target date passed {abs(days)} days ago",
                "body": f"Status is “{STATUS_LABELS.get(app['status'], app['status'])}”"
                        + (f", office: {app['office']}." if app.get("office") else "."),
                "due_date": app.get("target_date"),
                "source": "application",
                "application_id": app["id"],
            })
        elif 0 <= days <= max(app.get("remind_days") or 3, 1) and app["status"] not in ("approved", "completed"):
            alerts.append({
                "kind": "warning" if days <= 1 else "reminder",
                "title": f"{app['form_name']}: target date "
                         + ("is today" if days == 0 else ("is tomorrow" if days == 1 else f"in {days} days")),
                "body": f"Status is “{STATUS_LABELS.get(app['status'], app['status'])}”"
                        + (f", office: {app['office']}." if app.get("office") else "."),
                "due_date": app.get("target_date"),
                "source": "application",
                "application_id": app["id"],
            })
    for row in store.list_scans(user["id"]):
        analysis = security.safe_decrypt(user["id"], row.get("analysis_enc") or b"")
        if not analysis:
            continue
        try:
            data = json.loads(analysis)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        label = f"Scan #{row['id']}"
        raw_label = security.safe_decrypt(user["id"], row.get("label_enc") or b"")
        if raw_label:
            try:
                label = json.loads(raw_label).get("label") or label
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        for d in data.get("deadlines", []):
            days = d.get("days_left")
            if days is None:
                continue
            if days < 0:
                alerts.append({
                    "kind": "warning",
                    "title": f"{label}: deadline passed",
                    "body": f"{d.get('what', 'Deadline')} was {abs(days)} days ago ({d.get('date_iso')}).",
                    "due_date": d.get("date_iso"),
                    "source": "scan",
                    "scan_id": row["id"],
                })
            elif days <= 7:
                alerts.append({
                    "kind": "warning" if days <= 2 else "reminder",
                    "title": f"{label}: {d.get('what', 'Deadline')} "
                             + ("is today" if days == 0 else f"in {days} days"),
                    "body": f"Date: {d.get('date_iso')}. Open the scan reading for details.",
                    "due_date": d.get("date_iso"),
                    "source": "scan",
                    "scan_id": row["id"],
                })
        for flag in data.get("red_flags", [])[:3]:
            alerts.append({
                "kind": "warning",
                "title": f"{label}: warning found",
                "body": str(flag),
                "due_date": None,
                "source": "scan",
                "scan_id": row["id"],
            })
    for manual in store.list_alerts(user["id"]):
        days = _days_to(manual.get("due_date"))
        alerts.append({
            "kind": manual.get("kind") or "reminder",
            "title": manual["title"],
            "body": manual.get("body", ""),
            "due_date": manual.get("due_date"),
            "source": "manual",
            "alert_id": manual["id"],
            "read": bool(manual.get("read")),
            "days_left": days,
        })
    order = {"warning": 0, "reminder": 1}
    alerts.sort(key=lambda a: (order.get(a["kind"], 2), a.get("due_date") or "9999"))
    return alerts


@router.get("/applications")
async def list_applications(user=Depends(get_current_user)):
    apps = store.list_applications(user["id"])
    for app in apps:
        app["status_label"] = STATUS_LABELS.get(app["status"], app["status"])
        app["days_left"] = _days_to(app.get("target_date"))
        app["events"] = store.list_events(app["id"])
    return {"applications": apps, "statuses": STATUS_LABELS}


@router.post("/applications")
async def create_application(req: ApplicationCreate, request: Request, user=Depends(get_current_user)):
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    form_name = req.form_name.strip()
    form_id = req.form_id.strip()
    if form_id and not form_name:
        form = db.find_form(form_id)
        if not form:
            raise HTTPException(status_code=404, detail="That form is not in the verified knowledge base.")
        form_name = form["name"]
    if not form_name:
        raise HTTPException(status_code=400, detail="Give the paperwork a name so you can recognise it later.")
    if req.target_date and not _parse_date(req.target_date):
        raise HTTPException(status_code=400, detail="The target date must look like YYYY-MM-DD.")
    app_id = store.create_application(
        user["id"], form_id=form_id, form_name=form_name, office=req.office,
        reference_no=req.reference_no, target_date=req.target_date or None,
        notes=req.notes, remind_days=req.remind_days,
    )
    return {"ok": True, "id": app_id}


@router.get("/applications/{app_id}")
async def get_application(app_id: int, user=Depends(get_current_user)):
    app = store.get_application(user["id"], app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    app["status_label"] = STATUS_LABELS.get(app["status"], app["status"])
    app["days_left"] = _days_to(app.get("target_date"))
    app["events"] = store.list_events(app_id)
    form = db.find_form(app.get("form_id") or "")
    if form:
        app["form"] = {
            "where_to_go": form.get("where_to_go", {}),
            "processing_time": form.get("processing_time", ""),
            "compulsory_documents": form.get("compulsory_documents", form.get("documents", [])),
            "optional_documents": form.get("optional_documents", []),
            "costs": form.get("costs", []),
            "warnings": form.get("warnings", []),
            "official_url": form.get("official_url", ""),
        }
    return app


@router.patch("/applications/{app_id}")
async def update_application(app_id: int, req: ApplicationUpdate, request: Request, user=Depends(get_current_user)):
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    fields = req.model_dump(exclude_none=True)
    if "status" in fields and fields["status"] not in store.STATUSES:
        raise HTTPException(status_code=400, detail=f"Unknown status. Use one of: {', '.join(store.STATUSES)}")
    if fields.get("target_date") and not _parse_date(fields["target_date"]):
        raise HTTPException(status_code=400, detail="The target date must look like YYYY-MM-DD.")
    old = store.get_application(user["id"], app_id)
    if not old:
        raise HTTPException(status_code=404, detail="Application not found.")
    if not store.update_application(user["id"], app_id, **fields):
        raise HTTPException(status_code=400, detail="Nothing to update.")
    if fields.get("status") and fields["status"] != old["status"]:
        store.add_app_event(
            user["id"], app_id, fields["status"],
            note="Status updated in Samajh.",
        )
    return {"ok": True}


@router.post("/applications/{app_id}/events")
async def add_event(app_id: int, req: EventCreate, request: Request, user=Depends(get_current_user)):
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    if req.status not in store.STATUSES:
        raise HTTPException(status_code=400, detail=f"Unknown status. Use one of: {', '.join(store.STATUSES)}")
    if not store.add_app_event(user["id"], app_id, req.status, req.note):
        raise HTTPException(status_code=404, detail="Application not found.")
    return {"ok": True, "events": store.list_events(app_id)}


@router.delete("/applications/{app_id}")
async def delete_application(app_id: int, request: Request, user=Depends(get_current_user)):
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    if not store.delete_application(user["id"], app_id):
        raise HTTPException(status_code=404, detail="Application not found.")
    return {"ok": True}


@router.get("/alerts")
async def alerts(user=Depends(get_current_user)):
    items = _compute_alerts(user)
    return {"alerts": items, "unread": sum(1 for a in items if not a.get("read", False))}


@router.post("/alerts")
async def create_alert(req: AlertCreate, request: Request, user=Depends(get_current_user)):
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    if req.due_date and not _parse_date(req.due_date):
        raise HTTPException(status_code=400, detail="The date must look like YYYY-MM-DD.")
    alert_id = store.create_alert(user["id"], req.title, req.body, req.due_date, req.kind)
    return {"ok": True, "id": alert_id}


@router.patch("/alerts/{alert_id}")
async def mark_alert(alert_id: int, req: AlertRead, request: Request, user=Depends(get_current_user)):
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    if not store.set_alert_read(user["id"], alert_id, req.read):
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"ok": True}


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, request: Request, user=Depends(get_current_user)):
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    if not store.delete_alert(user["id"], alert_id):
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"ok": True}
