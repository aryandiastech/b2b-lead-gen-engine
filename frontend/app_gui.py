import streamlit as st
import requests
import pandas as pd
from chatbot_agent import run_agent

# Set up page configuration
st.set_page_config(
    page_title="B2B Lead Generation Engine",
    page_icon="💼",
    layout="wide"
)

BACKEND_API_URL = "http://localhost:8000/api/extract-leads"

# Initialize session states if they don't exist
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "extracted_leads" not in st.session_state:
    st.session_state.extracted_leads = []

# Sidebar panel
with st.sidebar:
    st.title("Control Panel")
    st.markdown("---")
    st.subheader("System Architecture")
    st.write("**LLM:** Mistral-7B (Ollama)")
    st.write("**Search:** Tavily AI Index API")
    st.markdown("---")
    
    if st.button("Clear Workspace"):
        st.session_state.chat_history = []
        st.session_state.extracted_leads = []
        st.rerun()

# Main Application Header
st.title("B2B Lead Generation & Market Intelligence Engine")
st.write("Analyze regional market trends via Tavily RAG or extract entities directly from target URLs.")
st.markdown("---")

# Layout Split
col_chat, col_scraper = st.columns([1, 1], gap="large")

# Left Column: RAG Research Chat
with col_chat:
    st.subheader("Autonomous Market Research Chat")
    
    # Persistent chat history box
    chat_container = st.container(height=400)
    with chat_container:
        if not st.session_state.chat_history:
            st.info("System ready. Enter your research query below.")
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Input bar
    if user_prompt := st.chat_input("Ask a market question..."):
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_prompt)
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        
        with st.spinner("Processing query..."):
            try:
                ai_response = run_agent(user_prompt)
                with chat_container:
                    with st.chat_message("assistant"):
                        st.markdown(ai_response)
                st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            except Exception as err:
                st.error(f"Error: {str(err)}")

# Right Column: URL Scraper & Data Grid
with col_scraper:
    st.subheader("Targeted URL Entity Extractor")
    
    target_url = st.text_input(
        "Target Analysis URL:", 
        placeholder="https://techcrunch.com/category/startups/"
    )
    execute_scrape = st.button("Run Lead Extraction")
    
    st.markdown("### Validated Lead Database")
    
    if execute_scrape and target_url:
        with st.spinner("Extracting leads..."):
            try:
                # BUILT-IN FIX: Handles both schema expectations automatically
                response = requests.post(BACKEND_API_URL, json={"target_url": target_url}, timeout=20)
                if response.status_code == 422:
                    response = requests.post(BACKEND_API_URL, json={"url": target_url}, timeout=20)
                
                if response.status_code == 200:
                    raw_data = response.json()
                    # BUILT-IN FIX: Safely parses the dictionary
                    results = raw_data.get("leads", raw_data.get("data", [])) if isinstance(raw_data, dict) else raw_data
                    
                    if results:
                        st.session_state.extracted_leads = results
                        st.success(f"Extracted {len(results)} records.")
                    else:
                        st.warning("No entities found on this page.")
                else:
                    st.error(f"Server error: {response.status_code}")
            except Exception as err:
                st.error(f"Pipeline error: {str(err)}")

    # Display results table
    if st.session_state.extracted_leads:
        df = pd.DataFrame(st.session_state.extracted_leads)
        
        # BUILT-IN FIX: Maps columns safely regardless of backend dict naming
        rename_dict = {}
        if "extracted_entity" in df.columns: rename_dict["extracted_entity"] = "Extracted Entity Name"
        if "category_label" in df.columns: rename_dict["category_label"] = "Classification Tag"
        if "ai_category_label" in df.columns: rename_dict["ai_category_label"] = "Classification Tag"
        if "context_snapshot" in df.columns: rename_dict["context_snapshot"] = "Contextual Trace"
        if "source_url" in df.columns: rename_dict["source_url"] = "Source Vector"
        
        df_display = df.rename(columns=rename_dict)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.dataframe(
            pd.DataFrame(columns=["Extracted Entity Name", "Classification Tag", "Contextual Trace", "Source Vector"]),
            use_container_width=True,
            hide_index=True
        )