"""
Extraction Spoke (Hub-and-Spoke Architecture)
Forces Claude 4.6 Sonnet to extract unstructured PDF text into strict, machine-readable JSON.
"""
import os
import json
import logging
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(".env.local")
logger = logging.getLogger("Extraction-Spoke")
logging.basicConfig(level=logging.INFO)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 1. Define the Strict Enterprise Schema
# This is the exact JSON structure the legacy banking database requires.
financial_schema = {
    "name": "extract_financial_data",
    "description": "Extracts core financial metrics from unstructured loan applications.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string", "description": "The legal name of the company."},
            "company_number": {"type": "string", "description": "The 8-digit UK company number."},
            "requested_loan_amount": {"type": "number", "description": "The requested loan amount in GBP."},
            "net_operating_income": {"type": "number", "description": "Total Revenue minus Operating Expenses."},
            "total_debt_service": {"type": "number", "description": "Annual debt service (Principal + Interest)."},
            "is_high_risk": {"type": "boolean", "description": "True if there are past bankruptcies or massive existing debt."}
        },
        "required":["entity_name", "company_number", "requested_loan_amount", "net_operating_income", "total_debt_service", "is_high_risk"]
    }
}

def extract_to_json(filepath: str) -> dict:
    """Reads a document and forces Claude to return a strict JSON dictionary."""
    logger.info(f"Ingesting document: {filepath}")
    
    with open(filepath, "r") as file:
        raw_text = file.read()

    logger.info("Executing Forced Structured Output extraction...")
    
    # EXAM CONCEPT: Forced Tool Calling for JSON Extraction
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        temperature=0,
        messages=[
            {"role": "user", "content": f"Extract the financial data from this document:\n\n{raw_text}"}
        ],
        tools=[financial_schema],
        # We FORCE Claude to use the tool, preventing any conversational output
        tool_choice={"type": "tool", "name": "extract_financial_data"} 
    )

    # Extract the JSON payload from the tool use block
    for block in response.content:
        if block.type == "tool_use":
            return block.input
            
    raise ValueError("Claude failed to output structured JSON.")

if __name__ == "__main__":
    # Test the Extraction Spoke
    try:
        extracted_data = extract_to_json("data/synthetic/loan_application.txt")
        
        print("\n✅ EXTRACTION SUCCESSFUL. READY FOR SQL DATABASE INSERTION:\n")
        # Print the beautiful, clean JSON object
        print(json.dumps(extracted_data, indent=4))
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")