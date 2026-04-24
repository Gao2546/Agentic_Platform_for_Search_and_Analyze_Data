FROM python:3.11-slim

# ลง OS dependencies สำหรับ psycopg2/asyncpg
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. ก๊อปปี้และติดตั้ง Shared Library (agentic_core)
COPY agentic_core /app/agentic_core
RUN pip install -e /app/agentic_core

# 2. ก๊อปปี้และติดตั้ง Backend Requirements
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 3. ก๊อปปี้ Source Code ของ Backend
COPY backend/src /app/backend/src

WORKDIR /app/backend

EXPOSE 8000

# รัน Uvicorn Server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]