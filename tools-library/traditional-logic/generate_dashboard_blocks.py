import argparse
import json
import datetime
import uuid
import os
from pymongo import MongoClient

# ==========================================
# 1. รับค่า Arguments ที่ Airflow ส่งมาให้
# ==========================================
parser = argparse.ArgumentParser(description="Generate Dynamic UI Blocks for Dashboard")
parser.add_argument('--scope_id', type=str, required=True, help="ID ของ Scope")
parser.add_argument('--schedule_id', type=str, required=True, help="ID ของ Schedule")
parser.add_argument('--ticker', type=str, default='AAPL', help="ชื่อหุ้นหรือสินทรัพย์")
parser.add_argument('--sentiment', type=str, default='Bullish', help="ผลการวิเคราะห์จาก AI")
args, unknown = parser.parse_known_args()

print(f"🎨 [VISUALIZE TASK] เริ่มสร้าง Dashboard Blocks สำหรับ {args.ticker} (Schedule: {args.schedule_id})")

# ==========================================
# 2. จำลองการสร้าง JSON Blocks (Standard Schema)
# ==========================================
# ในของจริง ตรงนี้จะเอาผลลัพธ์ที่ได้จาก Task AI Inference มาแปลงร่าง
color_map = {"Bullish": "green", "Bearish": "red", "Neutral": "gray"}
ui_color = color_map.get(args.sentiment, "blue")
trend_icon = "up" if args.sentiment == "Bullish" else "down" if args.sentiment == "Bearish" else "none"

blocks = [
    {
        "id": f"metric-1-{uuid.uuid4().hex[:8]}",
        "type": "metric",
        "colSpan": 4,
        "label": f"{args.ticker} Signal",
        "value": "STRONG BUY" if args.sentiment == "Bullish" else "SELL",
        "color": ui_color,
        "trend": trend_icon
    },
    {
        "id": f"metric-2-{uuid.uuid4().hex[:8]}",
        "type": "metric",
        "colSpan": 4,
        "label": "AI Sentiment Confidence",
        "value": "92",
        "suffix": "%",
        "color": "blue"
    },
    {
        "id": f"markdown-1-{uuid.uuid4().hex[:8]}",
        "type": "markdown",
        "colSpan": 12,
        "content": f"### 🤖 บทสรุปจาก AI Agent\nจากการวิเคราะห์ข่าวย้อนหลังของ **{args.ticker}** พบว่าทิศทางตลาดอยู่ในเกณฑ์ **{args.sentiment}** \n- ปัจจัยบวก: ผลประกอบการไตรมาสล่าสุดโตทะลุเป้า\n- แนวต้านถัดไป: สัปดาห์หน้าคาดว่าจะทดสอบ High เดิม"
    },
    {
        "id": f"chart-1-{uuid.uuid4().hex[:8]}",
        "type": "chart",
        "colSpan": 12,
        "title": f"จำลองราคา {args.ticker} ย้อนหลัง",
        "subType": "area",
        "config": {
            "xAxisKey": "time",
            "lines": [{"dataKey": "price", "name": "Price (USD)", "color": "#10b981" if ui_color == "green" else "#f43f5e"}]
        },
        "data": [
            {"time": "09:00", "price": 145.2},
            {"time": "10:00", "price": 146.5},
            {"time": "11:00", "price": 146.0},
            {"time": "12:00", "price": 148.3},
            {"time": "13:00", "price": 149.1},
            {"time": "14:00", "price": 150.5}
        ]
    }
]

# ==========================================
# 3. บันทึกข้อมูลลง MongoDB
# ==========================================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password123@mongodb:27017")
DB_NAME = "agentic_db"
COLLECTION_NAME = "ai_insights"

try:
    print("🔌 กำลังเชื่อมต่อ MongoDB...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    document = {
        "scope_id": args.scope_id,
        "schedule_id": args.schedule_id,
        "ticker": args.ticker,
        "insight_type": args.sentiment,
        "blocks": blocks,
        "created_at": datetime.datetime.now(datetime.timezone.utc) # แก้เรื่อง datetime serializable แล้ว
    }

    # Insert ลง Database
    result = collection.insert_one(document)
    print(f"✅ บันทึก Dashboard Blocks ลง MongoDB สำเร็จ! (ID: {result.inserted_id})")

except Exception as e:
    print(f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อหรือบันทึกข้อมูลลง MongoDB: {e}")
    # ใช้ default=str เพื่อไม่ให้ json.dumps พังเวลาเจอ datetime
    print(f"📊 พิมพ์ JSON Output จำลองแทน:\n{json.dumps(document, indent=2, default=str)}")

finally:
    if 'client' in locals():
        client.close()