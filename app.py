import streamlit as st
import os
import zipfile
import tempfile
import io
from pathlib import Path
from PIL import Image

from google import genai
from file_processor import (
    build_codebase_context,
    build_directory_tree,
    get_file_type_summary,
)

# ─────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAP Codebase Chat",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# Session-state defaults
# ─────────────────────────────────────────────────────────────────
for key in ["codebase_context", "directory_tree", "file_summary",
            "image_files", "chat_history", "system_prompt"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state.chat_history is None:
    st.session_state.chat_history = []

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────
def build_system_prompt(codebase_context: str) -> str:
    return f"""You are an expert SAP Integration Advisor and senior software architect.
You have been given FULL access to a SAP project codebase. Your job is to help
developers deeply understand, navigate, analyse, and improve this codebase.

Your expertise covers:
  • SAP Integration Suite / Cloud Integration (CPI / iFlow)
  • iFlow files (.iflw) — BPMN-based XML integration flows
  • Groovy scripts used in SAP CPI message processors
  • SAP adapter configuration (SFTP, KAFKA, SOAP, REST, JDBC, …)
  • Exception handling patterns (dead-letter, retry, circuit-breaker)
  • Property / parameter / propdef files
  • MANIFEST.MF and project metadata
  • Kafka, ECC, S/4HANA integration patterns

When answering:
  1. Reference specific file paths and relevant code sections.
  2. Explain SAP-specific concepts clearly for the audience level inferred from the question.
  3. Map out the data flow / integration flow end-to-end when asked.
  4. Proactively flag potential issues, anti-patterns, or improvements.
  5. If given an image, analyse it in the context of this codebase (e.g. a screenshot of an error, a flow diagram, etc.).
  6. Keep answers structured with headers, bullet points, and code blocks.

═══════════════════════  CODEBASE  ═══════════════════════
{codebase_context}
══════════════════════════════════════════════════════════
"""


def load_project(root_path: str):
    """Read the project and store everything in session state."""
    with st.spinner("🔍 Reading files and building codebase context …"):
        context, image_files = build_codebase_context(root_path)
        tree = build_directory_tree(root_path)
        summary = get_file_type_summary(root_path)

    st.session_state.codebase_context = context
    st.session_state.image_files = image_files
    st.session_state.directory_tree = tree
    st.session_state.file_summary = summary
    st.session_state.chat_history = []
    st.session_state.system_prompt = build_system_prompt(context)

    char_count = len(context)
    token_est = char_count // 4
    return char_count, token_est


def get_gemini_response(api_key: str, prompt: str, image_bytes: bytes | None) -> str:
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Rebuild conversation history (excluding last user message)
    history = []
    for msg in st.session_state.chat_history[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        parts = []
        if msg.get("image_bytes"):
            parts.append(
                types.Part.from_bytes(
                    data=msg["image_bytes"],
                    mime_type="image/jpeg"
                )
            )
        parts.append(types.Part.from_text(text=msg["content"]))
        history.append(types.Content(role=role, parts=parts))

    chat = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=st.session_state.system_prompt
        ),
        history=history,
    )

    # Current message
    if image_bytes:
        message = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            types.Part.from_text(text=prompt),
        ]
    else:
        message = prompt

    response = chat.send_message(message=message)
    return response.text

# ─────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 SAP Codebase Chat")
    st.caption("Powered by Google Gemini")

    st.divider()
    st.header("⚙️ API Key")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=os.environ.get("GEMINI_API_KEY", ""),
        help="Get yours at https://aistudio.google.com/app/apikey",
    )

    st.divider()
    st.header("📁 Load SAP Project")
    input_method = st.radio(
        "Input method",
        ["Upload ZIP File", "Local Folder Path"],
    )

    if input_method == "Upload ZIP File":
        uploaded_zip = st.file_uploader(
            "Upload your project as a ZIP",
            type=["zip"],
        )
        if uploaded_zip and st.button("🚀 Load Project", type="primary"):
            tmpdir = tempfile.mkdtemp()
            zip_path = os.path.join(tmpdir, "project.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_zip.read())
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)
            os.remove(zip_path)
            chars, tokens = load_project(tmpdir)
            st.success(f"✅ Loaded! ~{tokens:,} tokens of context.")

    else:
        folder_path = st.text_input(
            "Absolute path to unzipped project",
            placeholder="/Users/you/ESA_Exception_Handling",
        )
        if folder_path and st.button("🚀 Load Project", type="primary"):
            if os.path.isdir(folder_path):
                chars, tokens = load_project(folder_path)
                st.success(f"✅ Loaded! ~{tokens:,} tokens of context.")
            else:
                st.error("Folder not found. Please check the path.")

    # Directory tree & stats
    if st.session_state.directory_tree:
        st.divider()
        st.header("📂 Directory Tree")
        st.code(st.session_state.directory_tree, language=None)

        if st.session_state.file_summary:
            st.header("📊 File Types")
            for ext, count in sorted(st.session_state.file_summary.items()):
                st.text(f"  {ext or '(no ext)':15s} {count:>3} file(s)")

        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

# ─────────────────────────────────────────────────────────────────
# Main — Chat Interface
# ─────────────────────────────────────────────────────────────────
st.title("💬 Chat with your SAP Codebase")

if not st.session_state.codebase_context:
    st.info(
        "👈 **Step 1** – Enter your Gemini API key.\n\n"
        "👈 **Step 2** – Upload a ZIP or enter a folder path, then click **Load Project**.\n\n"
        "Once loaded you can ask anything about the codebase here."
    )
    st.stop()

if not api_key:
    st.warning("⚠️ Please enter your Gemini API key in the sidebar.")
    st.stop()

# Render existing messages
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("image_bytes"):
            st.image(msg["image_bytes"], width=400)

# Image attachment (above the input bar)
attached_image = st.file_uploader(
    "📎 Attach an image to your next message (optional)",
    type=["png", "jpg", "jpeg", "gif", "webp"],
    label_visibility="visible",
    key="img_uploader",
)

# Chat input
if prompt := st.chat_input("Ask about the codebase…  e.g. 'Explain the overall integration flow'"):
    img_bytes = attached_image.read() if attached_image else None

    # Record user message
    user_msg = {"role": "user", "content": prompt, "image_bytes": img_bytes}
    st.session_state.chat_history.append(user_msg)

    with st.chat_message("user"):
        st.markdown(prompt)
        if img_bytes:
            st.image(img_bytes, width=400)

    # Generate and display response
    with st.chat_message("assistant"):
        with st.spinner("Thinking …"):
            try:
                answer = get_gemini_response(api_key, prompt, img_bytes)
                st.markdown(answer)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": answer}
                )
            except Exception as exc:
                err = f"❌ Gemini API error: {exc}"
                st.error(err)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": err}
                )
