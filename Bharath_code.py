import streamlit as st
import requests
import json
import uuid
import time
import pytesseract
from PIL import Image
import base64
from io import BytesIO
import re

# --- ✅ Correct Tesseract path (Windows) ---
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# --- Page Config ---
st.set_page_config(page_title="💬 ChatGPT Clone", page_icon="💬", layout="wide")
st.title("💬 Chat with Ollama")

# --- Initialize session state ---
if "conversations" not in st.session_state:
    st.session_state["conversations"] = {}
if "current_chat" not in st.session_state:
    chat_id = str(uuid.uuid4())
    st.session_state["current_chat"] = chat_id
    st.session_state["conversations"][chat_id] = {"title": "New Chat", "messages": []}
if "pinned_chats" not in st.session_state:
    st.session_state["pinned_chats"] = set()
if "action_prompt" not in st.session_state:
    st.session_state["action_prompt"] = None
if "pending_prompt" not in st.session_state:
    st.session_state["pending_prompt"] = None
if "show_uploader" not in st.session_state:
    st.session_state["show_uploader"] = False

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    model = st.selectbox("Choose a model", ["phi3", "mistral", "llama2"])
    # Allow configuring Ollama endpoint (useful if Ollama is running on a different port)
    ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")
    dev_mode = st.checkbox("Developer: show sanitized payload", value=False)

    if st.button("➕ New Chat"):
        chat_id = str(uuid.uuid4())
        st.session_state["current_chat"] = chat_id
        st.session_state["conversations"][chat_id] = {"title": "New Chat", "messages": []}

    st.markdown("### 📜 Chat History")
    for chat_id, chat_data in st.session_state["conversations"].items():
        title = chat_data["title"]
        if st.button(title, key=chat_id):
            st.session_state["current_chat"] = chat_id

    st.markdown("### ⭐ Pinned Chats")
    for chat_id in st.session_state["pinned_chats"]:
        title = st.session_state["conversations"][chat_id]["title"]
        if st.button(f"⭐ {title}", key=f"pinned_{chat_id}"):
            st.session_state["current_chat"] = chat_id

    is_pinned = st.session_state["current_chat"] in st.session_state["pinned_chats"]
    pin_label = "Unpin Current Chat" if is_pinned else "⭐ Pin Current Chat"
    if st.button(pin_label):
        if is_pinned:
            st.session_state["pinned_chats"].remove(st.session_state["current_chat"])
        else:
            st.session_state["pinned_chats"].add(st.session_state["current_chat"])

    if st.button("🗑️ Clear Current Chat"):
        st.session_state["conversations"][st.session_state["current_chat"]]["messages"] = []

    st.markdown("<div class='footer'>🚀 Powered by Ollama + Streamlit</div>", unsafe_allow_html=True)

# --- 🌙 ChatGPT-like Modern UI ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    .stApp {background-color:#131416;color:#e6e6e6;font-family:'Inter',sans-serif;}
    section[data-testid="stSidebar"]{background-color:#1f2023 !important;color:#f1f5f9 !important;}
    h1{text-align:center;font-weight:700;background:linear-gradient(90deg,#10a37f,#4f46e5);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;padding:0.3rem 0;font-size:2rem!important;}
    /* Make chat area expand with content (not fixed-height/scrollable) */
    .chat-container{max-width:850px;margin:0 auto;padding:1.5rem;display:flex;flex-direction:column;}
    .chat-container::-webkit-scrollbar{width:6px;}
    .chat-container::-webkit-scrollbar-thumb{background:#3a3b41;border-radius:6px;}
    .chat-bubble{border-radius:12px;padding:1rem 1.4rem;margin:0.7rem 0;max-width:80%;
        word-break:break-word;font-size:1rem;line-height:1.6;animation:fadeIn 0.25s ease-in-out;
        box-shadow:0 1px 3px rgba(0,0,0,0.3);}
    @keyframes fadeIn{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);} }
    .chat-bubble.user{background-color:#0a84ff;color:white;align-self:flex-end;text-align:right;
        border-bottom-right-radius:4px;}
    .chat-bubble.assistant{background-color:#2a2b32;color:#e5e7eb;align-self:flex-start;
        border-bottom-left-radius:4px;}
    .chat-bubble.document{background-color:#3b3b46;color:#e5e7eb;align-self:flex-start;
        border-left:4px solid #10a37f;}
    .bottom-input{position:fixed;bottom:0;left:260px;right:0;background:#131416;padding:1rem 2rem;
        border-top:1px solid #2a2b32;z-index:999;}
    @media (max-width:768px){.bottom-input{left:0;padding:1rem;}}
    div[data-baseweb="input"] input{background-color:#2a2b32!important;color:#e5e7eb!important;
        border:none!important;border-radius:8px!important;font-size:1rem!important;}
    .footer{text-align:center;font-size:0.85rem;color:#a1a1aa;margin-top:2rem;}
    .typing-cursor::after{content:'▌';animation:blink 1s infinite;}
    @keyframes blink{0%,100%{opacity:1;}50%{opacity:0;}}
    </style>

    <!-- ✅ Auto-scroll script -->
    <script>
        var chatDiv = window.parent.document.querySelector('.chat-container');
        if (chatDiv) {
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }
    </script>
    """,
    unsafe_allow_html=True
)

# --- Current chat ---
current_chat_id = st.session_state["current_chat"]
current_chat = st.session_state["conversations"][current_chat_id]

# --- Chat Display ---
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for i, msg in enumerate(current_chat["messages"]):
    bubble_class = f"chat-bubble {msg['role']}"
    st.markdown(f"<div class='{bubble_class}'>{msg['content']}</div>", unsafe_allow_html=True)

    if msg["role"] in ["assistant", "document"] and i == len(current_chat["messages"]) - 1:
        cols = st.columns(3)
        if cols[0].button("🔍 Explain More"):
            st.session_state["pending_prompt"] = f"Explain this in detail:\n\n{msg['content']}"
        if cols[1].button("📝 Summarize"):
            st.session_state["pending_prompt"] = f"Summarize this:\n\n{msg['content']}"
        if cols[2].button("🌐 Translate"):
            st.session_state["pending_prompt"] = f"Translate this into Hindi:\n\n{msg['content']}"
st.markdown("</div>", unsafe_allow_html=True)

# --- Bottom Input ---
st.markdown("<div class='bottom-input'>", unsafe_allow_html=True)
cols = st.columns([9, 1])
prompt_input = cols[0].chat_input("Message ChatGPT...")
if cols[1].button("➕"):
    st.session_state["show_uploader"] = not st.session_state.get("show_uploader", False)
st.markdown("</div>", unsafe_allow_html=True)

# --- ✅ OCR Upload Section (Fixed Image Display) ---
if st.session_state.get("show_uploader"):
    uploaded_image = st.file_uploader("📤 Upload image for OCR", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        image = Image.open(uploaded_image)

        # Convert image to base64 string
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        img_html = f"<img src='data:image/png;base64,{img_str}' width='200'>"

        try:
            extracted_text = pytesseract.image_to_string(image)

            # --- Clean OCR result: remove stray newlines, collapse spaces, and fix uppercase splits ---
            def clean_ocr_text(s: str) -> str:
                if not s:
                    return ""
                # Normalize line endings and split lines
                s = s.replace('\r', '\n')
                lines = [ln.strip() for ln in s.splitlines()]
                # Remove empty lines and join into a single paragraph
                lines = [ln for ln in lines if ln]
                text = ' '.join(lines)
                # Collapse multiple whitespace
                text = re.sub(r'\s+', ' ', text)
                # Merge space-separated uppercase fragments (e.g. "COV ERNMENT" -> "COVERNMENT")
                text = re.sub(r"\b(?:[A-Z]{2,}\s)+[A-Z]{2,}\b", lambda m: m.group(0).replace(' ', ''), text)
                return text.strip()

            extracted_text = clean_ocr_text(extracted_text)
            chat_content = f"🖼️ {img_html}<br>"
            if extracted_text:
                # Use a plain paragraph for extracted text to avoid nested scrolls in some browsers
                chat_content += f"🧾 **Extracted Text:**<br>{extracted_text}"

            current_chat["messages"].append({
                "role": "document",
                "content": chat_content
            })

            st.session_state["show_uploader"] = False
            st.rerun()
        except Exception as e:
            st.error(f"❌ OCR Error: {e}")

# --- Determine prompt ---
prompt = None
if st.session_state.get("pending_prompt"):
    prompt = st.session_state.pop("pending_prompt")
elif st.session_state.get("action_prompt"):
    prompt = st.session_state.pop("action_prompt")
elif prompt_input:
    prompt = prompt_input

# --- Send prompt to Ollama with Typewriter + Auto-scroll ---
if prompt:
    if current_chat["title"] == "New Chat":
        current_chat["title"] = prompt[:30] + ("..." if len(prompt) > 30 else "")
    current_chat["messages"].append({"role": "user", "content": prompt})
    st.markdown(f"<div class='chat-bubble user'>{prompt}</div>", unsafe_allow_html=True)

    placeholder = st.empty()
    placeholder.markdown("<div class='chat-bubble assistant typing-cursor'>🤖 Thinking...</div>", unsafe_allow_html=True)

    full_reply = ""
    start_time = time.time()
    try:
        # --- Sanitize messages: remove embedded base64 images and HTML before sending ---
        payload_messages = []
        data_uri_re = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+")
        html_tag_re = re.compile(r"<[^>]+>")
        for m in current_chat["messages"]:
            safe_m = m.copy()
            if isinstance(safe_m.get("content"), str):
                # remove large base64 blobs used for inline display
                content = data_uri_re.sub("[image omitted]", safe_m["content"])
                # strip simple HTML tags so the model receives plain text
                content = html_tag_re.sub("", content)
                safe_m["content"] = content
            payload_messages.append(safe_m)

        # --- Quick connectivity check to the Ollama base URL ---
        try:
            health_resp = requests.get(ollama_url + "/", timeout=3)
        except Exception as e:
            st.error(f"❌ Can't reach Ollama at {ollama_url}: {e}")
            raise

        # Show sanitized payload in dev mode (trimmed) to help debugging
        if 'dev_mode' in globals() and dev_mode:
            try:
                preview = payload_messages[-6:]
                st.markdown("### Debug: sanitized messages sent to Ollama")
                st.json(preview)
            except Exception:
                pass

        response = requests.post(
            f"{ollama_url}/api/chat",
            json={"model": model, "messages": payload_messages, "stream": True},
            stream=True,
            timeout=120
        )
        if response.status_code != 200:
            # provide response details to aid diagnosis
            try:
                body = response.text
            except Exception:
                body = '<unreadable response body>'
            st.error(f"❌ Ollama returned status {response.status_code}: {body}")
            raise RuntimeError(f"Ollama error: {response.status_code}")
        text_placeholder = st.empty()
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                token = data.get("message", {}).get("content", "")
                if token:
                    full_reply += token
                    text_placeholder.markdown(
                        f"<div class='chat-bubble assistant typing-cursor'>{full_reply}</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        "<script>var chatDiv = window.parent.document.querySelector('.chat-container');"
                        "if(chatDiv){chatDiv.scrollTop = chatDiv.scrollHeight;}</script>",
                        unsafe_allow_html=True
                    )
                    time.sleep(0.02)
        elapsed = time.time() - start_time
        text_placeholder.markdown(
            f"<div class='chat-bubble assistant'>{full_reply}"
            f"<br><span style='color:#a1a1aa;font-size:0.8rem;'>⏱️ {elapsed:.2f}s</span></div>",
            unsafe_allow_html=True
        )
        current_chat["messages"].append({"role": "assistant", "content": full_reply})
    except requests.exceptions.ConnectionError:
        st.error("❌ Couldn't connect to Ollama. Make sure Ollama is running on localhost:11434.")
    except Exception as e:
        st.error(f"❌ Error: {e}")
