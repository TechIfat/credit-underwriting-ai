"""
Vision Extraction Spoke
Bypasses legacy OCR to natively extract structured JSON from messy financial images/PDFs.
"""
import os
import json
import base64
import logging
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(".env.local")
logger = logging.getLogger("Vision-Spoke")
logging.basicConfig(level=logging.INFO)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 1. The Strict Enterprise Schema (Same as Sprint 4)
financial_schema = {
    "name": "extract_financial_data",
    "description": "Extracts core financial metrics from visual documents.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string"},
            "requested_loan_amount": {"type": "number", "description": "Put 0 if not stated."},
            "net_operating_income": {"type": "number", "description": "Revenue minus Expenses."},
            "total_debt_service": {"type": "number"}
        },
        "required":["entity_name", "requested_loan_amount", "net_operating_income", "total_debt_service"]
    }
}

# 2. Base64 Encoding Helper (CCA Exam Requirement)
def get_base64_encoded_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_from_image(image_path: str) -> dict:
    """Reads an image and forces Claude to return a strict JSON dictionary."""
    logger.info(f"Ingesting visual document: {image_path}")
    
    # Encode the image
    base64_image = get_base64_encoded_image(image_path)
    # Determine media type (assuming png or jpeg based on extension)
    media_type = "image/png" if image_path.endswith(".png") else "image/jpeg"

    logger.info("Executing Multimodal Structured Output extraction...")
    
    # EXAM CONCEPT: The Multimodal Message Array
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content":[
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract the financial data from this scanned image."
                    }
                ],
            }
        ],
        tools=[financial_schema],
        tool_choice={"type": "tool", "name": "extract_financial_data"} 
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input
            
    raise ValueError("Claude failed to output structured JSON from image.")

if __name__ == "__main__":
    try:
        # Pass the screenshot you just took
        extracted_data = extract_from_image("data/synthetic/balance_sheet.png")
        
        print("\n👁️  VISION EXTRACTION SUCCESSFUL:\n")
        print(json.dumps(extracted_data, indent=4))
        
    except Exception as e:
        logger.error(f"Vision Extraction failed: {e}")