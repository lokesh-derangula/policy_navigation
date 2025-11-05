import streamlit as st
import requests
import json
from PIL import Image
import pytesseract
import base64
import os
import io

OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "phi3:mini"

st.set_page_config(page_title="AI Chat + OCR + Document Assistant", layout="wide")

# -------------------------------------------------
# CSS + Animation Styles
# -------------------------------------------------
st.markdown("""
    <style>
        /* ===== General Page Style ===== */
        h1 { font-size: 2.5rem !important; }
        body { background-color: #f5f7fa; }

        .main-title {
            text-align: center;
            font-size: 2.4rem !important;
            font-weight: 700;
            color: #222;
            margin-bottom: 8px;
        }
        .subtitle {
            text-align: center;
            font-size: 1.05rem;
            color: #666;
            margin-bottom: 25px;
        }

        /* ===== Chat Bubbles ===== */
        .chat-bubble-user {
            background: #e8f0fe;
            border: 1.5px solid #4a90e2;
            border-radius: 12px;
            padding: 0.8rem;
            margin: 0.4rem 0;
            color: #0d47a1;
            width: fit-content;
            max-width: 80%;
        }
        .chat-bubble-ai {
            background: #f1f8e9;
            border: 1.5px solid #8bc34a;
            border-radius: 12px;
            padding: 0.8rem;
            margin: 0.4rem 0;
            color: #33691e;
            width: fit-content;
            max-width: 80%;
        }

        /* ===== Buttons ===== */
        .stButton>button {
            background-color: #4a90e2;
            color: white;
            border-radius: 8px;
            font-weight: bold;
            border: none;
            transition: 0.3s;
        }
        .stButton>button:hover {
            background-color: #357ABD;
        }

        /* ===== File Uploader Styling ===== */
        [data-testid="stFileUploader"] section div div span,
        [data-testid="stFileUploader"] label,
        [data-testid="stFileUploader"] button {
            display: none !important; /* hide 'Browse files' completely */
        }

        [data-testid='stFileUploaderDropzone'] {
            border: none !important;
            background: transparent !important;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-testid='stFileUploaderDropzone']:focus,
        [data-testid='stFileUploaderDropzone']:focus-visible,
        [data-testid='stFileUploaderDropzone']:active {
            outline: none !important;
            box-shadow: none !important;
        }

        [data-testid='stFileUploaderDropzoneInstructions'] {
            display: none !important;
        }

        div[data-testid="stFileUploader"] {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 17px;
        }

        /* === Compact Upload Arrow === */
        [data-testid="stFileUploaderDropzone"]::before {
            content: "⬆️";
            font-size: 1.6rem;
            color: white;
            background-color: #4a90e2;
            border-radius: 50%;
            padding: 10px;
            display: inline-block;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 0 8px rgba(74,144,226,0.5);
        }
        [data-testid="stFileUploaderDropzone"]:hover::before {
            background-color: #357ABD;
            transform: scale(1.1);
            box-shadow: 0 0 15px rgba(74,144,226,0.8);
        }

        /* === Uploaded File Icon === */
        .upload-icon-wrapper {
            text-align: center;
            margin-top: 12px;
            transition: all 0.3s ease;
        }
        .upload-icon {
            font-size: 2.4rem;
            color: #4a90e2;
            animation: pulseGlow 1.5s infinite;
        }
        @keyframes pulseGlow {
            0% { text-shadow: 0 0 5px rgba(74,144,226,0.4); }
            50% { text-shadow: 0 0 12px rgba(74,144,226,0.8); }
            100% { text-shadow: 0 0 5px rgba(74,144,226,0.4); }
        }
        .file-name {
            font-size: 0.85rem;
            color: #333;
            margin-top: 4px;
            word-break: break-word;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Header
# -------------------------------------------------
st.markdown("<div class='main-title'>🤖 Hello Lokesh..How can I help you today?</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Personal Chatbot with AI, OCR, and Document Analysis</div>", unsafe_allow_html=True)

# -------------------------------------------------
# Session setup
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {"Current Chat": []}

messages = st.session_state.messages

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings & History")
    MODEL_NAME = st.text_input("Model Name", MODEL_NAME)

    if st.button("🆕 New Chat"):
        if messages:
            st.session_state.chat_history[f"Chat {len(st.session_state.chat_history)}"] = messages.copy()
        st.session_state.messages = []
        st.session_state.chat_history["Current Chat"] = []
        st.success("Started a new chat!")

    if st.button("🧹 Clear All History"):
        st.session_state.clear()
        st.success("Chat history cleared!")

    st.markdown("---")
    st.subheader("💬 Chat History")
    for chat_name, chat_data in st.session_state.chat_history.items():
        if chat_name == "Current Chat":
            st.markdown(f"**🟢 {chat_name}**")
        else:
            if st.button(chat_name):
                st.session_state.messages = chat_data.copy()
                st.success(f"Loaded {chat_name}")
        if chat_data:
            for msg in chat_data[-3:]:
                emoji = "🧑" if msg["role"] == "user" else "🤖"
                preview = msg["content"][:40] + ("..." if len(msg["content"]) > 40 else "")
                st.markdown(f"{emoji} {preview}")

# -------------------------------------------------
# Chat display
# -------------------------------------------------
st.markdown("### 💬 Conversation")
for msg in messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'><b>You:</b><br>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble-ai'><b>AI:</b><br>{msg['content']}</div>", unsafe_allow_html=True)

# -------------------------------------------------
# Input + Upload section
# -------------------------------------------------
col1, col2 = st.columns([10, 1])
with col1:
    user_input = st.text_area("Type your message:", key="user_input", height=80)
with col2:
    uploaded_file = st.file_uploader("", type=["png", "jpg", "jpeg", "pdf", "txt", "docx"], label_visibility="collapsed")

# File icon + filename preview
if uploaded_file is not None:
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    icon = "📄" if file_ext not in [".png", ".jpg", ".jpeg"] else "🖼️"
    st.markdown(f"""
        <div class='upload-icon-wrapper'>
            <div class='upload-icon'>{icon}</div>
            <div class='file-name'>{uploaded_file.name}</div>
        </div>
    """, unsafe_allow_html=True)

send_button = st.button("➤")

# -------------------------------------------------
# Main chat logic (context-aware document analysis)
# -------------------------------------------------
if send_button and (user_input.strip() or uploaded_file is not None):
    combined_prompt = user_input.strip()
    doc_context = ""

    if uploaded_file is not None:
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center; margin-top:10px; margin-bottom:10px;">
                <img src="data:image/png;base64,{base64.b64encode(uploaded_file.getvalue()).decode()}" 
                     alt="Uploaded Image" width="300" style="border-radius:10px; border:1px solid #ccc;">
            </div>
            """,
            unsafe_allow_html=True
        )

        # OCR for images
        if file_ext in [".png", ".jpg", ".jpeg"]:
            image = Image.open(uploaded_file)
            with st.spinner("Extracting text from image..."):
                ocr_text = pytesseract.image_to_string(image)
            if ocr_text.strip():
                doc_context = ocr_text.strip()

        # Text extraction for docs
        elif file_ext in [".pdf", ".txt", ".docx"]:
            with st.spinner("Extracting and analyzing document..."):
                text_content = ""
                if file_ext == ".txt":
                    text_content = uploaded_file.read().decode("utf-8")
                elif file_ext == ".pdf":
                    from PyPDF2 import PdfReader
                    pdf = PdfReader(uploaded_file)
                    text_content = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
                elif file_ext == ".docx":
                    from docx import Document
                    doc = Document(uploaded_file)
                    text_content = "\n".join([para.text for para in doc.paragraphs])
                doc_context = text_content.strip()

    # Intelligent prompt
    if doc_context:
        system_prompt = (
            "You are a helpful AI assistant that analyzes the provided document text "
            "and answers user questions strictly based on its content. "
            "If the question asks for a summary or explanation, provide a clear, concise, and structured answer."
        )
        combined_prompt = f"{system_prompt}\n\nUser query: {user_input.strip()}\n\nDocument content:\n{doc_context[:6000]}"

    # Add messages
    messages.append({"role": "user", "content": combined_prompt})
    st.session_state.chat_history["Current Chat"].append({"role": "user", "content": combined_prompt})

    payload = {"model": MODEL_NAME, "messages": messages, "stream": True}

    with st.spinner("AI is thinking..."):
        full_reply = ""
        try:
            resp = requests.post(OLLAMA_API_URL, json=payload, stream=True, timeout=600)
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                try:
                    line = raw_line.decode("utf-8").strip()
                    if line.startswith("data:"):
                        line = line[len("data:"):].strip()
                    data = json.loads(line)
                except Exception:
                    continue
                token = data.get("message", {}).get("content", "")
                if token:
                    full_reply += token
                if data.get("done") or data.get("type") == "response-complete":
                    break

            st.markdown(f"<div class='chat-bubble-ai'><b>AI:</b><br>{full_reply}</div>", unsafe_allow_html=True)
            messages.append({"role": "assistant", "content": full_reply})
            st.session_state.chat_history["Current Chat"].append({"role": "assistant", "content": full_reply})

        except requests.exceptions.RequestException as e:
            err = f"⚠️ Error connecting to Ollama: {e}"
            st.markdown(f"<div class='chat-bubble-ai'>{err}</div>", unsafe_allow_html=True)
            messages.append({"role": "assistant", "content": err})
            st.session_state.chat_history["Current Chat"].append({"role": "assistant", "content": err})
