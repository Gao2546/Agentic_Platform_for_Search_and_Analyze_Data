import argparse
import json
import boto3
from urllib.parse import urlparse

# รับค่า Parameter ที่ Airflow โยนมาให้
parser = argparse.ArgumentParser()
parser.add_argument('--ticker', type=str, default='AAPL')
parser.add_argument('--output_path', type=str)
args, unknown = parser.parse_known_args()

print(f"📡 Fetching data for {args.ticker}...")
data = [{"ticker": args.ticker, "price": 150.0, "status": "success", "content": "Sample news content for AI"}]

# ถ้ามีการระบุ output_path ให้บันทึกไฟล์
if args.output_path and args.output_path.startswith("s3a://"):
    parsed = urlparse(args.output_path.replace("s3a://", "http://"))
    bucket = parsed.netloc
    
    # เพิ่มชื่อไฟล์เข้าไปท้าย Path
    key = parsed.path.lstrip('/') + "raw_data.json"

    # เชื่อมต่อ MinIO
    s3 = boto3.client('s3', endpoint_url='http://minio:9000', aws_access_key_id='admin', aws_secret_access_key='password123')
    
    # บันทึกไฟล์
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(data))
    print(f"✅ Saved data to MinIO: s3a://{bucket}/{key}")