"""
FastAPI bridge connecting Stitch UI (code.html) to the backend agent.

Strict Requirements Compliance:
- Access document content ONLY through the four mandatory tools:
  * list_documents()
  * list_headings(doc_id)
  * get_page(doc_id, page_number)
  * search_keyword(doc_id, keyword)
- NO additional document tools.
- Budget: MAXIMUM 6 document-tool calls PER QUESTION.
- Fresh 6-call budget for every question.
- No global/session budget restriction.
- Real-time SSE streaming for live tool-call trace updates.
"""

import os
import json
import tempfile
import hashlib
import asyncio
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from agent import agent_answer


def _sse(event_type: str, payload: dict) -> str:
    """Format a single SSE event line."""
    data = json.dumps({"type": event_type, **payload}, ensure_ascii=False)
    return f"data: {data}\n\n"


app = FastAPI(title="Budgeted Doc Agent - Stitch Bridge")

os.makedirs("logs", exist_ok=True)

# Active document cache (stores temporary path by hash to avoid unnecessary rewrites)
ACTIVE_DOC = {
    "hash": None,
    "path": None,
}
SESSION_STATE = ACTIVE_DOC


@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists("code.html"):
        with open("code.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>code.html not found in project root</h1>"


def get_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@app.get("/api/budget")
def get_budget():
    """Returns the standard fresh budget specification: 6 calls max per question."""
    return {
        "calls_used": 0,
        "calls_remaining": 6
    }


@app.get("/api/docs/{doc_type}")
def get_doc(doc_type: str):
    doc_map = {
        "benchmark": ("Benchmark Evaluation Report", "BENCHMARK.md"),
        "documentation": ("System Architecture & Documentation", "DOCUMENTATION.md"),
        "memo": ("Engineering Design Memo", "memo.md"),
    }
    if doc_type not in doc_map:
        raise HTTPException(status_code=404, detail="Document not found")
    title, filename = doc_map[doc_type]
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    return {"title": title, "content": content}



@app.post("/api/ask")
async def ask_question(
    file: UploadFile = File(...),
    question: str = Form(...)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    content = await file.read()
    new_hash = get_file_hash(content)

    # Manage active document file handle
    if ACTIVE_DOC["hash"] != new_hash or not ACTIVE_DOC["path"] or not os.path.exists(ACTIVE_DOC["path"]):
        if ACTIVE_DOC["path"] and os.path.exists(ACTIVE_DOC["path"]):
            try:
                os.unlink(ACTIVE_DOC["path"])
            except Exception:
                pass

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            ACTIVE_DOC["path"] = tmp.name
        ACTIVE_DOC["hash"] = new_hash

    doc_path = ACTIVE_DOC["path"]

    # Each question gets its own fresh trace log and its own fresh 6-call budget
    question_hash = hashlib.md5(question.strip().encode("utf-8")).hexdigest()[:8]
    log_path = os.path.join("logs", f"trace_{question_hash}.jsonl")
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except Exception:
            pass

    try:
        # Use simulated LLM if requested via environment (for offline harness/UI testing)
        llm_func = None
        if os.environ.get("USE_SIMULATED_LLM", "").strip().lower() in ("1", "true", "yes"):
            from tests import SimulatedLLM
            llm_func = SimulatedLLM()

        # Run agent for this question (budget resets to 6 in agent_answer/BudgetedTools)
        result = agent_answer(question.strip(), doc_path, log_path, llm_func=llm_func)

        # Read trace records for this question
        trace_records = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        trace_records.append(json.loads(line))

        calls_used = len(trace_records)
        result["trace"] = trace_records
        result["calls_used"] = calls_used
        result["calls_remaining"] = max(0, 6 - calls_used)

        # Build SSE stream: yield each actual executed tool call record, then final_result
        async def event_generator():
            for record in trace_records:
                yield _sse("tool_call", {"record": record})
                await asyncio.sleep(0.06)
            yield _sse("final_result", {"result": result})

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    except Exception as e:
        err_result = {
            "status": "INSUFFICIENT",
            "answer": f"Error: {str(e)}",
            "citations": [],
            "conflict_note": None,
            "trace": [],
            "calls_used": 0,
            "calls_remaining": 6
        }
        body = _sse("error", {"detail": str(e)}) + _sse("final_result", {"result": err_result})
        return StreamingResponse(
            iter([body]),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
