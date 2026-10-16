"""Pydantic models for API responses."""
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
    steps: List[str] = Field(default_factory=list)
    official_url: str = ""
    notes: str = ""


class TextReply(BaseModel):
    type: Literal["text"] = "text"
    text: str = ""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
