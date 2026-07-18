from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "docs" / "Code" / "frontend"

app = FastAPI(title="Forensa API (No Database)", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory sample data. Changes remain only while the server is running.
CASES: list[dict[str, Any]] = [
    {"id": 1, "case_number": "FC-2026-001", "title": "Call for Forensic Evaluation: Homicide Case", "case_type": "Homicide", "status": "Active", "assigned_to": "Dr. R. Gunawardena", "opened_date": "2026-07-10", "description": "Forensic evaluation requested by law enforcement."},
    {"id": 2, "case_number": "PM-2026-884", "title": "Autopsy Status Update: Post Mortem Record", "case_type": "Post Mortem", "status": "In Progress", "assigned_to": "Dr. R. Gunawardena", "opened_date": "2026-07-15", "description": "Post-mortem examination and documentation in progress."},
    {"id": 3, "case_number": "CC-2026-4022", "title": "Scheduled Court Testimony Report", "case_type": "Court Testimony", "status": "Scheduled", "assigned_to": "Dr. K. Silva", "opened_date": "2026-07-02", "description": "Expert testimony scheduled for Case Court 3."},
]

RESOURCES: dict[str, list[dict[str, Any]]] = {
    "laboratory": [
        {"id": 1, "request_number": "LAB-8821", "case_number": "FC-2026-001", "sample_type": "Blood / Toxicology", "assigned_analyst": "Dr. K. Silva", "status": "In Progress", "received_date": "2026-07-17", "notes": "Toxicology screening underway."},
        {"id": 2, "request_number": "LAB-8822", "case_number": "PM-2026-884", "sample_type": "DNA Specimen", "assigned_analyst": "Dr. A. Perera", "status": "Completed", "received_date": "2026-07-16", "notes": "DNA profile completed."},
    ],
    "court-reports": [
        {"id": 1, "report_number": "CR-2026-4022", "case_number": "CC-2026-4022", "court_name": "Case Court 3", "testimony_date": "2026-08-12", "status": "Scheduled", "signed_by": None, "summary": "Scheduled expert testimony."},
        {"id": 2, "report_number": "CR-2026-3981", "case_number": "FC-2026-001", "court_name": "High Court 1", "testimony_date": "2026-07-02", "status": "Filed", "signed_by": "Dr. R. Gunawardena", "summary": "Expert medical testimony filed."},
    ],
    "incidents": [],
    "staff": [
        {"id": 1, "employee_number": "EMP-401", "full_name": "Dr. R. Gunawardena", "role": "Senior Pathologist", "extension": "401", "duty_status": "On Duty", "shift": "Day"},
        {"id": 2, "employee_number": "EMP-405", "full_name": "Dr. K. Silva", "role": "Laboratory Lead", "extension": "405", "duty_status": "On Duty", "shift": "Day"},
        {"id": 3, "employee_number": "EMP-412", "full_name": "Officer Fernando", "role": "Field Duty Officer", "extension": "412", "duty_status": "On Duty", "shift": "Field"},
    ],
    "audit-logs": [
        {"id": 1, "timestamp": "2026-07-18 10:42:01", "username": "dr_gunawardena", "action": "Updated Post Mortem", "resource": "PM-2026-884"},
        {"id": 2, "timestamp": "2026-07-18 09:15:30", "username": "admin_movers", "action": "Assigned Analyst", "resource": "LAB-8821"},
    ],
}


class CaseCreate(BaseModel):
    case_number: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=200)
    case_type: str
    status: str
    assigned_to: str | None = None
    opened_date: str
    description: str = ""


class CaseUpdate(BaseModel):
    title: str | None = None
    case_type: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    opened_date: str | None = None
    description: str | None = None


def find_case(case_id: int) -> dict[str, Any]:
    for case in CASES:
        if case["id"] == case_id:
            return case
    raise HTTPException(404, "Case not found")


def add_audit(action: str, resource: str) -> None:
    logs = RESOURCES["audit-logs"]
    logs.append({
        "id": max((item["id"] for item in logs), default=0) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "username": "system_user",
        "action": action,
        "resource": resource,
    })


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "storage": "memory", "database": "none"}


@app.get("/api/cases")
def list_cases(status_filter: str | None = None) -> list[dict[str, Any]]:
    items = CASES
    if status_filter:
        items = [case for case in CASES if case["status"] == status_filter]
    return sorted(items, key=lambda item: item["id"], reverse=True)


@app.get("/api/cases/{case_id}")
def get_case(case_id: int) -> dict[str, Any]:
    return find_case(case_id)


@app.post("/api/cases", status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate) -> dict[str, Any]:
    if any(case["case_number"] == payload.case_number for case in CASES):
        raise HTTPException(409, "Case number already exists")
    item = {"id": max((case["id"] for case in CASES), default=0) + 1, **payload.model_dump()}
    CASES.append(item)
    add_audit("Created Case", item["case_number"])
    return item


@app.patch("/api/cases/{case_id}")
def update_case(case_id: int, payload: CaseUpdate) -> dict[str, Any]:
    case = find_case(case_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "No fields supplied")
    case.update(changes)
    add_audit("Updated Case", case["case_number"])
    return case


@app.delete("/api/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: int) -> Response:
    case = find_case(case_id)
    CASES.remove(case)
    add_audit("Deleted Case", case["case_number"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/{resource_name}")
def list_resource(resource_name: str) -> list[dict[str, Any]]:
    if resource_name not in RESOURCES:
        raise HTTPException(404, "Resource not found")
    return sorted(RESOURCES[resource_name], key=lambda item: item["id"], reverse=True)


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def page_heading(title: str, body: str) -> str:
    return f'<h2 style="color:#260099;border-bottom:2px solid #260099;margin-top:0;padding-bottom:5px;font-size:18px;">{esc(title)}</h2>{body}'


@app.get("/api/pages/{page_id}", response_class=HTMLResponse)
def dynamic_page(page_id: str) -> str:
    if page_id in {"about_us", "contact_us"}:
        return (FRONTEND_DIR / "pages" / f"{page_id}.html").read_text(encoding="utf-8")
    if page_id == "cases":
        cards = "".join(f'<div style="background:#fffdf5;border:1px solid #e0dacb;padding:15px;margin-bottom:8px;"><strong>{esc(x["title"])} – {esc(x["case_number"])}</strong><p style="margin:8px 0;font-size:13px;">Status: {esc(x["status"])} | Assigned: {esc(x["assigned_to"] or "Unassigned")}</p><button onclick="showCase({x["id"]})" style="background:#004488;color:white;border:0;padding:6px 15px;cursor:pointer;">View Case</button></div>' for x in reversed(CASES))
        return page_heading("Active Forensic Cases & Applications", cards or "<p>No cases found.</p>")
    if page_id == "laboratory":
        body = "".join(f'<tr><td>{esc(x["request_number"])}</td><td>{esc(x["sample_type"])}</td><td>{esc(x["assigned_analyst"])}</td><td><strong>{esc(x["status"])}</strong></td></tr>' for x in RESOURCES["laboratory"])
        return page_heading("Laboratory Services", f'<table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;background:white;"><tr style="background:#260099;color:white;"><th>Request ID</th><th>Sample Type</th><th>Assigned Analyst</th><th>Status</th></tr>{body}</table>')
    if page_id == "court_reports":
        lis = "".join(f'<li><strong>{esc(x["report_number"])}:</strong> {esc(x["status"])} — {esc(x["court_name"])}</li>' for x in RESOURCES["court-reports"])
        return page_heading("Court Reports & Testimonies", f'<div style="background:white;border:1px solid #e0dacb;padding:20px;"><ul>{lis}</ul></div>')
    if page_id == "incidents":
        items = RESOURCES["incidents"]
        content = "".join(f'<div><strong>{esc(x["incident_number"])}: {esc(x["title"])}</strong><p>{esc(x["location"])} — {esc(x["status"])}</p></div>' for x in items) if items else "<p><em>No active field incident dispatches recorded.</em></p>"
        return page_heading("Incident Logs", f'<div style="background:white;border:1px solid #e0dacb;padding:20px;">{content}</div>')
    if page_id == "staff":
        lis = "".join(f'<li><strong>{esc(x["role"])}:</strong> {esc(x["full_name"])} (Ext. {esc(x["extension"])}) — {esc(x["duty_status"])}</li>' for x in RESOURCES["staff"])
        return page_heading("Staff & Duty Roster", f'<div style="background:white;border:1px solid #e0dacb;padding:20px;"><ul>{lis}</ul></div>')
    if page_id == "audit_logs":
        body = "".join(f'<tr><td>{esc(x["timestamp"])}</td><td>{esc(x["username"])}</td><td>{esc(x["action"])}</td><td>{esc(x["resource"])}</td></tr>' for x in reversed(RESOURCES["audit-logs"]))
        return page_heading("System Audit Logs", f'<table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;background:white;"><tr style="background:#260099;color:white;"><th>Timestamp</th><th>User</th><th>Action</th><th>Resource</th></tr>{body}</table>')
    raise HTTPException(404, "Page not found")


@app.get("/")
def frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/pages", StaticFiles(directory=FRONTEND_DIR / "pages"), name="pages")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
