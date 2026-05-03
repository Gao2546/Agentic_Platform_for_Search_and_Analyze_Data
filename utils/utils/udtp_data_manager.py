import os
import json
import hashlib
import boto3
import psycopg2
import pandas as pd
import io
from PIL import Image
import cv2
import tempfile
from psycopg2.extras import Json
from typing import Dict, Any, List, Optional, Union

class UDTPDataManager:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://minio:9000'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
            region_name='us-east-1'
        )
        self.bucket_name = "processed-data"
        self.db_dsn = os.getenv("POSTGRES_DSN", "postgresql://admin:password123@postgres:5432/agentic_db")

    def _get_db_connection(self):
        return psycopg2.connect(self.db_dsn)

    def _generate_deterministic_metadata(self, data_bytes: bytes, file_extension: str) -> Dict[str, Any]:
        """Deep Metadata Inspection สำหรับไฟล์หลากหลายประเภท"""
        asset_id = hashlib.sha256(data_bytes).hexdigest()
        size_byte = len(data_bytes)
        ext = file_extension.lower().replace(".", "")
        
        # Mapping Mime Type พื้นฐาน
        mime_map = {
            "json": "application/json", "csv": "text/csv", "parquet": "application/parquet",
            "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "mp4": "video/mp4", "txt": "text/plain", "pdf": "application/pdf"
        }
        mime_type = mime_map.get(ext, "application/octet-stream")

        custom_metadata = {"extension": ext}

        try:
            # 1. ข้อมูลตาราง (Tabular Data)
            if ext in ['csv', 'parquet']:
                df = pd.read_csv(io.BytesIO(data_bytes)) if ext == 'csv' else pd.read_parquet(io.BytesIO(data_bytes))
                custom_metadata["columns"] = list(df.columns)
                custom_metadata["row_count"] = len(df)
                custom_metadata["column_count"] = len(df.columns)

            # 2. รูปภาพ (Images)
            elif ext in ['png', 'jpg', 'jpeg']:
                with Image.open(io.BytesIO(data_bytes)) as img:
                    w, h = img.size
                    mode = img.mode # e.g., RGB (3 channels), RGBA (4)
                    custom_metadata["width"] = w
                    custom_metadata["height"] = h
                    custom_metadata["channels"] = len(img.getbands())
                    custom_metadata["aspect_ratio"] = round(w / h, 2)

            # 3. วิดีโอ (Videos) - ใช้ Temporary File เพื่อให้ OpenCV อ่านได้
            elif ext in ['mp4', 'avi', 'mov']:
                with tempfile.NamedTemporaryFile(suffix=f".{ext}") as tmp:
                    tmp.write(data_bytes)
                    tmp.flush()
                    cap = cv2.VideoCapture(tmp.name)
                    custom_metadata["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    custom_metadata["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    custom_metadata["fps"] = round(cap.get(cv2.CAP_PROP_FPS), 2)
                    custom_metadata["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    cap.release()

            # 4. ข้อความ (Text Files)
            elif ext == 'txt':
                content = data_bytes.decode('utf-8')
                custom_metadata["line_count"] = len(content.splitlines())
                custom_metadata["word_count"] = len(content.split())
                custom_metadata["encoding"] = "utf-8"

        except Exception as e:
            custom_metadata["inspection_error"] = str(e)

        return {
            "asset_id": asset_id,
            "size_byte": size_byte,
            "mime_type": mime_type,
            "hash_algorithm": "SHA-256",
            "custom_metadata": custom_metadata
        }

    def save_data(self, data: Union[Dict, str, bytes], stage: str, scope_id: str, 
                  schedule_id: str, task_id: str, tags: List[str] = None, 
                  file_extension: str = "json") -> str:
        
        # เตรียม Data Bytes
        if isinstance(data, (dict, list)):
            data_bytes = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data

        # สร้าง Metadata
        meta = self._generate_deterministic_metadata(data_bytes, file_extension)
        asset_id = meta["asset_id"]
        
        # กำหนด Path ตามมาตรฐานประเภทของ_task/scope_id/schedule_id/task_id/asset_id
        object_key = f"{stage}/{scope_id}/{schedule_id}/{task_id}/{asset_id}.{file_extension}"
        file_path = f"s3a://{self.bucket_name}/{object_key}"

        # Upload ลง MinIO
        self.s3_client.put_object(
            Bucket=self.bucket_name, Key=object_key, 
            Body=data_bytes, ContentType=meta["mime_type"]
        )

        # บันทึกลง PostgreSQL (รวม metadata ทั้งหมดลงใน attributes)
        full_attributes = {
            "size_byte": meta["size_byte"],
            "hash_algorithm": meta["hash_algorithm"],
            "custom_metadata": meta["custom_metadata"]
        }

        query = """
            INSERT INTO file_assets (
                asset_id, file_name, file_path, mime_type, size_byte, attributes, 
                udtp_stage, udtp_scope_ids, udtp_schedule_ids, udtp_task_ids, udtp_tags
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, ARRAY[%s]::uuid[], ARRAY[%s]::uuid[], ARRAY[%s]::uuid[], %s::text[]
            ) ON CONFLICT (asset_id) DO UPDATE SET 
                updated_at = CURRENT_TIMESTAMP,
                udtp_scope_ids = ARRAY(SELECT DISTINCT UNNEST(file_assets.udtp_scope_ids || EXCLUDED.udtp_scope_ids)),
                udtp_tags = ARRAY(SELECT DISTINCT UNNEST(file_assets.udtp_tags || EXCLUDED.udtp_tags));
        """
        
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (
                    asset_id, f"{asset_id}.{file_extension}", file_path, meta["mime_type"], 
                    meta["size_byte"], Json(full_attributes), stage, scope_id, schedule_id, task_id, tags or []
                ))
            conn.commit()
        finally:
            conn.close()

        return file_path

    def search_data(self, expected_metadata: Dict[str, Any] = None, **kwargs) -> List[Dict[str, Any]]:
        """ค้นหาข้อมูลแบบยืดหยุ่น: กรองเฉพาะ Key ที่ระบุใน expected_metadata"""
        
        where_clauses = []
        params = {}

        # กรองพื้นฐาน (stage, scope_id, etc.)
        for key in ['stage', 'scope_id', 'schedule_id', 'task_id']:
            if kwargs.get(key):
                col = f"udtp_{key}s" if key != 'stage' else "udtp_stage"
                if key == 'stage':
                    where_clauses.append(f"{col} = %({key})s")
                else:
                    where_clauses.append(f"%({key})s = ANY({col})")
                params[key] = kwargs[key]

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT asset_id, file_path, mime_type, attributes FROM file_assets WHERE {where_sql}"

        conn = self._get_db_connection()
        matched_results = []
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                for row in cur.fetchall():
                    item = dict(zip(columns, row))
                    db_attr = item['attributes']
                    
                    # Logic: Flexible Metadata Validation
                    is_match = True
                    if expected_metadata:
                        # รวมเอาทั้ง attributes ชั้นนอก และ custom_metadata มาเช็ค
                        flat_db_meta = {**db_attr, **db_attr.get('custom_metadata', {})}
                        
                        for k, v in expected_metadata.items():
                            # ถ้า Key ที่คาดหวัง "ไม่มี" หรือ "ไม่ตรง" ใน DB -> ข้ามไฟล์นี้
                            if k not in flat_db_meta or flat_db_meta[k] != v:
                                is_match = False
                                break
                    
                    if is_match:
                        matched_results.append(item)
        finally:
            conn.close()

        return matched_results

    def delete_data(self, stage: str, scope_id: str = None, schedule_id: str = None, task_id: str = None, asset_id: str = None):
        """ลบข้อมูลแบบ Hierarchical (ลบลดหลั่นตาม Path)"""
        
        # 1. สร้าง Path Prefix สำหรับลบใน MinIO
        path_parts = [stage]
        if scope_id: path_parts.append(scope_id)
        if schedule_id: path_parts.append(schedule_id)
        if task_id: path_parts.append(task_id)
        
        prefix = "/".join(path_parts) + "/"
        if asset_id:
            prefix = f"{prefix}{asset_id}" # ระบุเจาะจงไฟล์
            
        # ลบไฟล์ใน MinIO
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': objects_to_delete})

        # 2. ลบข้อมูลจาก PostgreSQL (ใช้ LIKE ตามรูปแบบ file_path)
        path_wildcard = f"s3a://{self.bucket_name}/{prefix}%"
        query = "DELETE FROM file_assets WHERE file_path LIKE %s"
        
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (path_wildcard,))
            conn.commit()
        finally:
            conn.close()
            
        return {"status": "success", "deleted_path_prefix": path_wildcard}