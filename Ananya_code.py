import streamlit as st
import requests
from streamlit_chat import message
import json
import os
from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

OLLAMA_API_URL = "http://localhost:11434/api/chat"
HISTORY_FILE = "chat_history.json"

if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            saved_history = json.load(f)
    except json.JSONDecodeError:
        saved_history = []
else:
    saved_history = []

if "user_input" not in st.session_state:
    st.session_state["user_input"] = []
if "ollama_response" not in st.session_state:
    st.session_state["ollama_response"] = []

for item in saved_history:
    if isinstance(item, dict):
        if "user" in item and "bot" in item:
            st.session_state["user_input"].append(item["user"])
            st.session_state["ollama_response"].append(item["bot"])
        elif item.get("role") == "user":
            st.session_state["user_input"].append(item.get("content", ""))
        elif item.get("role") == "assistant":
            st.session_state["ollama_response"].append(item.get("content", ""))

def ollama_chat(messages):
    payload = {
        "model": "llama2:latest",
        "messages": messages,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return f"⚠️ Error connecting to Ollama: {e}"

# --- Custom CSS for ChatGPT-style UI ---
st.markdown("""
    <style>
        .main {
            background-color: #0d0d0d;
            color: white;
        }
        .stTextInput>div>div>input {
            background-color: #1a1a1a;
            color: white;
            border: 1px solid #333;
            border-radius: 20px;
            padding: 12px;
            font-size: 16px;
        }
        .stButton>button {
            border-radius: 12px;
        }
        .stApp {
            text-align: center;
        }
        h1 {
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# --- Title (centered like ChatGPT UI) ---
st.markdown("<h1 style='text-align: center;'>What can I help with?</h1>", unsafe_allow_html=True)

# --- Sidebar: History and Controls ---
st.sidebar.title("🗂️ Conversation History")

if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state["user_input"] = []
    st.session_state["ollama_response"] = []

if st.sidebar.button("🧹 Clear History"):
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    st.session_state["user_input"] = []
    st.session_state["ollama_response"] = []

# --- Show past chats in sidebar ---
for i, (u, b) in enumerate(zip(st.session_state["user_input"], st.session_state["ollama_response"])):
    one_liner = u if len(u) <= 40 else u[:37] + "..."
    with st.sidebar.expander(f"{i + 1}. {one_liner}", expanded=False):
        st.markdown(f"**You:** {u}")
        st.markdown(f"**Bot:** {b}")

# --- Centered input area with icons ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)

# Upload and OCR Section
st.subheader("📸 OCR: Extract Text from Image")

uploaded_file = st.file_uploader("Upload an image (JPG, PNG, etc.)", type=["jpg", "jpeg", "png"])

ocr_text = ""
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    try:
        with st.spinner("🔍 Extracting text from image..."):
            ocr_text = pytesseract.image_to_string(image)

        if ocr_text.strip():
            st.success("✅ Text extracted successfully!")
            st.text_area("Extracted Text:", ocr_text, height=150)

            if st.button("📤 Send Extracted Text to Chat"):
                user_input = ocr_text
            else:
                user_input = st.text_input("Ask anything:", key="input")
        else:
            st.warning("⚠️ No readable text detected in the image.")
            user_input = st.text_input("Ask anything:", key="input")

    except pytesseract.TesseractNotFoundError:
        st.error("🚫 Tesseract not found! Please verify installation path.")
        user_input = st.text_input("Ask anything:", key="input")
else:
    user_input = st.text_input("Ask anything:", key="input")

st.markdown("</div>", unsafe_allow_html=True)

# --- Process user input ---
if user_input:
    conversation = [{"role": "system", "content": "You are a helpful AI assistant for coders."}]

    for u, b in zip(st.session_state["user_input"], st.session_state["ollama_response"]):
        conversation.append({"role": "user", "content": u})
        conversation.append({"role": "assistant", "content": b})

    conversation.append({"role": "user", "content": user_input})

    with st.spinner("🤖 Generating response..."):
        bot_response = ollama_chat(conversation).strip()

    st.session_state["user_input"].append(user_input)
    st.session_state["ollama_response"].append(bot_response)

    chat_data = [
        {"user": u, "bot": b}
        for u, b in zip(st.session_state["user_input"], st.session_state["ollama_response"])
    ]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=4)

# --- Display chat messages (ChatGPT-like flow) ---
if st.session_state["user_input"]:
    for i in range(len(st.session_state["user_input"])):
        message(st.session_state["user_input"][i], is_user=True, key=str(i) + "_user")
        message(st.session_state["ollama_response"][i], key=str(i) + "_bot")
