# ShiftAi Credit Underwriting AI — Deployment Guide

*For the client's engineering team. Questions: ifat.noreen@googlemail.com*

---

## Overview

This package contains a containerised, production-ready credit underwriting pipeline.
It ingests financial documents (text files or scanned images), extracts structured
financial data using Claude's vision and structured output capabilities, computes
credit ratios via a deterministic Python maths server, and outputs a JSON credit
decision packet ready for insertion into your core lending system.

**What runs inside the container:**

| Component | Role |
|---|---|
| PII Sanitiser (Layer 1 + 2) | Strips NI numbers, sort codes, and semantic PII before any data leaves your perimeter |
| Text Extraction Spoke | Forces Claude to emit strict JSON via `tool_choice` — no string parsing |
| Vision Extraction Spoke | Claude multimodal reads scanned images directly — no OCR engine needed |
| MCP Finance Maths Server | Deterministic Python subprocess — LLM is prohibited from performing arithmetic |

**What the container needs to run:**
- Docker Engine 20.10+ (or Docker Desktop)
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- A financial document to process (`.txt`, `.jpg`, or `.png`)

---

## 1. First-Time Setup

**Step 1 — Configure your API key:**

```bash
cp .env.example .env
```

Open `.env` in a text editor and replace the placeholder with your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Step 2 — Build the Docker image:**

```bash
docker build -t shiftai-credit-underwriting .
```

The build uses a two-stage pipeline. On first run it downloads Python dependencies (~150 MB).
Subsequent builds use the Docker layer cache and complete in under 10 seconds.

---

## 2. Running the Container

### Option A — docker compose (recommended for testing)

Place your financial document in the `input/` folder, then:

```bash
docker compose up
```

The credit decision JSON packet is written to `output/` automatically.

### Option B — docker run (for CI/CD or scripted integration)

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/input:/app/input:ro" \
  -v "$(pwd)/output:/app/output:rw" \
  shiftai-credit-underwriting
```

**To target a specific file rather than scanning the input folder:**

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/input:/app/input:ro" \
  -v "$(pwd)/output:/app/output:rw" \
  shiftai-credit-underwriting \
  --input /app/input/my-balance-sheet.txt
```

---

## 3. Volume Configuration

| Volume | Host Path | Container Path | Permission |
|---|---|---|---|
| Input documents | `./input/` | `/app/input/` | Read-only |
| Output packets | `./output/` | `/app/output/` | Read-write |

**Supported input formats:** `.txt`, `.md`, `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`

**Output format:** A JSON file named `<APPLICATION_ID>.json` (e.g. `CUA-A1B2C3D4.json`)

No ports are exposed — this is a batch processing container, not a persistent service.

---

## 4. Reading the Output

Each run produces a structured JSON credit decision packet in `output/`:

```json
{
  "application_id": "CUA-A1B2C3D4",
  "company_name": "Wayne Enterprises Ltd",
  "extracted_data": {
    "entity_name": "Wayne Enterprises Ltd",
    "requested_loan_amount": 5000000,
    "net_operating_income": 24700000,
    "total_debt_service": 850000,
    "is_high_risk": false
  },
  "ratios": {
    "dscr_raw": "DSCR: 29.06 | ✅ STRONG: Company generates 25% more income than required to service debt.",
    "dscr_value": 29.06,
    "ltv_raw": null
  },
  "recommendation": "APPROVE",
  "reasoning": "DSCR 29.06 meets the ≥1.25 serviceability threshold.",
  "audit_trail": [ ... ],
  "timestamp": "2026-06-12T10:30:00Z"
}
```

**Recommendation values:**

| Value | Meaning |
|---|---|
| `APPROVE` | DSCR ≥ 1.25. All automated thresholds met. Ready for system insertion. |
| `REFER` | DSCR between 1.0–1.25, or calculation error. Route to human underwriter. |
| `DECLINE` | DSCR < 1.0. Company cannot service proposed debt. |
| `BLOCKED` | PII guardrail triggered. Payload routed for compliance review. |

---

## 5. Checking Logs

**View live output during a run:**

```bash
docker compose up
# Logs stream to your terminal in real time.
```

**View logs from a previous run:**

```bash
docker compose logs credit-underwriting-ai
```

**Open a shell inside the container for debugging:**

```bash
docker run --rm -it \
  --env-file .env \
  --entrypoint /bin/bash \
  shiftai-credit-underwriting
```

---

## 6. Troubleshooting

### Container exits immediately with `ANTHROPIC_API_KEY is not set`

The `.env` file is missing or not being passed to the container:

```bash
# Verify .env exists and contains the key:
cat .env

# Test that the key is being read:
docker run --rm --env-file .env shiftai-credit-underwriting --help
```

### `No document found` error

No supported file is present in `./input/`:

```bash
# Check what the container can see in its input volume:
docker run --rm \
  -v "$(pwd)/input:/app/input:ro" \
  --entrypoint ls \
  shiftai-credit-underwriting /app/input
```

Ensure the file has a supported extension (`.txt`, `.jpg`, `.png`).

### API error 401 — Invalid API key

The key in `.env` is incorrect. Re-copy from [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).

### API error 429 — Rate limit exceeded

Your Anthropic account has reached its rate limit. Wait and retry, or increase your
usage tier at [console.anthropic.com/settings/limits](https://console.anthropic.com/settings/limits).

### MCP server connection error

The Finance Maths server failed to start. Run interactively to see the full error:

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/input:/app/input:ro" \
  -v "$(pwd)/output:/app/output:rw" \
  shiftai-credit-underwriting
```

---

## 7. Updating to a New Version

When ShiftAi delivers an updated build:

```bash
# Pull the latest source
git pull origin main

# Rebuild the image (uses layer cache — fast unless dependencies changed)
docker build -t shiftai-credit-underwriting .

# Restart with the new image
docker compose up
```

If ShiftAi delivers a pre-built image via a private container registry:

```bash
docker pull <registry>/shiftai-credit-underwriting:latest
docker compose up
```

---

## 8. Security Notes

- The container runs as a non-root user (`appuser`). Do not override this.
- Input volumes are mounted read-only (`:ro`) — the container cannot modify your source documents.
- API keys are injected via environment variables and are never baked into the image.
- All document text passes through a dual-layer PII sanitiser before reaching the Anthropic API.
- The Finance Maths Server runs as a sandboxed subprocess — the LLM receives only its arithmetic output, never raw numbers it computed itself.
- No ports are exposed. The container has no persistent internal state.

---

*ShiftAi Systems Ltd | Ifat Noreen, Principal Agentic AI Architect*
*ifat.noreen@googlemail.com*
