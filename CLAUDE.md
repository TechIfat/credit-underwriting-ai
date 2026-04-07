# Commercial Credit Underwriting AI (Project Hamilton)

## WHAT
A DevSecOps-hardened, Hub-and-Spoke architecture designed to process £5M+ commercial loan applications. It ingests 50-page unstructured financial PDFs via Claude Vision/Prompt Caching and calculates deterministic risk via decoupled MCP servers.

## ARCHITECTURAL CONSTRAINTS (CCA EXAM PREP)
1. **No LLM Math:** Claude must never calculate financial ratios. All math is routed to the `/mcp_servers/finance_math/` local server.
2. **Hub-and-Spoke:** The main orchestrator must delegate specific tasks to isolated nodes using Anthropic's native SDK.
3. **Structured Output:** Extraction agents must emit strict Pydantic JSON schemas.

## DIRECTORY MAP
- `/agents/hub/` - Orchestrator and state definitions
- `/agents/spokes/` - Vision extraction and JSON structuring nodes
- `/mcp_servers/finance_math/` - Isolated Python/Pandas MCP server for DSCR/DTI calculations
- `/data/synthetic/` - Mock 50-page financial PDFs
- `.claude/rules/` - Directory-specific context bounds for the Claude CLI