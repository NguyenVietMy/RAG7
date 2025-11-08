FROM python:3.12-slim

ARG PORT=8000

WORKDIR /app

# Install system dependencies for crawl4ai
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY requirements.txt ./

# Install Python dependencies using uv
# Using --system to install directly (no venv needed in Docker)
RUN uv pip install --system -r requirements.txt && \
    (crawl4ai-setup || echo "crawl4ai-setup not available, skipping")

# Copy the rest of the application code
COPY . .

# Expose the port
EXPOSE ${PORT}

# Default command: run FastAPI backend
# Can be overridden to run MCP server: python mcp_server.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

