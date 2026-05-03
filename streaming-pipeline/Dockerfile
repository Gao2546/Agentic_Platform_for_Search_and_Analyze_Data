FROM python:3.11-slim

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. ก๊อปปี้และติดตั้ง Shared Library (utils)
COPY utils /app/utils
RUN pip install -e /app/utils

# 2. ก๊อปปี้และติดตั้ง Streaming Requirements
COPY streaming-pipeline/requirements.txt /app/streaming-pipeline/
RUN pip install --no-cache-dir -r /app/streaming-pipeline/requirements.txt

# 3. ก๊อปปี้ Source Code
COPY streaming-pipeline /app/streaming-pipeline

WORKDIR /app/streaming-pipeline

# Default CMD ให้รันตัว Worker (ส่วนตัว Stream จำลอง ค่อยสั่งรันแยกได้)
CMD ["python", "processors/fast_lane_worker.py"]