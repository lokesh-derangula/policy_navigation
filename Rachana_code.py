import streamlit as st
import time
import ollama
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

# --- Configuration ---
POPPLER_PATH = r"C:\Release-25.07.0-0\poppler-25.07.0\Library\bin"  # ✅ Update this path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # ✅ Update if needed

st.set_page_config(page_title="Rachana's ChatGPT", page_icon="🤖", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
    .chat-history { padding-bottom: 120px; }
    .input-bar-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        padding: 10px 0;
        background-color: #0E1117;
        z-index: 100;
    }
    .input-bar-container .stColumns {
        width: 60%;
        margin: 0 auto;
        align-items: center;
    }
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"],
    .stFileUploader [data-testid="stFileUploaderFileInput"] + div { display: none; }
    .stFileUploader [data-testid="stFileUploaderDropzone"] { border: none; background-color: transparent; padding: 0; width: 40px; }
    .stFileUploader [data-testid="baseButton-secondary"] { width: 32px; height: 32px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.4); background-color: transparent; display: flex; align-items: center; justify-content: center; padding: 0; }
    .stFileUploader [data-testid="baseButton-secondary"] p { display: none; }
    .stFileUploader [data-testid="baseButton-secondary"]::after { content: '+'; font-size: 24px; font-weight: 300; color: white; line-height: 1; position: relative; top: -1px; }
    .stFileUploader [data-testid="baseButton-secondary"]:hover { border-color: white; background-color: rgba(255, 255, 255, 0.1); }
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.title("🤖 Rachana's ChatGPT")
st.caption("Powered by Ollama and Gemma — with OCR & PDF reading support")

# --- Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "active_chat_index" not in st.session_state:
    st.session_state.active_chat_index = -1
if "last_processed_file_name" not in st.session_state:
    st.session_state.last_processed_file_name = None
if "model_name" not in st.session_state:
    st.session_state.model_name = "llama2"

# --- Ollama Response Function ---
def get_bot_response(prompt):
    try:
        stream = ollama.chat(
            model=st.session_state.model_name,
            messages=[{'role': 'user', 'content': prompt}],
            stream=True
        )
        response_text = ""
        for chunk in stream:
            chunk_text = chunk['message']['content']
            response_text += chunk_text
            yield chunk_text
    except Exception as e:
        yield f"⚠️ Error: {e}"

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Chat Settings")

    st.session_state.model_name = st.selectbox(
        "Choose a Model",
        ["llama2", "gemma", "mistral"],
        index=["llama2", "gemma", "mistral"].index(st.session_state.model_name)
    )

    st.write("---")
    st.header("💬 Chat History")

    search_query = st.text_input("Search history", key="search_bar")

    if st.button("➕ New Chat"):
        st.session_state.active_chat_index = -1
        st.session_state.last_processed_file_name = None
        st.rerun()

    st.write("---")
    filtered_history = [
        (i, chat) for i, chat in reversed(list(enumerate(st.session_state.chat_history)))
        if search_query.lower() in chat["title"].lower()
    ]

    if not filtered_history:
        st.write("No conversations yet.")
    else:
        for i, chat in filtered_history:
            if st.button(chat["title"], key=f"chat_{i}"):
                st.session_state.active_chat_index = i
                st.session_state.last_processed_file_name = None
                st.rerun()

# --- Chat Container ---
chat_container = st.container()
with chat_container:
    st.markdown('<div class="chat-history">', unsafe_allow_html=True)

    if st.session_state.active_chat_index == -1:
        messages_to_display = [{"role": "assistant", "content": "Hello 👋 How can I help you today?"}]
    else:
        messages_to_display = st.session_state.chat_history[st.session_state.active_chat_index]["messages"]

    for message in messages_to_display:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    st.markdown('</div>', unsafe_allow_html=True)

# --- Input Bar ---
st.markdown('<div class="input-bar-container">', unsafe_allow_html=True)
col1, col2 = st.columns([1, 10])

with col1:
    uploaded_file = st.file_uploader(
        "Upload Image or PDF",
        label_visibility="collapsed",
        type=["jpg", "jpeg", "png", "pdf"],
        key="file_uploader"
    )

with col2:
    prompt = st.chat_input("Type your message here...")

st.markdown('</div>', unsafe_allow_html=True)

# --- Handle File Upload ---
if uploaded_file is not None and uploaded_file.name != st.session_state.last_processed_file_name:
    file_name = uploaded_file.name.lower()
    extracted_text = ""

    try:
        if file_name.endswith((".jpg", ".jpeg", ".png")):
            image = Image.open(uploaded_file)
            extracted_text = pytesseract.image_to_string(image)
        elif file_name.endswith(".pdf"):
            pdf_bytes = uploaded_file.read()
            pages = convert_from_bytes(pdf_bytes, poppler_path=POPPLER_PATH)
            for page in pages:
                extracted_text += pytesseract.image_to_string(page)

        if extracted_text.strip():
            ocr_prompt = f"Here is text from {uploaded_file.name}. Summarize it:\n\n---\n{extracted_text}\n---"

            with st.chat_message("user"):
                st.markdown(f"📄 **Extracted text from {uploaded_file.name}:**\n\n{extracted_text[:1000]}...")

            with st.chat_message("assistant"):
                response_text = ""
                for chunk in get_bot_response(ocr_prompt):
                    response_text += chunk
                    st.markdown(chunk)

            # Update session state
            st.session_state.last_processed_file_name = uploaded_file.name
            new_chat_title = f"OCR: {uploaded_file.name} ({time.strftime('%H:%M')})"
            new_chat = {
                "title": new_chat_title,
                "messages": [
                    {"role": "user", "content": f"Uploaded {uploaded_file.name}"},
                    {"role": "assistant", "content": response_text}
                ]
            }
            st.session_state.chat_history.append(new_chat)
            st.session_state.active_chat_index = len(st.session_state.chat_history) - 1
            st.rerun()

        else:
            st.warning("No readable text found in the uploaded file.")

    except Exception as e:
        st.error(f"⚠️ Error while processing file: {e}")

# --- Handle Text Prompt ---
if prompt:
    # Start new chat if needed
    if st.session_state.active_chat_index == -1:
        timestamp = time.strftime("%H:%M")
        new_chat_title = f"{prompt[:25]}... ({timestamp})"
        new_chat = {"title": new_chat_title, "messages": []}
        st.session_state.chat_history.append(new_chat)
        st.session_state.active_chat_index = len(st.session_state.chat_history) - 1

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history[st.session_state.active_chat_index]["messages"].append(
        {"role": "user", "content": prompt}
    )

    # Get response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response_text = ""
            for chunk in get_bot_response(prompt):
                response_text += chunk
                st.markdown(chunk)

    # Save assistant reply
    st.session_state.chat_history[st.session_state.active_chat_index]["messages"].append(
        {"role": "assistant", "content": response_text}
    )

    st.rerun()
