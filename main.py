#!/usr/bin/env python3
"""
ShiftAi Credit Underwriting AI — Docker Entrypoint

Runs the full Hub-and-Spoke pipeline on a single financial document:
  1. PII Sanitiser (Dual-Layer ingress guardrail)
  2. Extraction Spoke — Vision (images) or Text (documents)
  3. MCP Finance Maths Server — deterministic ratio calculation
  4. Credit decision with full JSON audit trail

Usage:
  python main.py --input /app/input/loan_application.txt
  python main.py --input /app/input/balance_sheet.png
  python main.py                  # scans /app/input/ for first supported file
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load env file if present (silently skipped in Docker where vars come from --env-file)
load_dotenv(".env.local")

_INPUT_DIR = Path("/app/input")
_OUTPUT_DIR = Path("/app/output")
_SUPPORTED = {".txt", ".md", ".jpg", ".jpeg", ".png", ".gif", ".webp"}
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# DSCR thresholds (standard commercial lending policy)
_DSCR_APPROVE = 1.25
_DSCR_REFER = 1.00


def _resolve_document(input_arg: str | None) -> Path:
    if input_arg:
        path = Path(input_arg)
        if not path.exists():
            print(f"ERROR: File not found: {input_arg}", file=sys.stderr)
            sys.exit(1)
        return path

    if _INPUT_DIR.exists():
        candidates = sorted(
            f for f in _INPUT_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in _SUPPORTED
        )
        if candidates:
            return candidates[0]

    print(
        "ERROR: No document found.\n"
        "  • Pass --input <path>, or\n"
        "  • Place a document in /app/input/",
        file=sys.stderr,
    )
    sys.exit(1)


async def _run_pipeline(document_path: Path) -> dict:
    """
    Full pipeline: extract → calculate (via MCP) → decide.

    The MCP Finance Maths Server is spawned as a subprocess — the LLM is
    explicitly prohibited from performing any arithmetic.
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    application_id = f"CUA-{uuid.uuid4().hex[:8].upper()}"
    audit: list[str] = []

    audit.append(f"PIPELINE-START: {application_id} | document={document_path.name}")

    # ── Step 1: PII Sanitisation (text documents only) ────────────────────────
    is_image = document_path.suffix.lower() in _IMAGE_EXTS

    if is_image:
        audit.append("PII-SCAN: Image input — vision model instructed to suppress PII at extraction")
        raw_text = None
    else:
        raw_text = document_path.read_text(encoding="utf-8")
        sys.path.insert(0, str(Path(__file__).parent))
        from src.security.pii_sanitiser import process_ingress_data
        sanitised_text = process_ingress_data(raw_text)
        # If blocked or flagged, surface the message and halt
        if sanitised_text.startswith("ERROR:") or sanitised_text.startswith("PENDING:"):
            audit.append(f"PII-SCAN: {sanitised_text}")
            return {
                "application_id": application_id,
                "status": "BLOCKED",
                "reason": sanitised_text,
                "audit_trail": audit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        audit.append("PII-SCAN: Payload cleared dual-layer ingress guardrail")
        raw_text = sanitised_text

    # ── Step 2: Extraction Spoke ──────────────────────────────────────────────
    sys.path.insert(0, str(Path(__file__).parent))

    if is_image:
        from src.agents.spokes.vision_extractor import extract_from_image
        financial_data = extract_from_image(str(document_path))
        audit.append(f"VISION-SPOKE: Extracted → {financial_data.get('entity_name', 'unknown')}")
    else:
        from src.agents.spokes.extractor import extract_to_json
        financial_data = extract_to_json(str(document_path))
        audit.append(f"TEXT-SPOKE: Extracted → {financial_data.get('entity_name', 'unknown')}")

    # ── Step 3: MCP Finance Maths Server ─────────────────────────────────────
    # Spawn the deterministic maths server as a subprocess.
    # LLM is prohibited from computing ratios — only reads the server output.
    audit.append("MCP-SERVER: Spawning Finance Maths Server subprocess")

    # Use sys.executable so the spawned process inherits the same venv Python.
    server_script = str(Path(__file__).parent / "mcp_servers" / "finance_math" / "server.py")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parent)},
    )

    dscr_result: str = "MCP-ERROR"
    ltv_result: str | None = None

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                dscr_response = await session.call_tool(
                    "calculate_dscr",
                    arguments={
                        "net_operating_income": financial_data["net_operating_income"],
                        "total_debt_service": financial_data["total_debt_service"],
                    },
                )
                dscr_result = dscr_response.content[0].text
                audit.append(f"MCP-CALC: DSCR → {dscr_result}")

                if financial_data.get("requested_loan_amount"):
                    loan_amt = financial_data["requested_loan_amount"]
                    # LTV requires property value; use total debt service * 10 as proxy if absent
                    property_value = financial_data.get("property_value") or financial_data.get("total_debt_service") * 15
                    if property_value and loan_amt:
                        ltv_response = await session.call_tool(
                            "calculate_ltv",
                            arguments={
                                "loan_amount": loan_amt,
                                "appraised_property_value": property_value,
                            },
                        )
                        ltv_result = ltv_response.content[0].text
                        audit.append(f"MCP-CALC: LTV → {ltv_result}")

    except Exception as exc:
        audit.append(f"MCP-ERROR: {exc}")
        dscr_result = f"ERROR: {exc}"

    # ── Step 4: Decision policy (deterministic thresholds) ────────────────────
    dscr_value: float | None = None
    try:
        dscr_value = float(dscr_result.split(":")[1].split("|")[0].strip())
    except (ValueError, IndexError):
        pass

    if dscr_value is None:
        recommendation = "REFER"
        reasoning = "Unable to compute DSCR — routed for manual underwriting review."
    elif dscr_value >= _DSCR_APPROVE:
        recommendation = "APPROVE"
        reasoning = f"DSCR {dscr_value:.2f} meets the ≥1.25 serviceability threshold."
    elif dscr_value >= _DSCR_REFER:
        recommendation = "REFER"
        reasoning = f"DSCR {dscr_value:.2f} is marginal (≥1.0 but <1.25) — requires human review."
    else:
        recommendation = "DECLINE"
        reasoning = f"DSCR {dscr_value:.2f} is below 1.0 — company cannot service proposed debt."

    audit.append(f"POLICY-ENGINE: Recommendation = {recommendation}")
    audit.append(f"PIPELINE-END: {datetime.now(timezone.utc).isoformat()}")

    return {
        "application_id": application_id,
        "company_name": financial_data.get("entity_name", "Unknown"),
        "company_number": financial_data.get("company_number"),
        "assessment_year": datetime.now(timezone.utc).year,
        "extracted_data": financial_data,
        "ratios": {
            "dscr_raw": dscr_result,
            "dscr_value": dscr_value,
            "ltv_raw": ltv_result,
        },
        "recommendation": recommendation,
        "reasoning": reasoning,
        "audit_trail": audit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ShiftAi Credit Underwriting AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", metavar="PATH", help="Path to financial document (.txt or .png/.jpg)")
    parser.add_argument("--output-dir", metavar="DIR", default=str(_OUTPUT_DIR), help="Output directory for JSON packet")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        print("Set it in .env.local or pass via -e ANTHROPIC_API_KEY=<key>", file=sys.stderr)
        sys.exit(1)

    document_path = _resolve_document(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[ShiftAi] Processing: {document_path.name}")
    print("[ShiftAi] Pipeline: PII sanitise → extract → MCP calculate → decide")
    print()

    try:
        packet = asyncio.run(_run_pipeline(document_path))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Pipeline failed — {exc}", file=sys.stderr)
        raise

    output_path = output_dir / f"{packet['application_id']}.json"
    output_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    print(f"  Application ID : {packet['application_id']}")
    print(f"  Company        : {packet.get('company_name', 'Unknown')}")
    print(f"  DSCR           : {packet['ratios'].get('dscr_raw', 'N/A')}")
    if packet['ratios'].get('ltv_raw'):
        print(f"  LTV            : {packet['ratios']['ltv_raw']}")
    print()
    print(f"  RECOMMENDATION : {packet['recommendation']}")
    print(f"  Reasoning      : {packet['reasoning']}")
    print()
    print(f"[ShiftAi] Output → {output_path}")


if __name__ == "__main__":
    main()
