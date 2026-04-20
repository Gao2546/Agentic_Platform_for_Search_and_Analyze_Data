import boto3
from botocore.exceptions import ClientError

# ตั้งค่าการเชื่อมต่อ MinIO
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='admin',
    aws_secret_access_key='password123',
    region_name='us-east-1' # ค่า Default สำหรับ S3 compatible
)

buckets_to_create = ['ai-tool-scripts', 'raw-data', 'processed-data']

def create_buckets():
    for bucket in buckets_to_create:
        try:
            s3_client.head_bucket(Bucket=bucket)
            print(f"Bucket '{bucket}' already exists.")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                s3_client.create_bucket(Bucket=bucket)
                print(f"Bucket '{bucket}' created successfully.")
            else:
                print(f"Error checking bucket '{bucket}': {e}")

if __name__ == "__main__":
    create_buckets()