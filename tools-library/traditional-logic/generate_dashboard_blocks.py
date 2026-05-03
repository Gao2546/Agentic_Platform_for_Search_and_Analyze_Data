import argparse
import json
import datetime
import uuid
import os
import pandas as pd
import io
import boto3
from urllib.parse import urlparse
from pymongo import MongoClient
from utils.udtp_data_manager import UDTPDataManager

parser = argparse.ArgumentParser()
parser.add_argument('--scope_id', type=str, required=True)
parser.add_argument('--schedule_id', type=str, required=True)
parser.add_argument('--task_id', type=str, required=True)
parser.add_argument('--ticker', type=str, default='AAPL')
args, unknown = parser.parse_known_args()

print(f"🎨 เริ่มสร้าง Dashboard Blocks จาก UDTP Data สำหรับ Scope: {args.scope_id}")

manager = UDTPDataManager()
s3 = boto3.client('s3', endpoint_url='http://minio:9000', aws_access_key_id='admin', aws_secret_access_key='password123')

# 1. ค้นหา Sentiment จาก Inference
insight_results = manager.search_data(stage="3_ANALYZE", scope_id=args.scope_id, schedule_id=args.schedule_id)
sentiment = "Neutral"

if insight_results:
    path = insight_results[-1]['file_path'] # เอาไฟล์ล่าสุด
    parsed = urlparse(path.replace("s3a://", "http://"))
    obj = s3.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip('/'))
    insight_data = json.loads(obj['Body'].read().decode('utf-8'))
    sentiment = insight_data.get("sentiment", "Neutral")

# 2. ค้นหาข้อมูลราคาจาก ETL มาสร้าง Chart
etl_results = manager.search_data(stage="2_ETL", scope_id=args.scope_id, schedule_id=args.schedule_id)
chart_data = []

if etl_results:
    for res in etl_results:
        path = res['file_path']
        parsed = urlparse(path.replace("s3a://", "http://"))
        obj = s3.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip('/'))
        df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
        
        # ค้นหามาได้เท่าไหร่ โชว์ตามนั้นทั้งหมด (ดึงมาสร้างโครงสร้าง Chart)
        for _, row in df.iterrows():
            time_val = str(row.get('timestamp', 'N/A'))
            price_val = float(row.get('price', 0))
            chart_data.append({"time": time_val, "price": price_val})

# 3. ประกอบร่าง UI Blocks
color_map = {"Bullish": "green", "Bearish": "red", "Neutral": "gray"}
ui_color = color_map.get(sentiment, "blue")
trend_icon = "up" if sentiment == "Bullish" else "down" if sentiment == "Bearish" else "none"

blocks = [
    {
        "id": f"metric-1-{uuid.uuid4().hex[:8]}",
        "type": "metric",
        "colSpan": 4,
        "label": f"{args.ticker} Signal",
        "value": "STRONG BUY" if sentiment == "Bullish" else "SELL" if sentiment == "Bearish" else "HOLD",
        "color": ui_color,
        "trend": trend_icon
    },
    {
        "id": f"chart-1-{uuid.uuid4().hex[:8]}",
        "type": "chart",
        "colSpan": 12,
        "title": f"ข้อมูลราคาจริงของ {args.ticker} แบบ Raw Display",
        "subType": "area",
        "config": {
            "xAxisKey": "time",
            "lines": [{"dataKey": "price", "name": "Price (USD)", "color": "#10b981" if ui_color == "green" else "#f43f5e"}]
        },
        "data": chart_data
    }
]

# 4. บันทึกลง MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password123@mongodb:27017")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    collection = client["agentic_db"]["ai_insights"]

    document = {
        "scope_id": args.scope_id,
        "schedule_id": args.schedule_id,
        "ticker": args.ticker,
        "insight_type": sentiment,
        "blocks": blocks,
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }

    result = collection.insert_one(document)
    print(f"✅ บันทึก Dashboard Blocks ลง MongoDB สำเร็จ! (ID: {result.inserted_id})")
except Exception as e:
    print(f"⚠️ เกิดข้อผิดพลาดในการบันทึก MongoDB: {e}")
finally:
    if 'client' in locals():
        client.close()