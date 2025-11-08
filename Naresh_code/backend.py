import os
import io
import numpy as np
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import pytesseract
import easyocr
import pdfplumber
from docx import Document


# --- Optional: point pytesseract to the installed Tesseract executable (Windows only)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# -------------------- FastAPI Setup --------------------
app = FastAPI(title="Chat + OCR + File Reader Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Config --------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")

# OCR setup
reader = easyocr.Reader(['en'], gpu=False)


# -------------------- Chat Endpoint --------------------
class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post("/chat")
async def chat_with_ollama(req: ChatRequest):
    """
    Sends a message and conversation history to Ollama model and returns AI reply.
    """
    try:
        conversation = ""
        for item in req.history:
            role = item.get("role", "user")
            content = item.get("content", "")
            conversation += f"{'User' if role == 'user' else 'Assistant'}: {content}\n"

        conversation += f"User: {req.message}\nAssistant:"

        payload = {"model": MODEL_NAME, "prompt": conversation, "stream": False}
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()

        reply = data.get("response") or data.get("text") or "⚠️ No reply from Ollama"
        return {"reply": reply}

    except Exception as e:
        return {"reply": f"⚠️ Ollama Error: {e}"}


# -------------------- OCR / File Extraction Endpoint --------------------
@app.post("/ocr")
async def extract_text(file: UploadFile = File(...)):
    """
    Handles OCR for images and text extraction for PDFs/DOCX.
    Then summarizes the extracted content using Ollama.
    """
    try:
        file_bytes = await file.read()
        filename = file.filename.lower()

        text = ""

        # --- 1️⃣ IMAGE (JPG, PNG) ---
        if filename.endswith((".jpg", ".jpeg", ".png")):
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            np_img = np.array(image)

            results = reader.readtext(np_img)
            text = " ".join([res[1] for res in results]).strip()

            if len(text) < 10:
                tesseract_text = pytesseract.image_to_string(image)
                if len(tesseract_text.strip()) > len(text):
                    text = tesseract_text.strip()

        # --- 2️⃣ PDF ---
        elif filename.endswith(".pdf"):
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            text = text.strip()

        # --- 3️⃣ DOCX ---
        elif filename.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join([p.text for p in doc.paragraphs]).strip()

        else:
            return {"error": "Unsupported file type. Please upload image, PDF, or DOCX."}

        if not text:
            return {"error": "No readable text found in file."}

        # --- Send extracted text to Ollama for summary ---
        summary_prompt = f"The following text was extracted from a document:\n\n{text}\n\nPlease summarize it clearly and concisely."
        payload = {"model": MODEL_NAME, "prompt": summary_prompt, "stream": False}
        ai_response = requests.post(OLLAMA_URL, json=payload, timeout=120)

        if ai_response.status_code == 200:
            data = ai_response.json()
            summary = data.get("response") or data.get("text") or "⚠️ No AI summary"
            return {"extracted_text": text, "ai_summary": summary}
        else:
            return {"extracted_text": text, "error": f"Ollama summary failed: {ai_response.text}"}

    except Exception as e:
        return {"error": f"Processing error: {e}"}



#uvicorn Python.backend:app --reload