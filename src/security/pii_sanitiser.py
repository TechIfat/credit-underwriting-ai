"""
DevSecAI Ingress Guardrail
Intercepts unstructured financial data (PDFs) and scrubs UK PII 
(National Insurance Numbers, Sort Codes) BEFORE it enters the Claude 4.6 context window.
"""
import re
import logging

# Configure enterprise logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DevSecAI-Sanitiser")

def sanitise_financial_text(raw_text: str) -> str:
    """
    Applies regex heuristics to redact sensitive UK PII.
    In production, this could integrate with Microsoft Presidio or AWS Macie via MCP.
    """
    original_text = raw_text
    
    # 1. Redact UK National Insurance Numbers (e.g., AB123456C)
    nin_pattern = r'[A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}[0-9]{6}[A-D\s]{1}'
    sanitised_text = re.sub(nin_pattern, "[REDACTED_NIN]", raw_text, flags=re.IGNORECASE)
    
    # 2. Redact UK Bank Sort Codes (e.g., 12-34-56 or 12 34 56)
    sort_code_pattern = r'\b\d{2}[-\s]\d{2}[-\s]\d{2}\b'
    sanitised_text = re.sub(sort_code_pattern, "[REDACTED_SORT_CODE]", sanitised_text)
    
    if sanitised_text != original_text:
        logger.warning("🔒 DevSecAI Guardrail Triggered: PII detected and redacted before LLM ingestion.")
    else:
        logger.info("✅ Data clean. Ready for Claude API context window.")
        
    return sanitised_text

if __name__ == "__main__":
    # Test the DevSecOps guardrail locally
    mock_pdf_extract = "Applicant Director: John Doe. NIN: AB123456C. Bank Sort Code: 20-45-14."
    print("\n--- INGRESS DATA ---")
    print(f"Original: {mock_pdf_extract}")
    print(f"Sanitised: {sanitise_financial_text(mock_pdf_extract)}")
    print("--------------------\n")