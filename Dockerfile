FROM node:22-slim AS webui
WORKDIR /src/webui/frontend
COPY webui/frontend/package.json ./
RUN npm install
COPY webui/frontend/ ./
RUN npm run build

FROM python:3.13-slim AS app
WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
COPY --from=webui /src/webui/frontend/dist /app/webui/frontend/dist

ENV PROXY_PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health', timeout=5)" || exit 1

CMD ["sh", "-lc", "UVICORN_LOG_LEVEL=$(printf '%s' \"${LOG_LEVEL:-INFO}\" | tr '[:upper:]' '[:lower:]') && uvicorn proxy:app --host 0.0.0.0 --port ${PORT:-8000} --log-level \"$UVICORN_LOG_LEVEL\""]

