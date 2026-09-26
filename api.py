import random
import time
from typing import Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

import agent  # noqa: E402  (reads GROQ settings after .env is loaded)
from investigation import Dataset, case_queue, entity_context, input_trace, investigate  # noqa: E402
from scenarios import build_demo_dataset  # noqa: E402
from scoring import score_all_entities  # noqa: E402

DEFAULT_SEED = 107

app = FastAPI(title="Zeyro Trade Sentinel", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

state: Dict = {"ds": None, "version": 0, "seed": DEFAULT_SEED}
feedback: Dict[str, Dict] = {}


def load(seed: int):
    entities, transactions = build_demo_dataset(seed=seed)
    evidence = score_all_entities(entities, transactions)
    state["version"] += 1
    state["seed"] = seed
    state["ds"] = Dataset(entities, transactions, evidence, state["version"])
    feedback.clear()
    agent.clear_cache()
    agent.prewarm(prewarm_jobs)


def ds() -> Dataset:
    return state["ds"]


def prewarm_jobs():
    d = ds()
    queue = case_queue(d)
    for c in queue["alerts"] + queue["monitored"][:1]:
        if ds().version != d.version:
            return
        inv = investigate(d, c["id"], feedback)
        yield d.version, inv["case"], inv["steps"]


def require_exporter(case_id: str):
    d = ds()
    if case_id not in d.entities or d.entities[case_id].entity_type.value != "exporter":
        raise HTTPException(404, "Case not found")


@app.on_event("startup")
def startup():
    load(DEFAULT_SEED)


@app.get("/health")
def health():
    d = ds()
    return {"status": "healthy", "entities": len(d.entities), "transactions": len(d.transactions),
            "dataset_version": d.version, "product": "Zeyro Trade Sentinel"}


@app.get("/cases")
def cases():
    return case_queue(ds())


@app.get("/cases/{case_id}")
def case_detail(case_id: str):
    require_exporter(case_id)
    return investigate(ds(), case_id, feedback)


@app.get("/cases/{case_id}/inputs")
def case_inputs(case_id: str):
    require_exporter(case_id)
    return input_trace(ds(), case_id)


@app.get("/entities/{entity_id}/context")
def context(entity_id: str, case: str):
    d = ds()
    if entity_id not in d.entities:
        raise HTTPException(404, "Entity not found")
    require_exporter(case)
    return entity_context(d, entity_id, case)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    case_id: str
    step: int
    mode: Literal["narrate", "ask"] = "narrate"
    message: Optional[str] = None
    history: List[ChatMessage] = []


@app.post("/chat")
def chat(req: ChatRequest):
    require_exporter(req.case_id)
    d = ds()
    inv = investigate(d, req.case_id, feedback)
    steps = inv["steps"]
    if not 0 <= req.step < len(steps):
        raise HTTPException(400, "Invalid step")
    if req.mode == "narrate":
        return {**agent.narrate(d.version, inv["case"], steps, req.step), "step": req.step}
    if not req.message or not req.message.strip():
        raise HTTPException(400, "Message required")
    out = agent.answer(d.version, inv["case"], steps, req.step, req.message, [m.model_dump() for m in req.history])
    return {**out, "step": out["goto"]}


class FeedbackRequest(BaseModel):
    case_id: str
    verdict: Literal["confirm", "dismiss", "escalate"]


@app.post("/feedback")
def post_feedback(req: FeedbackRequest):
    require_exporter(req.case_id)
    ev = ds().evidence[req.case_id]
    feedback[req.case_id] = {"verdict": req.verdict, "patterns": ev.matched_patterns, "at": time.time()}
    return {"ok": True, "case_id": req.case_id, "verdict": req.verdict}


@app.get("/feedback")
def get_feedback():
    return {cid: f["verdict"] for cid, f in feedback.items()}


@app.post("/regenerate")
def regenerate(seed: Optional[int] = None):
    """Reshuffle the random background companies. Scripted scenarios stay, all scores are recomputed."""
    load(seed if seed is not None else random.randint(1, 100000))
    return {"seed": state["seed"], "dataset_version": state["version"]}


@app.post("/reset")
def reset():
    load(DEFAULT_SEED)
    return {"seed": DEFAULT_SEED, "dataset_version": state["version"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
