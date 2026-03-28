@echo off
set API_KEYS=jnRLvIu9M2kaQFJjhXK3y05kb_BWhOZtGRv7hLDJ8KI
set OLLAMA_BASE=http://localhost:11434
set PROXY_PORT=8000
set RATE_LIMIT_RPM=60
set LOG_LEVEL=INFO
"C:\Users\swami\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn proxy:app --host 0.0.0.0 --port 8000
