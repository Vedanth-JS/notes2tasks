from fastapi import FastAPI
from pydantic import BaseModel
from src.orchestrator import run_pipeline, RunConfig

app = FastAPI(title="Meeting Notes Extractor API")

class TranscriptRequest(BaseModel):
    transcript: str

@app.post("/extract")
def extract_action_items(req: TranscriptRequest):
    config = RunConfig(seed=42)
    result = run_pipeline(req.transcript, config)
    return {"items": [item.model_dump() for item in result.items]}

@app.get("/health")
def health_check():
    return {"status": "ok"}
