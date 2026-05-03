import argparse
import pandas as pd
import io
import boto3
from urllib.parse import urlparse
from utils.udtp_data_manager import UDTPDataManager

parser = argparse.ArgumentParser()
parser.add_argument('--scope_id', type=str, required=True)
parser.add_argument('--schedule_id', type=str, required=True)
parser.add_argument('--task_id', type=str, required=True)
args, unknown = parser.parse_known_args()

manager = UDTPDataManager()

# 1. ค้นหาข้อมูลที่ผ่าน ETL มาแล้ว
search_results = manager.search_data(
    stage="2_ETL", 
    scope_id=args.scope_id, 
    schedule_id=args.schedule_id
)

if not search_results:
    print("⚠️ ไม่พบข้อมูลสำหรับทำ Inference")
    exit(0)

s3 = boto3.client('s3', endpoint_url='http://minio:9000', aws_access_key_id='admin', aws_secret_access_key='password123')

total_price = 0
count = 0

for res in search_results:
    path = res['file_path']
    parsed = urlparse(path.replace("s3a://", "http://"))
    obj = s3.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip('/'))
    
    df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
    if 'price' in df.columns:
        total_price += df['price'].sum()
        count += len(df)

# 2. Rule-based Logic จากค่าเฉลี่ย
avg_price = total_price / count if count > 0 else 0
sentiment = "Bullish" if avg_price >= 150 else "Bearish"

result_data = {
    "status": "success",
    "sentiment": sentiment,
    "average_price": round(avg_price, 2),
    "logic_used": "rule_based_average"
}

# 3. บันทึกผลลัพธ์
saved_path = manager.save_data(
    data=result_data,
    stage="3_ANALYZE",
    scope_id=args.scope_id,
    schedule_id=args.schedule_id,
    task_id=args.task_id,
    file_extension="json"
)

print(f"🧠 [Rule-based Agent] Analysis complete. Sentiment: {sentiment} (Avg: {avg_price:.2f})")
print(f"✅ Output saved via UDTP: {saved_path}")