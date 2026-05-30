"""
B2B Lead Generation Engine — FastAPI Backend
NLP Pipeline: spaCy en_core_web_sm + BeautifulSoup scraper
Endpoint: POST /api/extract-leads
"""

import logging
import sys
import re
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup
import spacy
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

# ─── Logging Configuration ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BACKEND] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("lead_engine.backend")

# ─── spaCy Model Bootstrap ───────────────────────────────────────────────────
log.info("Initialising spaCy pipeline (en_core_web_sm) …")
try:
    nlp = spacy.load("en_core_web_sm")
    log.info("spaCy pipeline loaded successfully.")
except OSError:
    log.warning("Model not found locally — downloading en_core_web_sm …")
    import subprocess
    subprocess.run(
        [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
        check=True,
    )
    nlp = spacy.load("en_core_web_sm")
    log.info("spaCy pipeline bootstrapped and loaded.")

# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="B2B Lead Extraction API",
    description="Scrapes target URLs and extracts ORG/PERSON entities via spaCy.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Schemas ──────────────────────────────────────────────
class LeadRequest(BaseModel):
    url: str  # kept as str intentionally — HttpUrl is too strict for some edge cases

class LeadRecord(BaseModel):
    extracted_entity: str
    category_label: str
    context_snapshot: str
    source_url: str


# ─── Utility: Clean Raw HTML Text ────────────────────────────────────────────
def _clean_text(raw: str) -> str:
    """Collapse whitespace and strip boilerplate noise."""
    text = re.sub(r"\s+", " ", raw)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # strip non-ASCII
    return text.strip()


# ─── Utility: Context Window Around Match ────────────────────────────────────
def _context_window(text: str, start: int, end: int, window: int = 100) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    snippet = text[left:right].strip()
    # Trim to nearest word boundary
    if left > 0 and " " in snippet:
        snippet = snippet[snippet.index(" ") + 1:]
    return f"…{snippet}…"


# ─── Core Scraping + NLP Function ────────────────────────────────────────────
def scrape_and_extract(url: str) -> List[Dict[str, Any]]:
    log.info(f"[SCRAPE] Targeting URL: {url}")

    # Aggressive Browser Spoofing Headers to bypass standard WAF/Anti-Bot walls
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        
        # Explicit intercept for aggressive bot protection (like Crunchbase/Cloudflare)
        if resp.status_code == 403:
            log.error(f"[SCRAPE] 403 Forbidden. Target is actively blocking automated scripts.")
            raise HTTPException(status_code=403, detail="Access Denied (403 Forbidden). This site uses advanced anti-bot protection (like Cloudflare/PerimeterX) that blocks automated Python requests. Please try a standard news domain like TechCrunch instead.")
            
        resp.raise_for_status()
        log.info(f"[SCRAPE] HTTP {resp.status_code} — content length: {len(resp.content)} bytes")
        
    except requests.RequestException as exc:
        log.error(f"[SCRAPE] Request failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script / style / nav noise
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    raw_text = soup.get_text(separator=" ")
    clean = _clean_text(raw_text)
    log.info(f"[NLP] Cleaned text length: {len(clean)} characters")

    # spaCy inference — truncate to 1 million chars (spaCy hard limit)
    doc = nlp(clean[:1_000_000])
    log.info(f"[NLP] spaCy found {len(doc.ents)} raw entities")

    TARGET_LABELS = {"ORG", "PERSON"}
    seen: set = set()
    records: List[Dict[str, Any]] = []

    for ent in doc.ents:
        if ent.label_ not in TARGET_LABELS:
            continue
        key = (ent.text.strip().lower(), ent.label_)
        if key in seen:
            continue
        seen.add(key)

        context = _context_window(clean, ent.start_char, ent.end_char)
        record = {
            "extracted_entity": ent.text.strip(),
            "category_label": ent.label_,
            "context_snapshot": context,
            "source_url": url,
        }
        records.append(record)

    log.info(f"[NLP] Deduplicated lead records extracted: {len(records)}")
    return records


# ─── Endpoint: POST /api/extract-leads ───────────────────────────────────────
@app.post("/api/extract-leads", response_model=List[LeadRecord])
async def extract_leads_post(payload: LeadRequest):
    """
    Primary endpoint. Accepts JSON body: {"url": "https://..."}
    Returns structured lead records with ORG / PERSON entities.
    """
    log.info(f"[ENDPOINT] POST /api/extract-leads — url={payload.url}")
    results = scrape_and_extract(payload.url)
    if not results:
        log.warning("[ENDPOINT] No entities found — returning empty list.")
    return results


# ─── Fallback Endpoint: GET /api/extract-leads?url=... ───────────────────────
@app.get("/api/extract-leads", response_model=List[LeadRecord])
async def extract_leads_get(url: str = Query(..., description="Target URL to scrape")):
    """
    Fallback endpoint for clients that cannot send a JSON body.
    Accepts query parameter: ?url=https://...
    """
    log.info(f"[ENDPOINT] GET /api/extract-leads — url={url}")
    results = scrape_and_extract(url)
    return results


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "spacy_model": "en_core_web_sm"}


# ─── Startup Log ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    log.info("=" * 60)
    log.info("B2B Lead Extraction API — ONLINE")
    log.info("Endpoints:")
    log.info("  POST /api/extract-leads  { url: string }")
    log.info("  GET  /api/extract-leads?url=<string>")
    log.info("  GET  /health")
    log.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")