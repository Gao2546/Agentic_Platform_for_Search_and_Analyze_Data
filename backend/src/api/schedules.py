from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
import os
import uuid
import asyncpg
from urllib.parse import urlparse
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Router สำหรับจัดการ Schedules
router = APIRouter(prefix="/api/v1/schedules", tags=["Schedules"])

# ==========================================
# 1. Models สำหรับรับ Request Body
# ==========================================
class TriggerPayload(BaseModel):
    # รองรับการส่ง Parameter แบบ Dynamic มหาศาล
    override_args: Dict[str, Any] = {}
    event_trigger_source: Optional[str] = None

# ==========================================
# 2. Configuration & Connections
# ==========================================
# 📌 แนะนำให้ตั้งค่าเป็น "http://agentic_airflow_webserver:8080/public" (หรือ /api/v2 แล้วแต่เวอร์ชั่นย่อยของ Airflow 3)
AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://agentic_airflow_webserver:8080/api/v2")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://admin:password123@postgres:5432/agentic_db")

# ดึง Base URL ออกมาอัตโนมัติ (เช่น http://agentic_airflow_webserver:8080)
parsed_url = urlparse(AIRFLOW_API_URL)
AIRFLOW_BASE_URL = f"{parsed_url.scheme}://{parsed_url.netloc}"

# ==========================================
# 3. Trigger Endpoint
# ==========================================
@router.post("/trigger/{schedule_id}")
async def trigger_airflow_dag(schedule_id: uuid.UUID, payload: TriggerPayload):
    schedule_id_str = str(schedule_id)
    
    # ---------------------------------------------------------
    # STEP 1: ค้นหา Scope ID จาก Database เพื่อประกอบชื่อ DAG
    # ---------------------------------------------------------
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "SELECT scope_id FROM schedules WHERE id = $1::uuid"
    record = await conn.fetchrow(query, schedule_id_str)
    await conn.close()

    if not record:
        raise HTTPException(status_code=404, detail="Schedule not found in database")
        
    scope_id_str = str(record['scope_id'])

    # ประกอบชื่อ DAG ให้ตรงกับที่ agentic_dag_factory.py สร้างไว้
    target_dag_id = f"dynamic_scope_{scope_id_str[:8]}_sch_{schedule_id_str[:8]}"

    # ---------------------------------------------------------
    # STEP 2: เตรียม Configuration สำหรับ Airflow
    # ---------------------------------------------------------
    airflow_conf = {
        "schedule_id": schedule_id_str,
        "scope_id": scope_id_str,
        "trigger_source": payload.event_trigger_source,
        "runtime_overrides": payload.override_args # ค่าที่จะไปทับ arguments ใน DB ชั่วคราว
    }

    airflow_trigger_url = f"{AIRFLOW_API_URL}/dags/{target_dag_id}/dagRuns"
    
    # 📌 สร้างเวลาปัจจุบัน (UTC) ในรูปแบบ ISO 8601 ที่ Airflow ต้องการ
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    airflow_payload = {
        "logical_date": now_utc,
        "conf": airflow_conf,
    }

    # ---------------------------------------------------------
    # STEP 3: ยิง API ไปหา Airflow
    # ---------------------------------------------------------
    try:
        async with httpx.AsyncClient() as client:
            
            # ขอ JWT Token จาก Airflow
            token_url = f"{AIRFLOW_BASE_URL}/auth/token"
            auth_data = {
                "username": AIRFLOW_USER,
                "password": AIRFLOW_PASSWORD
            }
            
            token_response = await client.post(token_url, json=auth_data)
            
            if token_response.status_code not in (200, 201):
                raise HTTPException(
                    status_code=401, 
                    detail=f"Airflow Authentication Failed. Status: {token_response.status_code}, Msg: {token_response.text}"
                )
            
            # สกัด Token ออกมาจาก Response
            access_token = token_response.json().get("access_token")

            # ส่งคำสั่ง Trigger DAG พร้อมแนบ Token
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = await client.post(
                airflow_trigger_url,
                headers=headers,
                json=airflow_payload
            )
            
            # เช็คว่า Airflow รับคำสั่งสำเร็จหรือไม่ (HTTP 200 หรือ 201)
            if response.status_code not in (200, 201):
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to trigger Airflow DAG '{target_dag_id}'. Status: {response.status_code}, Msg: {response.text}"
                )
            
            response_data = response.json()
            
            return {
                "status": "success",
                "message": f"Successfully triggered DAG '{target_dag_id}'",
                "schedule_id": schedule_id_str,
                "airflow_run_id": response_data.get("dag_run_id"),
                "queued_at": response_data.get("execution_date", response_data.get("logical_date"))
            }

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503, 
            detail=f"Airflow API is unreachable: {str(exc)}"
        )