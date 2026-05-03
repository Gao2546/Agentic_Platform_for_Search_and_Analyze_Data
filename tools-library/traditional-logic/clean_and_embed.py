import argparse
import json
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

# 1. ค้นหาข้อมูลจาก Stage 1_RAW
search_results = manager.search_data(
    stage="1_RAW", 
    scope_id=args.scope_id, 
    schedule_id=args.schedule_id
)

if not search_results:
    print("⚠️ ไม่พบข้อมูลสำหรับทำ ETL")
    exit(0)

print(f"🚀 เริ่มต้นงาน ETL พบข้อมูล {len(search_results)} ไฟล์")

s3 = boto3.client('s3', endpoint_url='http://minio:9000', aws_access_key_id='admin', aws_secret_access_key='password123')
all_data = []

for res in search_results:
    path = res['file_path']
    parsed = urlparse(path.replace("s3a://", "http://"))
    obj = s3.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip('/'))
    file_data = json.loads(obj['Body'].read().decode('utf-8'))
    all_data.extend(file_data)

# 2. ทำความสะอาดข้อมูลเบื้องต้น
df = pd.DataFrame(all_data)
df['embedding'] = 'mock_vector_placeholder'
df['udtp_stage'] = '2_ETL'

# 3. แปลงเป็น Parquet Bytes และบันทึก
parquet_buffer = io.BytesIO()
df.to_parquet(parquet_buffer, index=False)

saved_path = manager.save_data(
    data=parquet_buffer.getvalue(),
    stage="2_ETL",
    scope_id=args.scope_id,
    schedule_id=args.schedule_id,
    task_id=args.task_id,
    file_extension="parquet"
)

print(f"✅ Cleaned and saved Parquet via UDTP: {saved_path}")