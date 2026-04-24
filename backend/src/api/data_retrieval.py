from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import RedirectResponse
import boto3
import asyncpg
import os
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter(prefix="/api/v1/data", tags=["Data Retrieval"])

# ==========================================
# 1. Configuration & Connections
# ==========================================
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://admin:password123@localhost:5432/agentic_db")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password123@localhost:27017")

# ==========================================
# 2. MinIO Client Setup
# ==========================================
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name='us-east-1'
)

# ==========================================
# 3. API: ดึงไฟล์จาก MinIO โดยอ้างอิงจาก PostgreSQL
# ==========================================
@router.get("/files/{asset_id}/download")
async def download_file_from_minio(asset_id: str):
    """
    ค้นหา Path ของไฟล์จาก PostgreSQL ด้วย asset_id และคืนค่าเป็น Presigned URL
    เพื่อให้ Frontend ดาวน์โหลดไฟล์จาก MinIO ได้โดยตรง
    """
    try:
        # เชื่อมต่อ Database (ในโปรดักชันควรใช้ Connection Pool)
        conn = await asyncpg.connect(POSTGRES_DSN)
        
        # ค้นหา metadata ของไฟล์
        query = """
            SELECT file_path, file_name, mime_type 
            FROM file_assets 
            WHERE asset_id = $1
        """
        record = await conn.fetchrow(query, asset_id)
        await conn.close()

        if not record:
            raise HTTPException(status_code=404, detail="File asset not found in database")

        file_path = record['file_path']  # e.g., s3a://processed-data/clean-news/data.parquet
        
        # แปลง s3a://bucket/key เป็น bucket และ key
        if not file_path.startswith("s3a://"):
            raise HTTPException(status_code=500, detail="Invalid file path format format")
            
        path_without_scheme = file_path.replace("s3a://", "")
        bucket_name = path_without_scheme.split("/")[0]
        object_key = "/".join(path_without_scheme.split("/")[1:])

        # สร้าง Presigned URL (มีอายุ 15 นาที)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
                'ResponseContentDisposition': f'attachment; filename="{record["file_name"]}"'
            },
            ExpiresIn=900  # 15 นาที
        )

        # Redirect ให้เบราว์เซอร์ไปโหลดไฟล์ทันที (หรือจะ return เป็น JSON {"url": presigned_url} ก็ได้)
        return RedirectResponse(url=presigned_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. API: ค้นหาข้อมูลจาก MongoDB (UDTP Search)
# ==========================================
class UDTPSearchQuery(BaseModel):
    stage: str  # เช่น "3_ANALYZE", "4_VISUALIZE"
    scope_ids: List[str] = []
    schedule_ids: List[str] = []
    tags: List[str] = []
    limit: int = 50

@router.post("/insights/search")
async def search_mongodb_data(query: UDTPSearchQuery):
    """
    ค้นหาข้อมูล Insights หรือ Processed Data ใน MongoDB 
    โดยใช้ Logic UDTP: (Scope AND Schedule) OR Tags
    """
    try:
        # เชื่อมต่อ MongoDB
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.agentic_db
        collection = db.ai_insights # หรือ db.processed_data
        
        # สร้างเงื่อนไขการค้นหา (MongoDB Query Document)
        mongo_query = {"udtp.stage": query.stage}
        
        # สร้าง List สำหรับเก็บเงื่อนไข $or
        or_conditions = []
        
        # 1. เงื่อนไข Intersection (AND) ของ Scope และ Schedule
        if query.scope_ids or query.schedule_ids:
            and_conditions = []
            if query.scope_ids:
                and_conditions.append({"udtp.scope_ids": {"$in": query.scope_ids}})
            if query.schedule_ids:
                and_conditions.append({"udtp.schedule_ids": {"$in": query.schedule_ids}})
            
            if and_conditions:
                or_conditions.append({"$and": and_conditions})
                
        # 2. เงื่อนไข Union (OR) กับ Tags
        if query.tags:
            or_conditions.append({"udtp.tags": {"$in": query.tags}})
            
        # รวมเงื่อนไข $or เข้ากับ mongo_query หลัก (ถ้ามีการระบุเงื่อนไขมา)
        if or_conditions:
            mongo_query["$or"] = or_conditions

        # ดึงข้อมูลจาก MongoDB
        cursor = collection.find(mongo_query).limit(query.limit)
        results = []
        
        async for document in cursor:
            # แปลง ObjectId ให้เป็น String เพื่อให้ JSON Serialize ได้
            document["_id"] = str(document["_id"])
            results.append(document)
            
        return {
            "status": "success",
            "count": len(results),
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))