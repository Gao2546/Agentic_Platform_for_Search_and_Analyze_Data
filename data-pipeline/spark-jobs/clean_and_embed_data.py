import argparse
import uuid
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, current_timestamp, lit
from pyspark.sql.types import StringType

# ==========================================
# 1. รับค่า Arguments 
# ==========================================
parser = argparse.ArgumentParser()
parser.add_argument('--scope_id', type=str, required=True)
parser.add_argument('--schedule_id', type=str, required=True)
parser.add_argument('--tags', type=str, default="[]")
parser.add_argument('--input_path', type=str, required=True)
args = parser.parse_args()

try:
    tags_list = json.loads(args.tags)
except:
    tags_list = []

# ==========================================
# 2. Helper Functions
# ==========================================
def generate_mock_embedding(text):
    if not text:
        return json.dumps([0.0] * 1536)
    base_val = len(str(text)) / 1000.0
    mock_vector = [base_val] * 1536
    return json.dumps(mock_vector)

embedding_udf = udf(generate_mock_embedding, StringType())
uuid_udf = udf(lambda: str(uuid.uuid4()), StringType())

def main():
    # ==========================================
    # 3. สร้าง Spark Session
    # ==========================================
    spark = SparkSession.builder \
        .appName(f"Agentic_ETL_Scope_{args.scope_id}") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "admin") \
        .config("spark.hadoop.fs.s3a.secret.key", "password123") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
        # .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.6.0") \
        # .getOrCreate()

    print(f"🚀 เริ่มต้นงาน ETL สำหรับ Scope: {args.scope_id}")

    try:
        raw_df = spark.read.json(args.input_path)
    except Exception as e:
        print(f"⚠️ ไม่พบข้อมูลหรือเกิดข้อผิดพลาดในการอ่าน: {e}")
        spark.stop()
        return

    # ==========================================
    # 🌟 จุดแก้ปัญหา: ตรวจสอบและปรับ Schema อัตโนมัติ
    # ==========================================
    # ถ้าเป็นข้อมูลหุ้น (ไม่มี content) ให้เอา ticker มาต่อรวมกันเป็น content ชั่วคราว
    if "content" not in raw_df.columns:
        print("🔧 ตรวจพบข้อมูลประเภท Stock/Price... ทำการแปลง Schema ชั่วคราว")
        raw_df = raw_df.withColumn("content", lit(f"Data from {args.input_path}"))
        raw_df = raw_df.withColumn("title", col("ticker") if "ticker" in raw_df.columns else lit("Unknown Title"))
        raw_df = raw_df.withColumn("published_date", col("timestamp") if "timestamp" in raw_df.columns else current_timestamp())

    scope_pg_array = f"{{{args.scope_id}}}"
    schedule_pg_array = f"{{{args.schedule_id}}}"
    tags_pg_array = "{" + ",".join(tags_list) + "}"
    source_ref_col = col("url") if "url" in raw_df.columns else lit(args.input_path)

    # 5. Transform
    clean_df = raw_df.filter(col("content").isNotNull()) \
                     .withColumn("id", uuid_udf()) \
                     .withColumn("source_reference", source_ref_col) \
                     .withColumn("chunk_text", col("content")) \
                     .withColumn("embedding", embedding_udf(col("content"))) \
                     .withColumn("created_at", current_timestamp()) \
                     .withColumn("udtp_scope_ids", lit(scope_pg_array)) \
                     .withColumn("udtp_schedule_ids", lit(schedule_pg_array)) \
                     .withColumn("udtp_tags", lit(tags_pg_array)) \
                     .withColumn("udtp_stage", lit("2_ETL"))

    # 6. Load - บันทึก Parquet
    output_parquet_path = f"s3a://processed-data/clean-news/scope={args.scope_id}/schedule={args.schedule_id}/"
    lake_df = clean_df.select("id", "title", "content", "published_date", "udtp_scope_ids", "udtp_schedule_ids")
    lake_df.write.mode("overwrite").parquet(output_parquet_path)

    # 7 & 8. Load - บันทึก Metadata และ Vector ลง Postgres
    db_url = "jdbc:postgresql://postgres:5432/agentic_db"
    db_properties = {
        "user": "admin",
        "password": "password123",
        "driver": "org.postgresql.Driver",
        "stringtype": "unspecified" 
    }

    print("📝 กำลังลงทะเบียนไฟล์ใน file_assets...")
    asset_id = str(uuid.uuid4())
    file_asset_data = [(
        asset_id, asset_id, f"etl_output_{args.schedule_id}", output_parquet_path, "application/parquet", 
        0, "SNAPPY", json.dumps({"source": args.input_path}), scope_pg_array, schedule_pg_array, tags_pg_array, "2_ETL"
    )]
    file_asset_cols = ["id", "asset_id", "file_name", "file_path", "mime_type", "size_byte", "compression", "attributes", "udtp_scope_ids", "udtp_schedule_ids", "udtp_tags", "udtp_stage"]
    spark.createDataFrame(file_asset_data, schema=file_asset_cols).write.jdbc(url=db_url, table="file_assets", mode="append", properties=db_properties)

    print(f"🧠 กำลังบันทึก Vector Embeddings ลง PostgreSQL...")
    vector_df = clean_df.select("id", "source_reference", "chunk_text", "embedding", "created_at", "udtp_scope_ids", "udtp_schedule_ids", "udtp_tags", "udtp_stage")
    vector_df.write.jdbc(url=db_url, table="knowledge_embeddings", mode="append", properties=db_properties)

    print("✅ ETL Job สมบูรณ์แบบ!")
    spark.stop()

if __name__ == "__main__":
    main()