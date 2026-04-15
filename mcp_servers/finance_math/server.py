"""
Isolated MCP Server for Deterministic Financial Mathematics.
Ensures zero LLM hallucination on critical underwriting ratios.
"""
import logging
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FinanceMath-MCP")

# Initialize the isolated MCP Server
mcp = FastMCP("Finance Math Server")

@mcp.tool()
def calculate_dscr(net_operating_income: float, total_debt_service: float) -> str:
    """
    Calculates the Debt Service Coverage Ratio (DSCR).
    
    CRITICAL INSTRUCTION FOR CLAUDE: 
    Use this tool ANY TIME you need to evaluate if a company generates enough income 
    to pay its debts. DO NOT calculate DSCR yourself.
    
    Args:
        net_operating_income: The company's total revenue minus operating expenses.
        total_debt_service: The total annual loan payments (principal + interest).
    """
    logger.info(f"🧮 Calculating DSCR: NOI=£{net_operating_income}, Debt=£{total_debt_service}")
    
    if total_debt_service == 0:
        return "ERROR: Total debt service cannot be zero."
        
    # Deterministic CPU Maths
    dscr = net_operating_income / total_debt_service
    
    # Standard Banking Underwriting Logic
    if dscr >= 1.25:
        assessment = "✅ STRONG: Company generates 25% more income than required to service debt."
    elif dscr >= 1.0:
        assessment = "⚠️ MARGINAL: Company can pay debts, but has minimal safety buffer."
    else:
        assessment = "🚨 CRITICAL RISK: DSCR is below 1.0. Company does not generate enough income to service this debt."
        
    return f"DSCR: {dscr:.2f} | {assessment}"

@mcp.tool()
def calculate_ltv(loan_amount: float, appraised_property_value: float) -> str:
    """
    Calculates the Loan-to-Value (LTV) ratio for commercial real estate or collateral.
    DO NOT calculate LTV yourself. Always route the extracted numbers to this tool.
    """
    logger.info(f"🧮 Calculating LTV: Loan=£{loan_amount}, Value=£{appraised_property_value}")
    
    if appraised_property_value == 0:
        return "ERROR: Appraised value cannot be zero."
        
    ltv_percentage = (loan_amount / appraised_property_value) * 100
    
    if ltv_percentage <= 75.0:
        assessment = "✅ ACCEPTABLE: LTV is within standard commercial lending limits (<= 75%)."
    else:
        assessment = "🚨 HIGH RISK: LTV exceeds 75%. Requires Senior Credit Officer sign-off."
        
    return f"LTV: {ltv_percentage:.1f}% | {assessment}"

if __name__ == "__main__":
    logger.info("Starting Finance Math MCP Server on stdio...")
    mcp.run()