"""Streamlit UI.  Run:  uv run streamlit run app.py   (opens http://localhost:8501)"""

import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def error_message(response: requests.Response) -> str:
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text


st.set_page_config(page_title="Medical Diagnostics Support", page_icon="🩺")
st.title("🩺 Medical Diagnostics Support")
st.caption("Upload medical documents, then ask questions about them.")

# ---- Sidebar: upload documents ----
with st.sidebar:
    st.header("1. Upload documents")
    files = st.file_uploader("PDF or TXT files", type=["pdf", "txt"], accept_multiple_files=True)

    if st.button("Upload", disabled=not files, width="stretch"):
        for file in files:
            with st.spinner(f"Processing {file.name}..."):
                response = requests.post(
                    f"{BACKEND_URL}/upload",
                    files={"file": (file.name, file.getvalue())},
                    timeout=300,
                )
            if response.ok:
                st.success(f"{file.name}: {response.json()['chunks']} chunks added")
            else:
                st.error(f"{file.name}: {error_message(response)}")

# ---- Main area: chat ----
st.header("2. Ask a question")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question := st.chat_input("e.g. What are the symptoms of type 2 diabetes?"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = requests.post(f"{BACKEND_URL}/query", json={"question": question}, timeout=120)

        if response.ok:
            result = response.json()
            answer = result["answer"]
            st.markdown(answer)
            with st.expander("Sources"):
                for source in result["sources"]:
                    page = f" (page {source['page']})" if source["page"] else ""
                    st.markdown(f"**{source['source']}{page}**")
                    st.caption(source["text"])
        else:
            answer = f"Error: {error_message(response)}"
            st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
