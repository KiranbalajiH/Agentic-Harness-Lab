# Executive Memo: Budgeted Document-Answering Agent

---

## 1. Problem & Core Architecture

The system answers user questions about uploaded PDF documents under a strict constraint of **maximum 6 document-tool calls per question**. 

The architecture consists of a single procedural controller loop (`agent.py`) that interacts with documents solely through four restricted tools (`list_documents`, `list_headings`, `get_page`, `search_keyword`) defined in `tools.py`. All document-tool calls pass through a central `BudgetedTools` wrapper (`budget.py`) that enforces the 6-call cap in code and writes an audit record for every invocation to a JSONL trace log.

---

## 2. Core Design Principle & Strategy

> **"Under a hard 6-call document-access budget, the agent prioritizes targeted evidence retrieval and abstention over exhaustive retrieval or guessing."**

- **Enforced Budget:** Capped at 6 document-tool calls per question. The budget resets for every new question; final answer synthesis does not consume document-tool calls.
- **Evidence & Grounding:** The agent retrieves text via targeted keyword searches and physical page reads. Every citation quote is verified against raw page content.
- **LLM Self-Critique & Evidence Review:** Independent reviewing LLM audits the candidate draft against retrieved evidence and evaluates 7 critical criteria, issuing structured decisions (`ACCEPT`, `REVISE`, `MORE_EVIDENCE`, `ABSTAIN`) in a bounded revision loop.
- **Contradiction & Supersession:** Inspects text for revision keywords (`supersedes`, `revised`, `errata`), documenting updates in a structured `conflict_note`.
- **Prompt-Injection Defense:** PDF text is treated strictly as data in sandboxed buffers, preventing embedded malicious instructions from overriding system behavior.
- **Abstention Policy:** If evidence is missing or quote verification fails, the agent abstains with `"Insufficient information"` rather than hallucinating.

---

## 3. Benchmark Summary

The implementation was validated across all 9 required functional categories in `BENCHMARK.md`:

| Benchmark Category | Result | Key Observation |
|---|---|---|
| **1. Normal Factual** | **PASS** | Answered from Page 1 with verified citation quote. |
| **2. Multi-Page Reasoning** | **PASS** | Combined evidence from Pages 2 and 4 within 6 calls. |
| **3. Contradiction / Supersession** | **PASS** | Identified Page 9 supersession statement over Page 5. |
| **4. Insufficient Information** | **PASS** | Abstained cleanly with zero hallucinated text. |
| **5. Prompt Injection Defense** | **PASS** | Ignored Page 6 prompt redirection attack. |
| **6. Tool Budget Cap** | **PASS** | Stress query capped at 6 calls; 7th call blocked. |
| **7. Consecutive Questions** | **PASS** | Each question received a fresh 6-call budget. |
| **8. PDF Replacement** | **PASS** | Active PDF context switched cleanly without leakage. |
| **9. Unseen Document** | **PASS** | Successfully parsed and answered unconfigured PDF. |

---

## 4. Known Limitations

1. **Exact Keyword Phrasing:** Questions using synonyms not present in the PDF text may result in abstention (`INSUFFICIENT`).
2. **Complex Layout Parsing:** Plain-text PyMuPDF extraction may scramble multi-column tables.
3. **Exploration Cap:** Highly complex inquiries requiring $>6$ distinct page reads trigger an early budget-stop.
