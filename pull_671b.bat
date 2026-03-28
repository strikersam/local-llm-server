@echo off
echo Starting DeepSeek-R1:671B download to D:\aipc-models ...
echo This will take a long time depending on internet speed (~236 GB).
set OLLAMA_MODELS=D:\aipc-models
set OLLAMA_HOST=127.0.0.1:11434
"C:\Users\swami\AppData\Roaming\aipc\runtime\ollama\ollama.exe" pull deepseek-r1:671b
echo Download complete!
