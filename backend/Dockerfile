FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /bin/uv

WORKDIR /app

# Install dependencies (from the lock file)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the code
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
