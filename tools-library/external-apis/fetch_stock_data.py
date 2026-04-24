import json
import argparse
import boto3
import random
from datetime import datetime, timezone
from urllib.parse import urlparse

def fetch_mock_stock_data(ticker):
    """จำลองดึงข้อมูลหุ้น/ทองคำ"""
    now = datetime.now(timezone.utc)
    base_price = 2000.0 if "XAU" in ticker.upper() else 150.0
    
    return {
        "ticker": ticker,
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "open": round(base_price + random.uniform(-10, 10), 2),
        "high": round(base_price + random.uniform(5, 15), 2),
        "low": round(base_price + random.uniform(-15, -5), 2),
        "close": round(base_price + random.uniform(-10, 10), 2),
        "volume": int(random.uniform(1000, 10000)),
        "source": "mock_api"
    }

def main():
    # 1. ใช้ argparse เพื่อรับค่า --ticker และ --output_path ที่ Airflow ส่งมา
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', type=str, required=True)
    parser.add_argument('--output_path', type=str, required=True)
    args = parser.parse_args()

    print(f"🚀 Fetching data for {args.ticker}...")
    data = fetch_mock_stock_data(args.ticker)

    # 2. แปลงที่อยู่ s3a://... ที่ได้จาก Airflow ให้กลายเป็น Bucket และ Key สำหรับ MinIO
    # ตัวอย่าง: s3a://raw-data/stock-prices/ticker=AAPL/scope=unknown_scope/
    clean_url = args.output_path.replace('s3a://', 's3://')
    parsed_url = urlparse(clean_url)
    
    bucket_name = parsed_url.netloc # จะได้ 'raw-data'
    prefix = parsed_url.path.lstrip('/') # จะได้ 'stock-prices/ticker=AAPL/scope=unknown_scope/'
    
    timestamp_str = data['timestamp'].replace(':', '')
    file_key = f"{prefix}data_{timestamp_str}.json"

    # 3. เชื่อมต่อ MinIO
    print(f"🔗 Connecting to MinIO at http://minio:9000...")
    s3_client = boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='admin',
        aws_secret_access_key='password123',
        region_name='us-east-1'
    )
    
    # 4. อัปโหลด
    print(f"💾 Uploading to Bucket: '{bucket_name}' | Key: '{file_key}'")
    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=json.dumps(data, indent=2),
        ContentType='application/json'
    )
    print("✅ Upload complete!")

if __name__ == "__main__":
    main()