"""
Commercial Credit Underwriting Hub
Demonstrates Anthropic Prompt Caching for massive document ingestion.
"""
import os
import time
from dotenv import load_dotenv
from anthropic import Anthropic

# Load our DevSecOps environment
load_dotenv(".env.local")
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def read_document(filepath: str) -> str:
    with open(filepath, "r") as file:
        return file.read()

def query_underwriter(doc_text: str, question: str):
    print(f"❓ Question: {question}")
    start_time = time.time()
    
    # EXAM CONCEPT: Prompt Caching Syntax
    # We place the massive document in the System prompt and tag it as 'ephemeral'.
    # This tells Anthropic: "Hold this in RAM for 5 minutes. I will ask more questions."
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        temperature=0,
        system=[
            {
                "type": "text",
                "text": "You are a Commercial Credit Underwriter. Analyse this document: \n\n" + doc_text,
                "cache_control": {"type": "ephemeral"}  # <--- THE CCA EXAM MAGIC LINE
            }
        ],
        messages=[{"role": "user", "content": question}]
    )
    
    latency = time.time() - start_time
    print(f"🤖 Answer: {response.content[0].text}")
    
    # EXAM CONCEPT: Reading the Cache Telemetry
    usage = response.usage
    print(f"⏱️  Latency: {latency:.2f} seconds")
    print(f"📊 Token Usage:")
    print(f"   - Standard Input Tokens: {usage.input_tokens}")
    print(f"   - Cache CREATION Tokens: {getattr(usage, 'cache_creation_input_tokens', 0)}")
    print(f"   - Cache READ Tokens: {getattr(usage, 'cache_read_input_tokens', 0)}")
    print("-" * 50)

if __name__ == "__main__":
    print("🚀 Booting Commercial Underwriting AI (Prompt Caching Mode)...")
    
    raw_text = read_document("data/synthetic/loan_application.txt")
    
    # THE ARCHITECT'S HACK: 
    # Claude requires at least 1024 tokens to trigger a cache write.
    # Since our mock document is short, we pad it with 1500 words to simulate a 50-page PDF.
    padding = "[SIMULATED PAGE CONTENT] " * 1500
    massive_document = raw_text + padding
    
    # Query 1: The Initial Read (Cache Write)
    print("\n--- TURN 1: INITIAL UPLOAD (COLD CACHE) ---")
    query_underwriter(massive_document, "What is the name of the entity applying for the loan?")
    
    # Query 2: The Follow-Up (Cache Read)
    print("\n--- TURN 2: FOLLOW-UP (WARM CACHE) ---")
    query_underwriter(massive_document, "Who is the CEO and when were they appointed?")
    
    # Query 3: Deep Analysis (Warm Cache)
    print("\n--- TURN 3: DEEP ANALYSIS (WARM CACHE) ---")
    query_underwriter(massive_document, "What is the Net Income and Total Revenue for 2026?")