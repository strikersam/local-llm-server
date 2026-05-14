FROM python:3.12-slim

# Install git and essential build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi==0.136.1 \
    uvicorn[standard]==0.46.0 \
    httpx==0.28.1

# Copy the mcp_server package
COPY mcp_server/ ./mcp_server/

# Workspace directory (mounted from host or created fresh)
RUN mkdir -p /workspaces

# Create a non-root user and transfer ownership
RUN useradd -m -u 1000 -s /bin/bash mcpuser \
 && chown -R mcpuser:mcpuser /app /workspaces

USER mcpuser

# Configure git identity for commits made by the agent (runs as mcpuser)
RUN git config --global user.email "mcp-agent@local-llm-server" \
 && git config --global user.name "MCP Agent" \
 && git config --global credential.helper "" \
 && git config --global safe.directory "/workspaces/*"

EXPOSE 8008

ENV MCP_WORKSPACE_BASE=/workspaces
ENV PORT=8008
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "mcp_server.server"]
