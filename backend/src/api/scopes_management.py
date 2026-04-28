from time import timezone

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncpg
import json
import os
import uuid
import boto3
import httpx # 👈 นำเข้า httpx
from datetime import datetime, time, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
import motor.motor_asyncio
import os

router = APIRouter(prefix="/api/v1/projects", tags=["Scope & Schedule Management"])

# ==========================================
# Configuration
# ==========================================
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://admin:password123@postgres:5432/agentic_db")
AIRFLOW_DAGS_CONFIG_DIR = os.getenv("AIRFLOW_DAGS_CONFIG_DIR", "/opt/airflow/config")
CONFIG_FILE_PATH = os.path.join(AIRFLOW_DAGS_CONFIG_DIR, "schedules.json")

# เชื่อมต่อ MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@mongodb:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["agentic_db"]
insights_collection = db["ai_insights"]

# ==========================================
# Pydantic Models
# ==========================================
class ScopeCreate(BaseModel):
    user_id: str
    name: str
    description: Optional[str] = ""
    goal: Optional[str] = ""
    schedule_mode: str = "MANUAL"
    status: str = "ACTIVE"

class ScopeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[str] = None
    schedule_mode: Optional[str] = None
    status: Optional[str] = None

class ScheduleCreate(BaseModel):
    name: str
    task_mode: str
    execution_type: str # 'CRON', 'ONCE', 'CONTINUOUS'
    cron_expression: Optional[str] = None
    is_sequential: bool = True

class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    task_mode: Optional[str] = None
    execution_type: Optional[str] = None
    restart_policy: Optional[str] = None
    cron_expression: Optional[str] = None
    is_sequential: Optional[bool] = None

class TaskParameterUpdate(BaseModel):
    arguments: Dict[str, Any]

class TaskConnectionValidate(BaseModel):
    source_tool_id: str
    target_tool_id: str

class TaskCreate(BaseModel):
    task_type: str
    tool_id: str
    engine_type: str = "AIRFLOW_DAG"
    depends_on_task_id: Optional[str] = None
    execution_order: int = 1
    arguments: Dict[str, Any] = {}
    ui_position: Dict[str, float] = {"x": 100, "y": 100} # 👈 เพิ่ม

class TaskPositionUpdate(BaseModel):
    ui_position: Dict[str, float]

class TaskDependencyUpdate(BaseModel):
    depends_on_task_id: Optional[str]
class TaskUpdate(BaseModel):
    task_type: Optional[str] = None
    tool_id: Optional[str] = None
    engine_type: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None

# ==========================================
# Core Logic: Export JSON for Airflow
# ==========================================
async def export_schedules_to_json():
    """ดึงข้อมูล Schedules และ Tasks แบบที่มี CRON ไปสร้างเป็นไฟล์ JSON ให้ Airflow อ่านแบบ Dynamic"""
    os.makedirs(AIRFLOW_DAGS_CONFIG_DIR, exist_ok=True)
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = """
        SELECT 
            s.id as schedule_id, s.scope_id, s.cron_expression,
            t.id as task_id, t.task_type, t.depends_on_task_id, t.arguments, t.execution_order,
            tl.script_url, tl.input_schema, tl.output_schema
        FROM schedules s
        LEFT JOIN tasks t ON s.id = t.schedule_id
        LEFT JOIN tools tl ON t.tool_id = tl.id
        WHERE s.execution_type = 'CRON' AND s.cron_expression IS NOT NULL
        ORDER BY s.id, t.execution_order ASC
    """
    rows = await conn.fetch(query)
    await conn.close()

    schedules_dict = {}
    for r in rows:
        sch_id = str(r['schedule_id'])
        if sch_id not in schedules_dict:
            schedules_dict[sch_id] = {
                "schedule_id": sch_id,
                "scope_id": str(r['scope_id']),
                "cron": r['cron_expression'],
                "tasks": []
            }
        
        if r['task_id']:
            schedules_dict[sch_id]["tasks"].append({
                "task_id": str(r['task_id']),
                "task_type": r['task_type'],
                "depends_on_task_id": str(r['depends_on_task_id']) if r['depends_on_task_id'] else None,
                "arguments": json.loads(r['arguments']) if isinstance(r['arguments'], str) else (r['arguments'] or {}),
                "script_url": r['script_url'],
                "input_schema": json.loads(r['input_schema']) if isinstance(r['input_schema'], str) else (r['input_schema'] or {}),
                "output_schema": json.loads(r['output_schema']) if isinstance(r['output_schema'], str) else (r['output_schema'] or {})
            })

    final_output = list(schedules_dict.values())
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(final_output, f, indent=4)
        
    print(f"✅ Exported {len(final_output)} schedules to JSON for Airflow.")

    AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://agentic_airflow_webserver:8080/api/v2")
    AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
    AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
    parsed_url = urlparse(AIRFLOW_API_URL)
    AIRFLOW_BASE_URL = f"{parsed_url.scheme}://{parsed_url.netloc}"


# ==========================================
# 1. Scope APIs
# ==========================================
@router.get("/scopes")
async def get_scopes():
    conn = await asyncpg.connect(POSTGRES_DSN)
    # 👈 ดึงข้อมูลมาให้ครบทุกฟิลด์
    query = """
        SELECT id, name, description, goal, schedule_mode, status 
        FROM scopes ORDER BY created_at DESC
    """
    rows = await conn.fetch(query)
    await conn.close()
    
    return {
        "status": "success", 
        "data": [{
            "id": str(r['id']), 
            "name": r['name'],
            "description": r['description'],
            "goal": r['goal'],
            "schedule_mode": r['schedule_mode'],
            "status": r['status']
        } for r in rows]
    }

@router.post("/scopes")
async def create_scope(scope: ScopeCreate):
    try:
        conn = await asyncpg.connect(POSTGRES_DSN)
        query = """
            INSERT INTO scopes (user_id, name, description, goal, schedule_mode, status)
            VALUES ($1::uuid, $2, $3, $4, $5, $6) RETURNING id
        """
        # บันทึกข้อมูลลง Database
        scope_id = await conn.fetchval(
            query, 
            scope.user_id, 
            scope.name, 
            scope.description, 
            scope.goal, 
            scope.schedule_mode, 
            scope.status
        )
        await conn.close()
        
        return {"status": "success", "scope_id": str(scope_id)}
    except Exception as e:
        # ดัก Error ไว้เผื่อมีปัญหาตอน Insert จะได้รู้สาเหตุชัดๆ
        raise HTTPException(status_code=500, detail=f"Failed to create scope: {str(e)}")

@router.put("/scopes/{scope_id}")
async def update_scope(scope_id: str, updates: ScopeUpdate):
    # 👈 ใช้ exclude_unset=True เพื่อเอาเฉพาะค่าที่ Frontend ส่งมาจริงๆ
    update_data = updates.dict(exclude_unset=True) 
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(update_data.keys())])
    values = list(update_data.values())
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = f"UPDATE scopes SET {set_clause} WHERE id = $1::uuid RETURNING id"
    updated_id = await conn.fetchval(query, scope_id, *values)
    await conn.close()
    
    if not updated_id:
        raise HTTPException(status_code=404, detail="Scope not found")
    return {"status": "success", "message": "Scope updated"}

# ==========================================
# 2. Schedule APIs
# ==========================================
@router.post("/scopes/{scope_id}/schedules")
async def create_schedule(scope_id: str, schedule: ScheduleCreate, background_tasks: BackgroundTasks):
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = """
        INSERT INTO schedules (scope_id, name, task_mode, execution_type, cron_expression, is_sequential)
        VALUES ($1::uuid, $2, $3, $4, $5, $6) RETURNING id
    """
    # 👈 ส่งค่า schedule.name เข้าไปด้วย
    schedule_id = await conn.fetchval(
        query, scope_id, schedule.name, schedule.task_mode, schedule.execution_type, 
        schedule.cron_expression, schedule.is_sequential
    )
    await conn.close()

    if schedule.execution_type == 'CRON':
        background_tasks.add_task(export_schedules_to_json)

    return {"status": "success", "schedule_id": schedule_id}

@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, updates: ScheduleUpdate, background_tasks: BackgroundTasks):
    # exclude_unset=True คือการเอาเฉพาะฟิลด์ที่ส่งค่ามาจริงๆ เท่านั้น
    update_data = updates.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # สร้าง SET clause แบบ Dynamic (รองรับการอัปเดต name อัตโนมัติ)
    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(update_data.keys())])
    values = list(update_data.values())
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = f"UPDATE schedules SET {set_clause} WHERE id = $1::uuid RETURNING id"
    updated_id = await conn.fetchval(query, schedule_id, *values)
    await conn.close()
    
    if not updated_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    background_tasks.add_task(export_schedules_to_json)
    return {"status": "success", "message": "Schedule updated. Airflow is syncing."}

# ==========================================
# 3. Task & Tools Logic APIs
# ==========================================
@router.put("/tasks/{task_id}/parameters")
async def update_task_parameters(task_id: str, payload: TaskParameterUpdate, background_tasks: BackgroundTasks):
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "UPDATE tasks SET arguments = $1::jsonb WHERE id = $2::uuid RETURNING id"
    updated_id = await conn.fetchval(query, json.dumps(payload.arguments), task_id)
    await conn.close()

    if not updated_id:
        raise HTTPException(status_code=404, detail="Task not found")

    background_tasks.add_task(export_schedules_to_json)
    return {"status": "success", "message": "Task parameters updated. Airflow is syncing."}

@router.post("/validate_task_connection")
async def validate_connection(data: TaskConnectionValidate):
    """ตรวจสอบว่า Output Format ของ Tool ต้นทาง ตรงกับ Input Format ของ Tool ปลายทางหรือไม่"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "SELECT id, input_schema, output_schema FROM tools WHERE id IN ($1::uuid, $2::uuid)"
    tools = await conn.fetch(query, data.source_tool_id, data.target_tool_id)
    await conn.close()

    if len(tools) != 2:
        raise HTTPException(status_code=404, detail="One or both tools not found")

    tool_dict = {str(t['id']): t for t in tools}
    source_out = tool_dict[data.source_tool_id].get('output_schema', {}) or {}
    target_in = tool_dict[data.target_tool_id].get('input_schema', {}) or {}

    # Logic เปรียบเทียบ File Type (ประยุกต์ตาม Schema จริงของคุณเก้าได้เลย)
    if source_out.get('file_type') != target_in.get('expected_file_type'):
        return {"valid": False, "reason": f"File type mismatch: Output is {source_out.get('file_type')} but Input expects {target_in.get('expected_file_type')}"}
    
    return {"valid": True, "message": "Tasks can be securely connected"}

# ==========================================
# 4. GET Scopes API (ดึงรายชื่อ Scope ไปแสดงใน Dropdown)
# ==========================================
@router.get("/scopes")
async def get_scopes():
    conn = await asyncpg.connect(POSTGRES_DSN)
    # ดึง Scope ทั้งหมดเรียงตามเวลาที่สร้างล่าสุด
    rows = await conn.fetch("SELECT id, name FROM scopes ORDER BY created_at DESC")
    await conn.close()
    
    return {
        "status": "success", 
        "data": [{"id": str(r['id']), "name": r['name']} for r in rows]
    }

# ==========================================
# 5. Upload Tool API (อัปโหลดสคริปต์ขึ้น MinIO และบันทึกลง Database)
# ==========================================
@router.post("/tools/upload")
async def upload_tool(
    name: str = Form(...),
    language: str = Form(...), # 'Python', 'Go', 'C++'
    author_type: str = Form(...), # 'HUMAN', 'AI_GENERATED'
    file: UploadFile = File(...)
):
    try:
        # 1. อัปโหลดไฟล์ขึ้น MinIO
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://minio:9000'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
            region_name='us-east-1'
        )
        
        bucket = "ai-tool-scripts"
        folder = "traditional-logic" if author_type == "HUMAN" else "ai-inference"
        file_path = f"{folder}/{file.filename}"
        
        # อัปโหลดแบบ Stream
        s3.upload_fileobj(file.file, bucket, file_path)
        script_url = f"s3a://{bucket}/{file_path}"
        
        # 2. บันทึก Metadata ลง PostgreSQL
        conn = await asyncpg.connect(POSTGRES_DSN)
        query = """
            INSERT INTO tools (name, language, script_url, author_type) 
            VALUES ($1, $2, $3, $4) RETURNING id
        """
        tool_id = await conn.fetchval(query, name, language, script_url, author_type)
        await conn.close()
        
        return {
            "status": "success", 
            "message": "Tool uploaded successfully",
            "tool_id": str(tool_id),
            "script_url": script_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ==========================================
# 6. GET API (สำหรับดึงข้อมูลไปทำ Dropdown ใน Frontend)
# ==========================================
@router.get("/tools")
async def get_tools():
    """ดึงรายชื่อ Tools ทั้งหมดที่มีในระบบ"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    rows = await conn.fetch("SELECT id, name, language FROM tools ORDER BY created_at DESC")
    await conn.close()
    return {"status": "success", "data": [{"id": str(r['id']), "name": r['name'], "language": r['language']} for r in rows]}

@router.get("/scopes/{scope_id}/schedules")
async def get_schedules_by_scope(scope_id: str):
    """ดึงตารางเวลาทั้งหมดที่อยู่ใน Scope นั้นๆ"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = """
        SELECT id, name, execution_type, cron_expression, task_mode, restart_policy, is_sequential 
        FROM schedules WHERE scope_id = $1::uuid ORDER BY created_at DESC
    """
    rows = await conn.fetch(query, scope_id)
    await conn.close()
    
    return {
        "status": "success", 
        "data": [{
            "id": str(r['id']), 
            "name": r['name'], 
            "type": r['execution_type'], 
            "cron": r['cron_expression'],
            "task_mode": r['task_mode'],
            "restart_policy": r['restart_policy'],
            "is_sequential": r['is_sequential']
        } for r in rows]
    }

# 2. แก้ไข GET /schedules/{schedule_id}/tasks
@router.get("/schedules/{schedule_id}/tasks")
async def get_tasks_by_schedule(schedule_id: str):
    conn = await asyncpg.connect(POSTGRES_DSN)
    
    # 👈 ดึง tool_id และ engine_type เพิ่ม เพื่อให้ Frontend นำไปใช้ในหน้า Modal แก้ไข Task
    query = """
        SELECT id, task_type, tool_id, engine_type, execution_order, depends_on_task_id, ui_position, arguments 
        FROM tasks 
        WHERE schedule_id = $1::uuid 
        ORDER BY execution_order ASC
    """
    rows = await conn.fetch(query, schedule_id)
    await conn.close()
    
    return {
        "status": "success", 
        "data": [{
            "id": str(r['id']), 
            "task_type": r['task_type'], 
            "tool_id": str(r['tool_id']) if r['tool_id'] else "", # เผื่อกรณี Task บางประเภทไม่มี tool_id
            "engine_type": r['engine_type'] if r['engine_type'] else "AIRFLOW_DAG", # Default ตาม Frontend
            "order": r['execution_order'],
            "depends_on_task_id": str(r['depends_on_task_id']) if r['depends_on_task_id'] else None,
            "ui_position": json.loads(r['ui_position']) if isinstance(r['ui_position'], str) else (r['ui_position'] or {"x": 250, "y": 150}),
            "arguments": json.loads(r['arguments']) if isinstance(r['arguments'], str) else (r['arguments'] or {})
        } for r in rows]
    }

# 3. เพิ่ม API สำหรับอัปเดต X, Y ตอนลากกล่อง
@router.put("/tasks/{task_id}/position")
async def update_task_position(task_id: str, data: TaskPositionUpdate, background_tasks: BackgroundTasks):
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "UPDATE tasks SET ui_position = $1::jsonb WHERE id = $2::uuid"
    await conn.execute(query, json.dumps(data.ui_position), task_id)
    await conn.close()
    background_tasks.add_task(export_schedules_to_json)
    return {"status": "success"}

# 4. เพิ่ม API สำหรับอัปเดตเส้นเชื่อม (Dependencies)
@router.put("/tasks/{task_id}/dependency")
async def update_task_dependency(task_id: str, data: TaskDependencyUpdate, background_tasks: BackgroundTasks):
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "UPDATE tasks SET depends_on_task_id = $1::uuid WHERE id = $2::uuid"
    await conn.execute(query, data.depends_on_task_id, task_id)
    await conn.close()
    background_tasks.add_task(export_schedules_to_json)
    return {"status": "success"}

# ==========================================
# 7. POST API สร้าง Task ลงใน Schedule
# ==========================================
@router.post("/schedules/{schedule_id}/tasks")
async def create_task(schedule_id: str, task: TaskCreate, background_tasks: BackgroundTasks):
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = """
        INSERT INTO tasks (schedule_id, task_type, tool_id, engine_type, depends_on_task_id, execution_order, arguments)
        VALUES ($1::uuid, $2, $3::uuid, $4, $5::uuid, $6, $7::jsonb) RETURNING id
    """
    # จัดการกรณีที่ Frontend ส่งค่าว่างมาให้เป็น NULL
    dep_id = task.depends_on_task_id if task.depends_on_task_id else None
    
    task_id = await conn.fetchval(
        query, schedule_id, task.task_type, task.tool_id, 
        task.engine_type, dep_id, task.execution_order, json.dumps(task.arguments)
    )
    await conn.close()
    
    # สั่งให้ Airflow อัปเดต DAG ใหม่ทันที
    background_tasks.add_task(export_schedules_to_json)
    
    return {"status": "success", "task_id": str(task_id)}

@router.put("/tasks/{task_id}")
async def update_task_full(task_id: str, updates: TaskUpdate, background_tasks: BackgroundTasks):
    update_data = updates.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # ถ้ามีการอัปเดต arguments ต้องแปลงเป็น JSON String ก่อนลง DB
    if 'arguments' in update_data:
        update_data['arguments'] = json.dumps(update_data['arguments'])

    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(update_data.keys())])
    values = list(update_data.values())
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = f"UPDATE tasks SET {set_clause} WHERE id = $1::uuid RETURNING id"
    updated_id = await conn.fetchval(query, task_id, *values)
    await conn.close()
    
    if not updated_id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    background_tasks.add_task(export_schedules_to_json)
    return {"status": "success", "message": "Task updated"}

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, background_tasks: BackgroundTasks):
    conn = await asyncpg.connect(POSTGRES_DSN)
    # จะลบ Task ต้องลบเส้นเชื่อมที่ชี้มาหามันด้วย (แต่เราตั้ง ON DELETE SET NULL/CASCADE ไว้ใน init.sql แล้ว)
    query = "DELETE FROM tasks WHERE id = $1::uuid RETURNING id"
    deleted_id = await conn.fetchval(query, task_id)
    await conn.close()
    
    if not deleted_id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    background_tasks.add_task(export_schedules_to_json)
    return {"status": "success", "message": "Task deleted"}

# ==========================================
# API สำหรับ Delete Scope & Schedule
# ==========================================
@router.delete("/scopes/{scope_id}")
async def delete_scope(scope_id: str, background_tasks: BackgroundTasks):
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "DELETE FROM scopes WHERE id = $1::uuid RETURNING id"
    deleted_id = await conn.fetchval(query, scope_id)
    await conn.close()
    
    if not deleted_id:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    background_tasks.add_task(export_schedules_to_json)
    return {"status": "success", "message": "Scope deleted"}

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, background_tasks: BackgroundTasks):
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "DELETE FROM schedules WHERE id = $1::uuid RETURNING id"
    deleted_id = await conn.fetchval(query, schedule_id)
    await conn.close()
    
    if not deleted_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    # สั่งให้ Airflow อัปเดตไฟล์ JSON ทันทีที่ตารางเวลาถูกลบ
    background_tasks.add_task(export_schedules_to_json)
    return {"status": "success", "message": "Schedule deleted"}


@router.get("/schedules/{schedule_id}/insights")
async def get_schedule_insights(schedule_id: str):
    """ดึงข้อมูล JSON Blocks ล่าสุดของ Schedule นั้นๆ จาก MongoDB"""
    try:
        # ค้นหาผลลัพธ์ล่าสุดของ schedule นี้ เรียงตามเวลาล่าสุด (ลดหลั่นลงมา)
        insight = await insights_collection.find_one(
            {"schedule_id": schedule_id},
            sort=[("created_at", -1)] # เอาอันล่าสุด
        )

        if not insight or "blocks" not in insight:
            return {"status": "success", "data": []} # ถ้าไม่มีข้อมูล ส่ง Array ว่างกลับไป

        # ส่ง JSON Blocks กลับไปให้ Frontend
        return {"status": "success", "data": insight["blocks"]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))