from __future__ import annotations

import time
import requests
import streamlit as st
from typing import Dict, Any


# -----------------------------
# CONFIG
# -----------------------------
API_BASE = "http://127.0.0.1:8000"
HEALTH_ENDPOINT = "/api/health"
TEXT2SQL_ENDPOINT = "/api/text2sql"


# -----------------------------
# PAGE SETUP
# -----------------------------
st.set_page_config(
    page_title="GARV Text2SQL",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# HEALTH CHECK
# -----------------------------
def is_api_alive() -> bool:
    try:
        r = requests.get(API_BASE + HEALTH_ENDPOINT, timeout=1)
        return r.status_code == 200
    except Exception:
        return False


# -----------------------------
# SESSION STATE
# -----------------------------
if "chats" not in st.session_state:
    st.session_state.chats = []
if "active_chat" not in st.session_state:
    st.session_state.active_chat = None
if "persona" not in st.session_state:
    st.session_state.persona = "analyst"


def new_chat():
    cid = f"chat-{int(time.time()*1000)}"
    st.session_state.chats.insert(
        0,
        {
            "id": cid,
            "title": "New chat",
            "messages": [
                {
                    "role": "assistant",
                    "content": "Hi! Ask me an airport ops question and I’ll generate SQL + results."
                }
            ],
        },
    )
    st.session_state.active_chat = cid


def get_chat():
    if not st.session_state.active_chat:
        new_chat()
    for c in st.session_state.chats:
        if c["id"] == st.session_state.active_chat:
            return c
    new_chat()
    return get_chat()


# -----------------------------
# SIDEBAR
# -----------------------------
with st.sidebar:
    st.title("GARV Text2SQL")

    st.session_state.persona = st.selectbox(
        "Persona",
        options=["executive", "ops_manager", "analyst"],
        index=["executive", "ops_manager", "analyst"].index(st.session_state.persona),
        help="Controls RBAC, depth of analysis, and visualization"
    )

    if st.button("+ New chat", use_container_width=True):
        new_chat()

    st.divider()

    for c in st.session_state.chats:
        if st.button(c["title"], use_container_width=True):
            st.session_state.active_chat = c["id"]

    st.divider()

    st.caption(
        f"API: {'🟢 Connected' if is_api_alive() else '🔴 Offline'}"
    )


# -----------------------------
# CHAT UI
# -----------------------------
chat = get_chat()

for m in chat["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input(
    "Ask a question… e.g. Top 5 airports by avg security wait time last 7 days"
)

if prompt:
    if chat["title"] == "New chat":
        chat["title"] = prompt[:30] + ("…" if len(prompt) > 30 else "")

    chat["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generating SQL and results…"):
            try:
                r = requests.post(
                    API_BASE + TEXT2SQL_ENDPOINT,
                    json={
                        "question": prompt,
                        "persona": st.session_state.persona,
                    },
                    timeout=120,
                )

                if r.status_code != 200:
                    raise RuntimeError(r.text)

                out: Dict[str, Any] = r.json()

                if not out.get("ok"):
                    answer = f"❌ {out.get('message', 'Unknown error')}"
                else:
                    explanation = out.get("explanation")
                    if isinstance(explanation, dict):
                        explanation_text = explanation.get("summary") or json.dumps(
                            explanation, indent=2
                        )
                    else:
                        explanation_text = explanation or ""

                    answer = f"""
                            {explanation_text}

                            **SQL**
                            ```sql
                            {out.get("final_sql", "")}
                            Preview
                            {out.get("preview_markdown", "No preview available")}
                            """
            except Exception as e:
                answer = f"❌ API error: {e}"

            st.markdown(answer)
            chat["messages"].append({"role": "assistant", "content": answer})