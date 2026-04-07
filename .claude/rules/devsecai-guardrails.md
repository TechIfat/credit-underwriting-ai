# DevSecAI & Data Handling Guardrails
**Scope:** Global Repository
**Enforcement:** Strict

1. **Synthetic Data Only:** Never write or execute scripts that pull real-world financial data. All mock data must be explicitly labeled as "SYNTHETIC_MOCK".
2. **Terminal Output Sanitisation:** When reading files, DO NOT print raw unredacted financial data (e.g., NINs, sort codes) to the terminal. 
3. **Architectural Boundary:** You are forbidden from writing LLM calculation logic. Any script requiring mathematical resolution MUST be routed to `/mcp_servers/finance_math/`.