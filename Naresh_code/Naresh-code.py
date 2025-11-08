import streamlit as st
import time
import requests
import hashlib

BACKEND_CHAT = "http://127.0.0.1:8000/chat"
BACKEND_OCR = "http://127.0.0.1:8000/ocr"

st.set_page_config(page_title="Chat + OCR (Ollama)", layout="wide", page_icon="💬")

# -------------------- Session State --------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {"New Chat": []}
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "New Chat"
if "last_ocr_hash" not in st.session_state:
    st.session_state.last_ocr_hash = None

# -------------------- Sidebar --------------------
with st.sidebar:
    st.header("💬 Chat Sessions")
    for chat_name in list(st.session_state.chat_history.keys()):
        if st.button(chat_name, key=f"open_{chat_name}", use_container_width=True):
            st.session_state.active_chat = chat_name
            st.session_state.messages = st.session_state.chat_history[chat_name].copy()

    if st.button("➕ New Chat"):
        st.session_state.active_chat = "New Chat"
        st.session_state.messages = []
        st.session_state.chat_history["New Chat"] = []

    st.markdown("---")
    st.write("👤 User: **Naresh**")
    st.write("⚙️ Powered by: **Ollama + EasyOCR + Streamlit**")

# -------------------- Main Layout --------------------
st.title("💬 ChatGPT Clone + OCR (Image / PDF / Word Supported)")

# Display Chat
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# -------------------- OCR Upload --------------------
st.markdown("### 📎 Upload Image, PDF, or Word File for OCR + AI Summary")
ocr_file = st.file_uploader(
    "Upload File",
    type=["jpg", "jpeg", "png", "pdf", "docx"],
    label_visibility="collapsed"
)

if ocr_file:
    file_bytes = ocr_file.read()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    if file_hash != st.session_state.last_ocr_hash:
        st.session_state.last_ocr_hash = file_hash
        with st.spinner("🧠 Extracting text and generating summary..."):
            try:
                files = {"file": (ocr_file.name, file_bytes, ocr_file.type)}
                resp = requests.post(BACKEND_OCR, files=files, timeout=120)

                if resp.status_code == 200:
                    data = resp.json()
                    extracted_text = data.get("extracted_text", "")
                    ai_summary = data.get("ai_summary", "")

                    if extracted_text:
                        st.success("✅ Text extracted successfully!")

                        # Add OCR result to chat
                        st.session_state.messages.append({
                            "role": "user",
                            "content": f"📄 **Extracted Text:**\n\n{extracted_text}"
                        })

                        # Add AI summary automatically
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"🤖 **AI Summary:**\n\n{ai_summary}"
                        })

                        st.session_state.chat_history[st.session_state.active_chat] = st.session_state.messages.copy()
                        st.rerun()
                    else:
                        st.warning("⚠️ No text found in file.")
                else:
                    st.error(f"OCR Error: {resp.status_code} {resp.text}")
            except Exception as e:
                st.error(f"OCR request failed: {e}")

# -------------------- Chat Input --------------------
prompt = st.chat_input("Type your message...")

if prompt:
    if st.session_state.active_chat == "New Chat":
        short_title = " ".join(prompt.split()[:5])
        base = short_title
        suffix = 1
        while short_title in st.session_state.chat_history:
            short_title = f"{base}_{suffix}"
            suffix += 1
        st.session_state.chat_history[short_title] = st.session_state.chat_history.pop("New Chat")
        st.session_state.active_chat = short_title

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        resp = requests.post(
            BACKEND_CHAT,
            json={"message": prompt, "history": st.session_state.messages},
            timeout=120,
        )
        if resp.status_code == 200:
            reply = resp.json().get("reply", "⚠️ No reply.")
        else:
            reply = f"⚠️ Chat Error: {resp.status_code} {resp.text}"
    except Exception as e:
        reply = f"⚠️ Request Failed: {e}"

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_text = ""
        for chunk in reply.split():
            full_text += chunk + " "
            time.sleep(0.03)
            placeholder.markdown(full_text + "▌")
        placeholder.markdown(full_text)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.session_state.chat_history[st.session_state.active_chat] = st.session_state.messages.copy()


    #streamlit run Python/app.py


