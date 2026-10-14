"""Minimal chat interface for the budgeted document-answering agent.

Requirements:
- PDF upload
- Question input
- Agent answer
- Tool-call trace (from logs/trace.jsonl)
"""

import streamlit as st
import os
import json
import tempfile
from agent import agent_answer

st.set_page_config(page_title="Budgeted Doc Agent", layout="wide")

st.title("Budgeted Document Agent")

# Sidebar for PDF upload
uploaded_file = st.sidebar.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        doc_path = tmp.name

    # Chat interface
    st.header("Chat")
    question = st.text_input("Ask a question about the document:")

    if st.button("Answer"):
        if not question:
            st.warning("Please enter a question.")
        else:
            # We need a log path for this session
            log_path = os.path.join("logs", "session_trace.jsonl")
            if os.path.exists(log_path):
                os.remove(log_path)

            with st.spinner("Agent is thinking..."):
                result = agent_answer(question, doc_path, log_path)

            trace_data = []
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            trace_data.append(json.loads(line))

            calls_used = len(trace_data)
            st.metric("Calls Used", f"{calls_used} / 6", f"{max(0, 6 - calls_used)} remaining")

            st.write("### Answer")
            st.write(result["answer"])

            st.write("### Status:", result["status"])

            if result.get("citations"):
                st.write("### Citations")
                for cite in result["citations"]:
                    st.info(f"Page {cite['page']}: '{cite['quote']}'")

            if result.get("conflict_note"):
                st.warning(f"Conflict Note: {result['conflict_note']}")

            # Trace panel
            st.header("Tool-Call Trace")
            if trace_data:
                st.table(trace_data)
            else:
                st.info("No tool calls recorded.")

    # Clean up temp file after a while (Streamlit reruns, this is basic)
    # st.sidebar.button("Clear session", on_click=lambda: os.remove(doc_path))
else:
    st.info("Please upload a PDF document in the sidebar to begin.")
