# AI Chat + OCR Assistant (Ollama + FastAPI + Streamlit)

## Setup
1. Install requirements: `pip install -r requirements.txt`
2. Run Ollama:
   ```bash
   ollama serve
   ollama pull llama3
   ```
3. Run backend:
   ```bash
   uvicorn backend:app --reload
   ```
4. Run frontend:
   ```bash
   streamlit run app.py
   ```
