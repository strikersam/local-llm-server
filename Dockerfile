FROM node:22-alpine AS webui
WORKDIR /src/webui/frontend
COPY webui/frontend/package.json webui/frontend/package-lock.json* ./
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

CMD ["sh", "-lc", "uvicorn proxy:app --host 0.0.0.0 --port ${PORT:-8000} --log-level ${LOG_LEVEL:-info}"]

