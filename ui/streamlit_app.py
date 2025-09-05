import os
import json
from typing import Optional

import requests
import streamlit as st


def get_api_base_url() -> str:
    # Allow overriding the FastAPI base URL via env var; default to local
    return os.getenv("API_BASE_URL", "http://localhost:8000")


def post_chat_message(message: str, user_id: str, api_base_url: str) -> dict:
    url = f"{api_base_url}/chat"
    headers = {"Content-Type": "application/json"}
    payload = {"message": message, "user_id": user_id}
    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    st.set_page_config(page_title="Agent Swarm UI", page_icon="🤖", layout="centered")
    st.title("Agent Swarm – Test UI")
    st.caption("Simple Streamlit interface for exercising the /chat endpoint")

    with st.sidebar:
        st.header("Settings")
        api_base_url = st.text_input("API Base URL", value=get_api_base_url(), help="FastAPI server base URL")
        default_user_id = st.text_input("Default User ID", value="tester001")
        st.markdown("""
        - Start the API server separately
        - Example: `uvicorn app.main:app --reload`
        """)

    if "history" not in st.session_state:
        st.session_state.history = []  # list[tuple[str, dict]] of (message, response)

    with st.form("chat_form", clear_on_submit=False):
        message = st.text_area("Message", placeholder="Ask something...", height=120)
        user_id = st.text_input("User ID", value=default_user_id)
        submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted:
        if not message.strip():
            st.warning("Please enter a message.")
        elif not user_id.strip():
            st.warning("Please provide a user id.")
        else:
            try:
                result = post_chat_message(message.strip(), user_id.strip(), api_base_url)
                st.session_state.history.append((message.strip(), result))
            except requests.HTTPError as http_err:
                st.error(f"HTTP error: {http_err}")
            except requests.RequestException as req_err:
                st.error(f"Request error: {req_err}")
            except Exception as ex:
                st.error(f"Unexpected error: {ex}")

    st.subheader("Responses")
    if not st.session_state.history:
        st.info("No messages yet. Submit your first message above.")
    else:
        for idx, (msg, resp) in enumerate(reversed(st.session_state.history), start=1):
            with st.expander(f"Message {len(st.session_state.history) - idx + 1}: {msg[:48]}{'...' if len(msg) > 48 else ''}", expanded=False):
                st.write("Request")
                st.code(json.dumps({"message": msg}, ensure_ascii=False, indent=2), language="json")
                st.write("Response")
                st.code(json.dumps(resp, ensure_ascii=False, indent=2), language="json")


if __name__ == "__main__":
    main()


