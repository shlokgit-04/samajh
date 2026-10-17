"""Pydantic models for API requests and responses."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class LabelValue(BaseModel):
    label: str = ""
    value: str = ""


class Deadline(BaseModel):
    date_iso: Optional[str] = None
    what: str = ""
    days_left: Optional[int] = None


class Action(BaseModel):
    text: str = ""
    urgency: Literal["now", "soon", "later"] = "soon"


class Flagged(BaseModel):
    value: bool = False
    reason: str = ""


class AnalysisResult(BaseModel):
    document_type: str = ""
    issuer: str = ""
    summary: str = ""
    explanation: str = ""
    key_facts: List[LabelValue] = Field(default_factory=list)
    amounts: List[LabelValue] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    can_ignore: Flagged = Field(default_factory=Flagged)
    needs_professional: Flagged = Field(default_factory=Flagged)
    confidence: Literal["high", "medium", "low"] = "medium"


class FormSheet(BaseModel):
    type: Literal["form_sheet"] = "form_sheet"
    form_name: str = ""
    mode: Literal["home", "partly_home", "in_person"] = "partly_home"
    mode_reason: str = ""
    documents: List[str] = Field(default_factory=list)
    compulsory_documents: List[str] = Field(default_factory=list)
    optional_documents: List[str] = Field(default_factory=list)
    extra_info: str = ""
    costs: List[LabelValue] = Field(default_factory=list)
    where_to_go: str = ""
    processing_time: str = ""
    warnings: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    official_url: str = ""
    notes: str = ""


class TextReply(BaseModel):
    type: Literal["text"] = "text"
    text: str = ""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    lang: Optional[str] = None


# ---------------------------------------------------------------- auth

class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    role: Literal[
        "citizen", "farmer", "govt_employee", "doctor", "student",
        "senior_citizen", "entrepreneur", "worker",
    ] = "citizen"
    lang: str = "en"
    area: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=20)
    consent: bool = False


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[str] = None
    lang: Optional[str] = None
    area: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------- tracker

class ApplicationCreate(BaseModel):
    form_id: str = Field(default="", max_length=80)
    form_name: str = Field(default="", max_length=200)
    office: str = Field(default="", max_length=200)
    reference_no: str = Field(default="", max_length=120)
    target_date: Optional[str] = Field(default=None, max_length=10)
    notes: str = Field(default="", max_length=2000)
    remind_days: int = Field(default=3, ge=0, le=60)


class ApplicationUpdate(BaseModel):
    form_name: Optional[str] = Field(default=None, max_length=200)
    office: Optional[str] = Field(default=None, max_length=200)
    reference_no: Optional[str] = Field(default=None, max_length=120)
    status: Optional[str] = None
    target_date: Optional[str] = Field(default=None, max_length=10)
    notes: Optional[str] = Field(default=None, max_length=2000)
    remind_days: Optional[int] = Field(default=None, ge=0, le=60)


class EventCreate(BaseModel):
    status: str
    note: str = Field(default="", max_length=2000)


class AlertCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=2000)
    due_date: Optional[str] = Field(default=None, max_length=10)
    kind: Literal["reminder", "warning"] = "reminder"


class AlertRead(BaseModel):
    read: bool = True


# ---------------------------------------------------------------- pdf

class PdfSection(BaseModel):
    heading: str = Field(max_length=200)
    items: List[str] = Field(default_factory=list)


class ChecklistPdfRequest(BaseModel):
    title: str = Field(default="Checklist", max_length=200)
    subtitle: str = Field(default="", max_length=300)
    sections: List[PdfSection] = Field(default_factory=list)
    lang: str = "en"
    notes: str = Field(default="", max_length=2000)
