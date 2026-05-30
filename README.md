**B2B Lead Generation & Market Intelligence Engine**

An end-to-end intelligence system that unifies a Streamlit UI, a FastAPI service layer, spaCy-based entity extraction, and an autonomous RAG router powered by a local Mistral-7B model (Ollama) and the Tavily AI Index API.

**High-level architecture:** Streamlit UI → FastAPI API → spaCy NLP entity extraction for targeted URL scraping, alongside a RAG router → Tavily AI Index retrieval → Ollama Mistral-7B synthesis for autonomous market research.

## Core Features
1. Dual-track operation: **Autonomous RAG Market Research (Tavily + Mistral-7B)** and **Targeted URL Entity Scraping (spaCy NLP)**.
2. Unified UX for rapid lead discovery, enrichment, and intelligence synthesis.
3. Modular backend and NLP pipeline designed for extensibility and scale.

## Tech Stack
1. Streamlit
2. FastAPI
3. Uvicorn
4. spaCy
5. Ollama (Mistral-7B)
6. Tavily AI Index API

## Installation & Setup
```bash
# 1) Clone the repository
git clone <YOUR_REPO_URL>
cd lead_generator

# 2) Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Install spaCy model
python -m spacy download en_core_web_sm
```

### Configure environment variables
Set your Tavily API key:
```bash
# Windows PowerShell
$env:TAVILY_API_KEY="your_api_key_here"

# macOS/Linux
export TAVILY_API_KEY="your_api_key_here"
```

### Run the FastAPI backend (port 8000)
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Run the Streamlit frontend
```bash
cd frontend
streamlit run app_gui.py
```

##  Future Roadmap
This system will soon be infused with advanced **Marketing Automation** modules to seamlessly convert extracted targets into automated outreach campaigns.

