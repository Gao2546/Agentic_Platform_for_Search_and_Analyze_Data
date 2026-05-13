# ใช้ Python 3.11 ที่มีขนาดเล็ก
FROM python:3.11-slim

WORKDIR /app

# ติดตั้ง System Dependencies ที่อาจจำเป็นสำหรับการทำ Sandbox หรือรันโค้ดเบื้องต้น
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# คัดลอกและติดตั้ง requirements.txt
COPY ai-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกซอร์สโค้ดทั้งหมดเข้ามา
COPY ai-engine/ .
# กำหนด PYTHONPATH ให้ Python มองเห็นโฟลเดอร์ src 
ENV PYTHONPATH=/app:$PYTHONPATH

# รัน Uvicorn server บนพอร์ต 8000 (พอร์ตภายใน Container)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]