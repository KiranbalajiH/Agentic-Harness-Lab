"""BudgetedTools wrapper: cap, logging, argument validation.

The agent never holds a reference to the raw tools. Every call routes through
here, so the budget is enforced in code, not in the prompts.
"""

import json
import os
import time
from datetime import datetime, timezone

MAX_TOOL_CALLS = 6


class BudgetExhausted(Exception):
    """Raised when the agent has used all of its tool-call budget."""


ALLOWED_TOOLS = {"list_documents", "list_headings", "get_page", "search_keyword"}


def _validate(tool, args, doc_path):
    """Argument allowlist. Doubles as an injection defense: page text cannot
    talk the agent into calling an unknown tool or a different doc_id."""
    if tool not in ALLOWED_TOOLS:
        raise ToolError(f"unknown tool: {tool!r}")

    if not isinstance(args, dict):
        raise ToolError("args must be a dict")

    if tool == "list_documents":
        if args:
            raise ToolError("list_documents takes no arguments")
        return

    if tool == "list_headings":
        if set(args.keys()) != {"doc_id"}:
            raise ToolError("list_headings requires exactly doc_id")
    elif tool == "get_page":
        if set(args.keys()) != {"doc_id", "page_number"}:
            raise ToolError("get_page requires doc_id and page_number")
        if not isinstance(args["page_number"], int) or args["page_number"] < 1:
            raise ToolError("page_number must be a positive integer")
    elif tool == "search_keyword":
        if set(args.keys()) != {"doc_id", "keyword"}:
            raise ToolError("search_keyword requires doc_id and keyword")
        if not isinstance(args["keyword"], str) or not args["keyword"].strip():
            raise ToolError("keyword must be a non-empty string")
        if len(args["keyword"]) > 200:
            raise ToolError("keyword too long")

    if args.get("doc_id") != doc_path:
        raise ToolError("doc_id does not match the uploaded document")


class ToolError(Exception):
    """A tool received bad input or the PDF could not be read."""


def _summarize(result):
    """A short, bounded summary of a tool result for the trace."""
    if result is None:
        return None
    if isinstance(result, list):
        return f"list[{len(result)}]"
    if isinstance(result, dict):
        return {k: v for k, v in result.items() if k != "text"}
    if isinstance(result, str):
        return result[:200]
    return str(result)[:200]


class BudgetedTools:
    """Wraps a tools object with a hard cap and a JSONL logger."""

    def __init__(self, tools, question, log_path):
        self.tools = tools
        self.question = question
        self.log_path = log_path
        self.used = 0

    @property
    def calls_remaining(self):
        return MAX_TOOL_CALLS - self.used

    def call(self, tool, args, purpose):
        if self.used >= MAX_TOOL_CALLS:
            raise BudgetExhausted(
                f"budget exhausted: {MAX_TOOL_CALLS} calls used"
            )
        _validate(tool, args, getattr(self.tools, "doc_path", args.get("doc_id")))

        self.used += 1  # count BEFORE executing, so failures count
        call_number = self.used
        start = time.time()
        result, err = None, None
        try:
            result = getattr(self.tools, tool)(**args)
        except Exception as e:
            result, err = None, str(e)

        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "question": self.question,
            "call_number": call_number,
            "tool": tool,
            "args": args,
            "purpose": purpose,
            "result_summary": _summarize(result),
            "error": err,
            "calls_used": self.used,
            "calls_remaining": MAX_TOOL_CALLS - self.used,
            "duration_ms": round((time.time() - start) * 1000),
        }
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return result, err