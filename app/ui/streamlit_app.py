from __future__ import annotations

import time
import requests
import streamlit as st
from typing import Dict, Any, List


# -----------------------------
# CONFIG
# -----------------------------
API_BASE = "http://127.0.0.1:8000"
HEALTH_ENDPOINT = "/api/health"
TEXT2SQL_ENDPOINT = "/api/text2sql"


# -----------------------------
# PAGE SETUP (MUST BE FIRST)
# -----------------------------
st.set_page_config(
    page_title="GARV Text2SQL",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# GLOBAL CSS (DO NOT MOVE)
# -----------------------------
st.markdown(
    """
<style>
/* Remove Streamlit padding */
.block-container {
    padding-top: 0 !important;
    max-width: 1300px;
}

/* Hide Streamlit default header */
header[data-testid="stHeader"] {
    display: none;
}

/* ===== TOP HEADER ===== */
.top-header {
    position: sticky;
    top: 0;
    z-index: 9999;
    background: #0e1117;
    border-bottom: 1px solid #2a2e36;
    padding: 12px 24px;
}

.top-header-inner {
    max-width: 1300px;
    margin: auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Branding */
.brand {
    display: flex;
    align-items: center;
    gap: 14px;
}

.logo {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 14px;
    border: 1px solid #2a2e36;
}

.logo.client { background: #1f2937; }
.logo.garv { background: #0ea5e9; color: black; }

.brand-text {
    display: flex;
    flex-direction: column;
}

.brand-title {
    font-size: 18px;
    font-weight: 800;
}

.brand-sub {
    font-size: 12px;
    color: #9ca3af;
}

/* Status pills */
.status-bar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.pill {
    border: 1px solid #2a2e36;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
}
.dot.green { background: #22c55e; }
.dot.red { background: #ef4444; }

/* Chat container */
.chat-container {
    max-width: 900px;
    margin: auto;
    padding-top: 16px;
}
</style>
""",
    unsafe_allow_html=True,
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
# HEADER (SAFE HTML)
# -----------------------------
connected = is_api_alive()

# st.markdown(
#     f"""
# <div class="top-header">
#   <div class="top-header-inner">
#     <div class="brand">
#       <div class="logo client">CL</div>
#       <div class="logo garv">GARV</div>
#       <div class="brand-text">
#         <div class="brand-title">GARV Text2SQL</div>
#         <div class="brand-sub">Enterprise conversational SQL for airport operations</div>
#       </div>
#     </div>

#     # <div class="status-bar">
#     #   <div class="pill">
#     #     <span class="dot {'green' if connected else 'red'}"></span>
#     #     {'Connected' if connected else 'Offline'}
#     #   </div>
#     #   <div class="pill">DuckDB</div>
#     #   <div class="pill">Ollama · qwen2.5:7b</div>
#     #   <div class="pill">API 127.0.0.1:8000</div>
#     # </div>
#   </div>
# </div>
# """,
#     unsafe_allow_html=True,
# )


# -----------------------------
# SESSION STATE
# -----------------------------
if "chats" not in st.session_state:
    st.session_state.chats = []
if "active_chat" not in st.session_state:
    st.session_state.active_chat = None


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

    if st.button("+ New chat", use_container_width=True):
        new_chat()

    st.divider()

    for c in st.session_state.chats:
        if st.button(c["title"], use_container_width=True):
            st.session_state.active_chat = c["id"]

    st.caption("Keep FastAPI running on 127.0.0.1:8000")


# -----------------------------
# CHAT UI
# -----------------------------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

chat = get_chat()

for m in chat["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Ask a question… e.g. Top 5 airports by avg security wait time last 7 days")

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
                    json={"question": prompt},
                    timeout=120,
                )
                out = r.json()

                if out.get("ok"):
                    answer = (
                        f"{out['explanation']['summary']}\n\n"
                        f"**SQL**\n```sql\n{out['final_sql']}\n```\n\n"
                        f"**Preview**\n{out['preview_markdown']}"
                    )
                else:
                    answer = f"❌ Error: {out.get('message')}"

            except Exception as e:
                answer = f"❌ API error: {e}"

        st.markdown(answer)
        chat["messages"].append({"role": "assistant", "content": answer})

st.markdown("</div>", unsafe_allow_html=True)