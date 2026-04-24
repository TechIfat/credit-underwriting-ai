#!/bin/bash

echo "🧪 STARTING CI/CD EVALUATION PIPELINE..."
echo "----------------------------------------"

# EXAM CONCEPT: CI/CD Secret Injection
# We explicitly load the environment variables so the headless CLI has access to the API Key
export $(grep -v '^#' .env.local | xargs)

echo "1. Running Extractor Spoke..."
uv run python src/agents/spokes/extractor.py > tests/evals/temp_output.txt

echo "2. Invoking Claude Code (Headless Judge)..."

# EXAM CONCEPT: -p sends a single prompt. --bare removes all UI formatting.
# Notice we are passing the API key directly to the process to bypass OAuth
JUDGE_RESULT=$(ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY npx -y @anthropic-ai/claude-code -p "Read tests/evals/temp_output.txt. Verify that the JSON contains 'Wayne Enterprises Ltd' and the 'requested_loan_amount' is exactly 5000000. If both are true, output exactly the word 'PASS'. Otherwise, output 'FAIL'." --bare)

echo "----------------------------------------"
echo "⚖️  JUDGE VERDICT: $JUDGE_RESULT"

# 3. Standard CI/CD Exit Codes
# We use wildcard matching (*PASS*) in case Claude adds a period or newline
if [[ "$JUDGE_RESULT" == *"PASS"* ]]; then
    echo "🟢 PIPELINE SUCCESS: Code is safe to merge to main."
    rm tests/evals/temp_output.txt
    exit 0
else
    echo "🚨 PIPELINE FAILED: Regression detected in extraction logic."
    rm tests/evals/temp_output.txt
    exit 1
fi