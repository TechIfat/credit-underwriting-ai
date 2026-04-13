"""
DevSecAI Ingress Guardrail (Advanced)
Layer 1: Deterministic Regex Redaction (Known Knowns)
Layer 2: Probabilistic Semantic Scoring via Claude 3 Haiku (Unknown Unknowns)
"""
import re
import os
import logging
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(".env.local")

# Configure enterprise logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DevSecAI-Sanitiser")

# Initialize the fast, cheap model for security scanning
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ---------------------------------------------------------
# LAYER 1: DETERMINISTIC REGEX (Fast & Free)
# ---------------------------------------------------------
def regex_redact(raw_text: str) -> str:
    original_text = raw_text
    
    # Redact standard UK NINs
    nin_pattern = r'[A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}[0-9]{6}[A-D\s]{1}'
    sanitised_text = re.sub(nin_pattern, "[REDACTED_NIN]", raw_text, flags=re.IGNORECASE)
    
    # Redact standard UK Sort Codes
    sort_code_pattern = r'\b\d{2}[-\s]\d{2}[-\s]\d{2}\b'
    sanitised_text = re.sub(sort_code_pattern, "[REDACTED_SORT_CODE]", sanitised_text)
    
    if sanitised_text != original_text:
        logger.warning("🔒 Layer 1 Triggered: Deterministic PII redacted.")
        
    return sanitised_text

# ---------------------------------------------------------
# LAYER 2: PROBABILISTIC SCORING (Claude 4.5 Haiku)
# ---------------------------------------------------------
def semantic_risk_scan(text: str) -> dict:
    """
    Uses Claude 3 Haiku to evaluate ambiguous PII, hidden account numbers, or contextual risks.
    Forces strict JSON output using tool_choice.
    """
    risk_tool = {
        "name": "record_risk_score",
        "description": "Records the security risk score of the provided text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_category": {
                    "type": "string", 
                    "enum":["LOW", "UNCERTAIN", "HIGH"],
                    "description": "LOW: Safe. UNCERTAIN: Ambiguous/Hidden PII. HIGH: Clear security breach."
                },
                "confidence_score": {
                    "type": "integer", 
                    "description": "Confidence in this assessment from 1 to 100."
                },
                "reasoning": {
                    "type": "string", 
                    "description": "Brief explanation of why this score was given."
                }
            },
            "required": ["risk_category", "confidence_score", "reasoning"]
        }
    }

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        temperature=0,
        system="You are a strict DevSecOps data sanitiser for a UK Bank. Look for hidden, obfuscated, or contextual PII that Regex might miss.",
        messages=[{"role": "user", "content": f"Analyze this text for security risks: '{text}'"}],
        tools=[risk_tool],
        tool_choice={"type": "tool", "name": "record_risk_score"} # Force the model to use this tool
    )

    # Extract the structured JSON output from the tool use block
    for block in response.content:
        if block.type == "tool_use":
            return block.input
            
    return {"risk_category": "UNCERTAIN", "reasoning": "Failed to parse LLM output."}

# ---------------------------------------------------------
# THE INGRESS GATEWAY
# ---------------------------------------------------------
def process_ingress_data(raw_text: str) -> str:
    logger.info("Initiating Ingress Security Scan...")
    
    # 1. Run Regex
    cleaned_text = regex_redact(raw_text)
    
    # 2. Run Semantic Scan
    semantic_result = semantic_risk_scan(cleaned_text)
    category = semantic_result.get("risk_category")
    reason = semantic_result.get("reasoning")
    
    # 3. The Triage Logic
    if category == "HIGH":
        logger.error(f"🚨 BLOCKING PAYLOAD: {reason}")
        return "ERROR: Payload blocked by Semantic Security Policy."
        
    elif category == "UNCERTAIN":
        logger.warning(f"⚠️ ROUTING TO HUMAN REVIEW (HITL): {reason}")
        # In production, this saves to a database queue for compliance officers
        return f"PENDING: Payload flagged for Human Review. Reason: {reason}"
        
    else:
        logger.info("✅ Payload cleared all security layers.")
        return cleaned_text

if __name__ == "__main__":
    # Test 1: The Ambiguous Threat (Regex will fail, Claude will catch it)
    print("\n--- TEST 1: AMBIGUOUS DATA ---")
    sneaky_text = "Applicant John Doe. Send the loan to my NatWest account. The sort code is the year 2024 followed by 12."
    print(f"Result: {process_ingress_data(sneaky_text)}")
    
    # Test 2: Safe Data
    print("\n--- TEST 2: SAFE DATA ---")
    safe_text = "Applicant John Doe. Requesting £5,000 for purchasing retail inventory."
    print(f"Result: {process_ingress_data(safe_text)}\n")