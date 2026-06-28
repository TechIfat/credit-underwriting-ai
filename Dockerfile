# ─── Stage 1: dependency installer ───────────────────────────────────────────
# Uses uv to sync the locked dependency tree into an isolated venv.
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only the files uv needs to resolve dependencies — this layer is cached
# as long as pyproject.toml and uv.lock are unchanged.
COPY pyproject.toml uv.lock .python-version ./

# Sync exact locked versions into /app/.venv (no editable installs, no dev deps)
RUN uv sync --frozen --no-dev --no-install-project


# ─── Stage 2: minimal runtime image ───────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Keep uv in the runtime so the MCP server subprocess can be launched with
# `uv run` in development workflows (docker exec). Not required for main.py.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Non-root user — never run application processes as root
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin -c "ShiftAi app user" appuser

WORKDIR /app

# Copy the pre-built virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy project metadata (required for `uv run` to locate the venv at runtime)
COPY pyproject.toml uv.lock .python-version ./

# Copy application source — no secrets, no .env files, no test data
COPY src/          src/
COPY mcp_servers/  mcp_servers/
COPY main.py       main.py

# Volume mount points for input documents and output JSON packets
RUN mkdir -p /app/input /app/output && \
    chown -R appuser:appuser /app

# Activate the venv for all subsequent commands
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check — verifies the Python environment and key packages are intact
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import anthropic, fastmcp; print('ok')" || exit 1

# Drop to non-root user before running
USER appuser

ENTRYPOINT ["python", "main.py"]
