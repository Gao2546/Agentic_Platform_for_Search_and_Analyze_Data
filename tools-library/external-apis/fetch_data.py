import argparse
import random
import time
from utils.udtp_data_manager import UDTPDataManager

parser = argparse.ArgumentParser()
parser.add_argument('--ticker', type=str, default='AAPL')
parser.add_argument('--scope_id', type=str, required=True)
parser.add_argument('--schedule_id', type=str, required=True)
parser.add_argument('--task_id', type=str, required=True)
args, unknown = parser.parse_known_args()

print(f"📡 Fetching random data for {args.ticker}...")

# 1. จำลองการสุ่มข้อมูล
data = []
base_price = random.uniform(100, 200)
for i in range(10):
    data.append({
        "ticker": args.ticker,
        "price": round(base_price + random.uniform(-5, 5), 2),
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + (i * 60))),
        "content": f"Sample simulated news {i} for {args.ticker}"
    })

# 2. บันทึกด้วย Library ใหม่
manager = UDTPDataManager()
saved_path = manager.save_data(
    data=data,
    stage="1_RAW",
    scope_id=args.scope_id,
    schedule_id=args.schedule_id,
    task_id=args.task_id,
    file_extension="json"
)

print(f"✅ Saved random data via UDTP: {saved_path}")