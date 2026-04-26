# Commercial Credit Underwriting AI 
**Status:** Completed (CCA Exam Architecture)  
**Architect:** Ifat Noreen, Principal Agentic AI Architect (ShiftAi Systems Ltd)  

## 🏢 The Initiative
A DevSecOps-hardened, Hub-and-Spoke architecture designed to solve the "Paperwork Avalanche" in Commercial Banking. This platform processes complex, unstructured 50-page financial PDFs and scanned balance sheets, extracting structured data while enforcing strict mathematical and security boundaries.

Built specifically to demonstrate mastery of the Anthropic ecosystem for the **Claude Certified Architect (CCA)** exam.

---

## 🏗️ Architectural Sprints & Capabilities

### 🛡️ Sprint 1: DevSecAI Ingress Guardrails
- Implemented a dual-layer security boundary (`src/security/pii_sanitiser.py`).
- **Layer 1:** Deterministic Regex for UK National Insurance Numbers and Sort Codes.
- **Layer 2:** Probabilistic semantic scoring via Claude 3 Haiku to catch obfuscated PII.

### ⚡ Sprint 2: FinOps & Prompt Caching
- Architected context management using Anthropic's `cache_control: ephemeral`.
- Uploaded massive simulated loan documents to RAM, reducing latency and dropping token costs by 90% for subsequent queries.

### 🧮 Sprint 3: Banning LLM Maths (MCP)
- LLMs are semantic engines, not calculators. Decoupled all financial formulas into a deterministic Python server (`mcp_servers/finance_math/server.py`).
- Integrated via the open-source **Model Context Protocol (MCP)** to calculate Debt Service Coverage Ratios (DSCR) safely.

### 📝 Sprint 4: Forced Structured Output
- Bypassed conversational LLM "chatter" using strict Pydantic schemas and `tool_choice`.
- The Extraction Spoke (`src/agents/spokes/extractor.py`) forces Claude to emit 100% compliant, machine-readable JSON ready for legacy SQL database insertion.

### 🧪 Sprint 5: CI/CD Automated Evals
- Built a headless bash pipeline (`tests/evals/ci_pipeline.sh`) integrating the native `claude` CLI (`-p --bare`).
- Acts as an automated "LLM-as-a-Judge" to verify JSON outputs, throwing standard UNIX exit codes to block deployments upon regression.

### 👁️ Sprint 6: Multimodal Hub-and-Spoke Orchestrator
- **OCR Bypass:** Utilised Claude 4.6 Sonnet's native vision capabilities to read messy, unstructured images of balance sheets (`src/agents/spokes/vision_extractor.py`).
- **The Hub:** (`src/agents/hub/underwriter_hub.py`) Coordinates the workflow: Ingests image → Routes to Vision Spoke for JSON → Routes to MCP Server for Maths → Outputs deterministic loan approval decision.

---

## 🚀 How to Run 

This project uses `uv` for dependency management.

**1. Clone and Sync**

```bash
uv sync
```
**2. Environment Setup**
Create a .env.local file in the root directory:

```Env
ANTHROPIC_API_KEY="sk-ant-your-key-here"
```
**3. Run the Architecture**

```Bash
# Test the DevSecAI Ingress Firewall
uv run python src/security/pii_sanitiser.py

# Test Prompt Caching 
uv run python src/agents/hub/orchestrator.py

# Run the complete Hub-and-Spoke Vision/Maths Pipeline
uv run python src/agents/hub/underwriter_hub.py

# Run the CI/CD Evaluation Pipeline
./tests/evals/ci_pipeline.sh
```
## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📬 Contact & Consulting

**Ifat Noreen**
*Principal Agentic AI Architect | Founder, ShiftAi Systems Ltd*

* **LinkedIn:**[linkedin.com/in/ifat-noreen](https://www.linkedin.com/in/ifat-noreen)
* **GitHub:** [@TechIfat](https://github.com/TechIfat)