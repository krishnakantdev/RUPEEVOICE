from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent.parent
KB_PATH = BASE_DIR / "data" / "knowledge_base.yaml"
FRONTEND_DIR = BASE_DIR / "frontend"


def load_kb() -> dict[str, Any]:
    with KB_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


KB = load_kb()


class Lead(BaseModel):
    name: str = "Partner Lead"
    phone: str = ""
    language: str = "auto"
    city: str = ""
    source: str = "Demo"


class ChatRequest(BaseModel):
    session_id: str | None = None
    lead: Lead = Field(default_factory=Lead)
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    language: str
    stage: str
    score: int
    classification: Literal["Hot", "Warm", "Cold"]
    next_action: str
    objections: list[str]
    summary: dict[str, Any]


class BatchRequest(BaseModel):
    leads: list[Lead]


app = FastAPI(title="RupeeVoice AI Partner Lead Agent", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


SESSIONS: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_language(text: str, preferred: str = "auto") -> str:
    lowered = text.lower()
    if preferred and preferred != "auto":
        return preferred
    if re.search(r"[\u0900-\u097F]", text):
        return "hi-IN"
    hinglish_markers = [
        "hai",
        "haan",
        "namaste",
        "mujhe",
        "bataye",
        "nahi",
        "kya",
        "kaise",
        "broker ke saath",
        "soch",
        "baad mein",
    ]
    if any(marker in lowered for marker in hinglish_markers):
        return "hi-IN"
    return "en-IN"


def lang_key(language: str) -> str:
    return "hi" if language.startswith("hi") else "en"


def classification(score: int) -> Literal["Hot", "Warm", "Cold"]:
    if score >= 75:
        return "Hot"
    if score >= 45:
        return "Warm"
    return "Cold"


def next_action(label: str) -> str:
    if label == "Hot":
        return "Warm transfer to RM with full context and signup intent."
    if label == "Warm":
        return "Send WhatsApp signup link and schedule RM follow-up."
    return "Log for nurture campaign and retry later with lighter messaging."


def find_objection(text: str) -> str | None:
    lowered = text.lower()
    objection_map = {
        "already_with_broker": ["already", "another broker", "other broker", "zerodha", "angel", "upstox", "broker ke saath"],
        "small_network": ["contacts", "network", "clients", "log nahi", "enough people", "small"],
        "support": ["support", "issue", "problem", "client issue", "help"],
        "trust": ["trust", "trustworthy", "safe", "license", "regulated", "reliable", "bharosa"],
        "later": ["later", "think", "call me", "busy", "baad", "soch", "kal"],
    }
    for key, terms in objection_map.items():
        if any(term in lowered for term in terms):
            return key
    return None


def interest_delta(text: str) -> int:
    lowered = text.lower()
    score = 0
    positive = ["yes", "haan", "interested", "signup", "sign up", "start", "send", "link", "ready", "whatsapp"]
    medium = ["maybe", "details", "tell me", "explain", "benefit", "commission", "brokerage", "payout"]
    negative = ["not interested", "no ", "nahi", "don't want", "stop", "wrong number"]
    if any(term in lowered for term in positive):
        score += 24
    if any(term in lowered for term in medium):
        score += 12
    if any(term in lowered for term in negative):
        score -= 25
    contacts = re.findall(r"\b\d{2,5}\b", lowered)
    if contacts:
        largest = max(int(value) for value in contacts)
        if largest >= 100:
            score += 20
        elif largest >= 25:
            score += 10
    return score


def create_session(lead: Lead) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,
        "lead": lead.model_dump(),
        "language": lead.language if lead.language != "auto" else "en-IN",
        "stage": "opening",
        "score": 30,
        "objections": [],
        "topics": [],
        "messages": [],
        "started_at": now_iso(),
        "updated_at": now_iso(),
    }
    SESSIONS[session_id] = session
    return session


def get_session(session_id: str | None, lead: Lead) -> dict[str, Any]:
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    return create_session(lead)


def render(template_id: str, language: str, **kwargs: Any) -> str:
    text = KB["responses"][template_id][lang_key(language)]
    return text.format(**kwargs)


def build_summary(session: dict[str, Any]) -> dict[str, Any]:
    started = datetime.fromisoformat(session["started_at"])
    updated = datetime.fromisoformat(session["updated_at"])
    duration = max(1, int((updated - started).total_seconds()))
    label = classification(session["score"])
    return {
        "lead": session["lead"],
        "duration_seconds": duration,
        "topics_covered": sorted(set(session["topics"])),
        "objections_raised": session["objections"],
        "interest_score": session["score"],
        "classification": label,
        "recommended_next_action": next_action(label),
        "transcript": session["messages"],
    }


def choose_reply(session: dict[str, Any], user_text: str) -> str:
    lead_name = session["lead"].get("name") or "there"
    language = session["language"]
    objection = find_objection(user_text)
    if objection:
        if objection not in session["objections"]:
            session["objections"].append(objection)
        session["topics"].append("objection_handling")
        session["stage"] = "qualification"
        return KB["objections"][objection][lang_key(language)]

    lowered = user_text.lower()
    if session["stage"] == "opening":
        session["stage"] = "pitch"
        session["topics"].extend(["opening_hook", "key_benefits"])
        return render("pitch", language, name=lead_name)

    if any(word in lowered for word in ["how", "kaise", "start", "signup", "sign up", "join", "eligible"]):
        session["stage"] = "qualification"
        session["topics"].extend(["eligibility", "getting_started"])
        return render("eligibility", language)

    if any(word in lowered for word in ["yes", "haan", "interested", "ready", "send", "link", "whatsapp"]):
        session["score"] += 18
        session["stage"] = "close"
        session["topics"].append("closing")
        return render("close_hot", language)

    if any(word in lowered for word in ["no", "nahi", "not interested", "stop"]):
        session["score"] -= 20
        session["stage"] = "close"
        return render("close_cold", language)

    session["stage"] = "qualification"
    session["topics"].append("qualification")
    return render("qualify", language)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/dashboard")
def dashboard_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    session = get_session(payload.session_id, payload.lead)
    language = detect_language(payload.message, payload.lead.language)
    session["language"] = language
    session["score"] = max(0, min(100, session["score"] + interest_delta(payload.message)))
    session["messages"].append({"role": "lead", "text": payload.message, "language": language, "at": now_iso()})
    reply = choose_reply(session, payload.message)
    session["messages"].append({"role": "agent", "text": reply, "language": language, "at": now_iso()})
    session["updated_at"] = now_iso()
    label = classification(session["score"])
    return ChatResponse(
        session_id=session["id"],
        reply=reply,
        language=language,
        stage=session["stage"],
        score=session["score"],
        classification=label,
        next_action=next_action(label),
        objections=session["objections"],
        summary=build_summary(session),
    )


@app.post("/api/leads/batch")
def create_batch(payload: BatchRequest) -> dict[str, Any]:
    created = [create_session(lead) for lead in payload.leads]
    return {"created": len(created), "session_ids": [item["id"] for item in created]}


@app.get("/api/sessions")
def sessions() -> dict[str, Any]:
    summaries = [build_summary(session) | {"session_id": session["id"]} for session in SESSIONS.values()]
    funnel = {"contacted": len(summaries), "Hot": 0, "Warm": 0, "Cold": 0}
    for summary in summaries:
        funnel[summary["classification"]] += 1
    return {"funnel": funnel, "sessions": summaries}


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str) -> dict[str, Any]:
    session = SESSIONS[session_id]
    return build_summary(session) | {"session_id": session_id}
