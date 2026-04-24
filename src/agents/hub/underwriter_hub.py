"""
Commercial Credit Underwriting Hub
Orchestrates the Hub-and-Spoke architecture: 
Image -> Vision Spoke (JSON) -> MCP Server (Maths) -> Final Decision.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add the project root to the Python path so we can import our spoke
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from src.agents.spokes.vision_extractor import extract_from_image

load_dotenv(".env.local")

async def run_hub(image_path: str):
    print("\n🏦 STARTING ENTERPRISE HUB ORCHESTRATOR...")
    print("-" * 50)
    
    # ---------------------------------------------------------
    # 1. DELEGATE TO VISION SPOKE (No OCR)
    # ---------------------------------------------------------
    print("📸 HUB: Delegating to Vision Extraction Spoke...")
    try:
        financial_data = extract_from_image(image_path)
        print(f"✅ HUB: Received structured data for {financial_data['entity_name']}")
    except Exception as e:
        print(f"❌ HUB ERROR: Vision Extraction Failed: {e}")
        return

    # ---------------------------------------------------------
    # 2. DELEGATE TO MCP MATHS SERVER (No LLM Maths)
    # ---------------------------------------------------------
    print("\n🧮 HUB: Delegating to Finance Maths MCP Server...")
    
    server_params = StdioServerParameters(
        command="uv", 
        args=["run", "mcp_servers/finance_math/server.py"], 
        env=os.environ
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # We pass the EXACT integers Claude extracted directly into the deterministic Python server
                result = await session.call_tool(
                    "calculate_dscr", 
                    arguments={
                        "net_operating_income": financial_data["net_operating_income"],
                        "total_debt_service": financial_data["total_debt_service"]
                    }
                )
                
                maths_result = result.content[0].text
                print(f"✅ HUB: Received deterministic calculation:\n   {maths_result}")
                
    except Exception as e:
        print(f"❌ HUB ERROR: MCP Server Connection Failed: {e}")
        return

    # ---------------------------------------------------------
    # 3. FINAL DECISION LOGIC
    # ---------------------------------------------------------
    print("\n📝 HUB: Final Underwriting Decision")
    print("-" * 50)
    print(f"Entity: {financial_data['entity_name']}")
    if "STRONG" in maths_result or "ACCEPTABLE" in maths_result:
        print("Verdict: 🟢 APPROVED (Financials meet risk thresholds)")
    else:
        print("Verdict: 🔴 REJECTED / ESCALATE (Fails DSCR requirements)")
    print("-" * 50)

if __name__ == "__main__":
    # Point the Hub at the messy screenshot we took earlier
    asyncio.run(run_hub("data/synthetic/balance_sheet.png"))