import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Clinical Text-to-SQL", page_icon="🩺", layout="wide")
st.title("🩺 Clinical Text-to-SQL Agent")
st.caption(
    "Ask questions about synthetic patient records (Synthea). Read-only; SQL is always shown."
)

with st.sidebar:
    model = st.text_input("Model override (optional)", "")
    st.markdown("**Examples**")
    examples = [
        "How many female patients are older than 60?",
        "What are the 5 most common conditions?",
        "Average total claim cost of emergency encounters?",
        "How many patients have an active diabetes diagnosis?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["q"] = ex

question = st.text_input(
    "Question", key="q", placeholder="e.g. How many patients had an emergency visit in 2024?"
)

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Thinking..."):
        try:
            r = requests.post(
                f"{API_URL}/ask",
                json={"question": question, "model": model or None},
                timeout=300,
            )
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            st.error(f"Could not reach the API at {API_URL}: {e}")
            st.stop()

    if data.get("refused"):
        st.warning(
            data.get("answer") or "I can only answer data questions, not give medical advice."
        )
    else:
        if data.get("error"):
            st.error(data["error"])
        if data.get("answer"):
            st.success(data["answer"])
        if data.get("sql"):
            st.subheader("SQL")
            st.code(data["sql"], language="sql")
        if data.get("rows"):
            st.subheader(f"Result ({len(data['rows'])} rows)")
            st.dataframe(
                pd.DataFrame(data["rows"], columns=data["columns"]), use_container_width=True
            )
    with st.expander("Agent trace"):
        st.json(data.get("trace", []))
