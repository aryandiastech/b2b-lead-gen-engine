import requests
import json
import os

class AutonomousLeadAgent:
    def __init__(self):
        # Your local GPU inference endpoint
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model_name = "mistral"
        
        # The key to a smart agent: A dedicated API key (replace with your free key)
        self.search_api_key = os.getenv("TAVILY_API_KEY", "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")

    def _live_web_search(self, query: str) -> str:
        """Production-grade search using an API explicitly designed for LLM context."""
        
        # 1. Query Optimization: Clean the prompt for the search engine
        search_term = query.lower().replace("what are the names of", "").replace("which major", "").strip()
        if not search_term:
             search_term = "mumbai tech startups venture funding 2026"
             
        print(f"\n[AGENT SEARCH] Querying Official AI Index for: '{search_term}'")
        
        try:
            # 2. Official Network Call: Bypasses all anti-bot protections
            payload = {
                "api_key": self.search_api_key,
                "query": search_term,
                "search_depth": "basic",
                "max_results": 3
            }
            response = requests.post("https://api.tavily.com/search", json=payload, timeout=10)
            response.raise_for_status() # Catches any HTTP errors immediately
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return "System Alert: Live search returned zero results. Proceeding with foundational knowledge."
                
            # 3. Context Construction: Package the clean JSON into a readable string
            context_chunks = []
            for res in results:
                title = res.get("title", "")
                content = res.get("content", "")
                if title and content:
                    context_chunks.append(f"Source: {title} | Context: {content}")
                    
            return "\n\n".join(context_chunks)[:2000]
            
        except Exception as e:
            # 4. The Circuit Breaker: Fail gracefully without crashing the UI
            print(f"[SEARCH FALLBACK TRIGGERED] API/Network Error: {str(e)}")
            return "Real-time search network is temporarily unreachable. I will answer based on my foundational training data."

    def process_user_query(self, user_prompt: str) -> str:
        """Coordinates the retrieval and the local LLM generation."""
        web_data = self._live_web_search(user_prompt)
        
        system_prompt = (
            "You are a professional B2B Lead Generation data assistant.\n"
            "Using the live, real-time web search context provided below, thoroughly answer the user prompt.\n"
            "Identify and extract actual company names, tech platforms, and business updates from the text context.\n\n"
            f"--- LIVE WEB CONTEXT SEED ---\n{web_data}\n-----------------------------\n"
        )
        
        payload = {
            "model": self.model_name,
            "prompt": f"{system_prompt}\nUser Question: {user_prompt}\n\nStrategic Summary:",
            "stream": False
        }
        
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.ollama_url, 
                data=json.dumps(payload), 
                headers=headers, 
                timeout=45
            )
            
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return f"AI Generation Node Threw an Error Code: {response.status_code}"
            
        except requests.exceptions.ConnectionError:
            return "Pipeline Error: Cannot connect to your local AI engine. Make sure Ollama is running in your terminal."
        except Exception as e:
            return f"Pipeline Error during text processing: {str(e)}"

def run_agent(user_input: str) -> str:
    agent = AutonomousLeadAgent()
    return agent.process_user_query(user_input)