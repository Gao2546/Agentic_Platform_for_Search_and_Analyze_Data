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
import urllib.parse

router = APIRouter(prefix="/api/v1/projects", tags=["Scope & Schedule Management"])

# ==========================================
# Configuration
# ==========================================
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://admin:password123@postgres:5432/agentic_db")
AIRFLOW_DAGS_CONFIG_DIR = os.getenv("AIRFLOW_DAGS_CONFIG_DIR", "/opt/airflow/config")
CONFIG_FILE_PATH = os.path.join(AIRFLOW_DAGS_CONFIG_DIR, "schedules.json")
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://ai-engine:8000/api/v1")

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
    goal: Optional[str] = None
    task_mode: str
    execution_type: str # 'CRON', 'ONCE', 'CONTINUOUS'
    cron_expression: Optional[str] = None
    is_sequential: bool = True

class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
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

class ToolUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    author_type: Optional[str] = None

class ToolSearchQuery(BaseModel):
    query: str
    tags: List[str] = []
    limit: int = 3

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
            tl.script_url, tl.input_schema, tl.output_schema, tl.dependencies
        FROM schedules s
        LEFT JOIN tasks t ON s.id = t.schedule_id
        LEFT JOIN tools tl ON t.tool_id = tl.id
        WHERE (s.execution_type = 'CRON' AND s.cron_expression IS NOT NULL) or s.execution_type = 'ONCE'
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
                "output_schema": json.loads(r['output_schema']) if isinstance(r['output_schema'], str) else (r['output_schema'] or {}),
                "dependencies": json.loads(r['dependencies']) if isinstance(r['dependencies'], str) else (r['dependencies'] or {})
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
# Background Task Helpers
# ==========================================
async def trigger_ai_schedule_planner(scope_id: str, goal: str):
    """เรียก Module 1 & 2 ให้ AI ออกแบบ Schedules ตาม Scope Goal"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            await client.post(
                f"{AI_ENGINE_URL}/generate/schedules",
                json={"scope_id": scope_id, "goal": goal}
            )
    except Exception as e:
        print(f"Failed to trigger AI Engine for Scope {scope_id}: {str(e)}")

async def trigger_ai_task_orchestrator(scope_id: str, schedule_id: str, schedule_goal: str):
    """เรียก Module 3 & 4 ให้ AI ค้นหา/สร้าง Tool และร้อยเรียงเป็น Task Pipeline"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            await client.post(
                f"{AI_ENGINE_URL}/generate/tasks",
                json={
                    "scope_id": scope_id,          # 👈 ส่ง scope_id เพิ่ม
                    "schedule_id": schedule_id, 
                    "schedule_goal": schedule_goal
                }
            )
    except Exception as e:
        print(f"Failed to trigger AI Engine for Schedule {schedule_id}: {str(e)}")


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
async def create_scope(scope: ScopeCreate, background_tasks: BackgroundTasks):
    try:
        conn = await asyncpg.connect(POSTGRES_DSN)
        query = """
            INSERT INTO scopes (user_id, name, description, goal, schedule_mode, status)
            VALUES ($1::uuid, $2, $3, $4, $5, $6) RETURNING id
        """
        scope_id = await conn.fetchval(
            query, scope.user_id, scope.name, scope.description, 
            scope.goal, scope.schedule_mode, scope.status
        )
        await conn.close()
        
        # 🚀 ถ้า Mode เป็น AI_AGENT ให้ส่งงานไปที่ AI Engine ทำงานเบื้องหลัง
        if scope.schedule_mode == "AI_AGENT" and scope.goal:
            background_tasks.add_task(trigger_ai_schedule_planner, str(scope_id), scope.goal)
        
        return {"status": "success", "scope_id": str(scope_id)}
    except Exception as e:
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
        INSERT INTO schedules (scope_id, name, goal, task_mode, execution_type, cron_expression, is_sequential)
        VALUES ($1::uuid, $2, $3, $4, $5, $6, $7) RETURNING id
    """
    schedule_id = await conn.fetchval(
        query, scope_id, schedule.name, schedule.goal, schedule.task_mode, schedule.execution_type,
        schedule.cron_expression, schedule.is_sequential
    )
    await conn.close()

    # จัดการ Airflow Sync สำหรับ CRON
    if schedule.execution_type == 'CRON' or schedule.execution_type == 'ONCE':
        background_tasks.add_task(export_schedules_to_json)

    # 🚀 ถ้า Task Mode เป็น AI_AGENT ให้ AI ไปสร้าง Pipeline ให้
    if schedule.task_mode == "AI_AGENT":
        # หมายเหตุ: อาจจะใช้ schedule.name เป็น goal ย่อย หรือเพิ่มฟิลด์ goal ในตาราง schedules ก็ได้
        background_tasks.add_task(trigger_ai_task_orchestrator, scope_id, str(schedule_id), schedule.goal)

    return {"status": "success", "schedule_id": str(schedule_id)}

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
    description: Optional[str] = Form(None), 
    description_for_vector_db: Optional[str] = Form(None),
    tags: Optional[str] = Form("[]"), 
    input_schema: Optional[str] = Form(None),
    output_schema: Optional[str] = Form(None),
    dependencies: Optional[str] = Form("{}"),
    file: UploadFile = File(...)
):
    try:
        # 1. แปลง tags จาก String เป็น List
        parsed_tags = json.loads(tags) if tags else []
        parsed_deps = json.loads(dependencies) if dependencies else {}

        # 2. อัปโหลดไฟล์ขึ้น MinIO
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
        
        s3.upload_fileobj(file.file, bucket, file_path)
        script_url = f"s3a://{bucket}/{file_path}"
        
        # 3. บันทึก Metadata ลง PostgreSQL (อัปเดต Query)
        conn = await asyncpg.connect(POSTGRES_DSN)
        query = """
            INSERT INTO tools (
                name, language, script_url, author_type, 
                description, description_for_vector_db, tags, input_schema, output_schema, dependencies
            ) 
            VALUES ($1, $2, $3, $4, $5, $6, $7::text[], $8, $9, $10::jsonb) RETURNING id
        """
        tool_id = await conn.fetchval(
            query, 
            name, 
            language, 
            script_url, 
            author_type,
            description,
            description_for_vector_db,
            parsed_tags,
            input_schema,
            output_schema,
            json.dumps(parsed_deps)
        )
        await conn.close()
        
        return {
            "status": "success", 
            "message": "Tool uploaded successfully",
            "tool_id": str(tool_id),
            "script_url": script_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/tools/search")
async def search_tools(search_params: ToolSearchQuery):
    """
    API สำหรับค้นหา Tool ด้วย Hybrid Search 
    (กรองด้วย tags จากตาราง tools และคำนวณ Vector 
    เทียบกับตาราง knowledge_embeddings)
    """
    try:
        # 📝 TODO: ฝั่ง Backend ต้องมีฟังก์ชันแปลง search_params.query เป็น Vector 
        # (เช่น เรียกใช้ OpenAI Embedding API หรือ Model ภายใน)
        # mock_vector = await get_embedding(search_params.query)
        mock_vector = "[0.1, 0.2, 0.3, ...]" # จำลอง Vector ที่ได้มา
        
        conn = await asyncpg.connect(POSTGRES_DSN)
        
        # ค้นหาโดยเชื่อมตาราง tools เข้ากับ knowledge_embeddings
        # กรอง tag เบื้องต้น (ถ้ามี) แล้วจัดเรียงตามความใกล้เคียงของ Vector
        if search_params.tags:
            query = """
                SELECT t.id, t.name, t.description, t.description_for_vector_db, t.tags, t.input_schema, t.output_schema 
                FROM tools t
                JOIN knowledge_embeddings k ON t.id = k.tool_id
                WHERE t.tags && $1::text[] 
                ORDER BY k.embedding <=> $2::vector
                LIMIT $3
            """
            rows = await conn.fetch(query, search_params.tags, mock_vector, search_params.limit)
        else:
            query = """
                SELECT t.id, t.name, t.description, t.description_for_vector_db, t.tags, t.input_schema, t.output_schema 
                FROM tools t
                JOIN knowledge_embeddings k ON t.id = k.tool_id
                ORDER BY k.embedding <=> $1::vector
                LIMIT $2
            """
            rows = await conn.fetch(query, mock_vector, search_params.limit)
            
        await conn.close()
        
        results = [{
            "tool_id": str(r['id']),
            "name": r['name'],
            "description": r['description'],
            "description_for_vector_db": r['description_for_vector_db'],
            "tags": r['tags'],
            "input_schema": json.loads(r['input_schema']) if isinstance(r['input_schema'], str) else (r['input_schema'] or {}),
            "output_schema": json.loads(r['output_schema']) if isinstance(r['output_schema'], str) else (r['output_schema'] or {})
        } for r in rows]

        return {"status": "success", "data": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ==========================================
# 6. GET API (สำหรับดึงข้อมูลไปทำ Dropdown ใน Frontend)
# ==========================================
@router.get("/tools")
async def get_tools():
    """ดึงรายชื่อ Tools ทั้งหมดที่มีในระบบ"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    rows = await conn.fetch("SELECT id, name, language, author_type, description, description_for_vector_db, tags, input_schema, output_schema, dependencies FROM tools ORDER BY created_at DESC")
    await conn.close()
    return {"status": "success", "data": [{"id": str(r['id']), "name": r['name'], "language": r['language'], "author_type": r['author_type'], "description": r['description'], "description_for_vector_db": r['description_for_vector_db'], "tags": r['tags'], "input_schema": json.loads(r['input_schema']) if isinstance(r['input_schema'], str) else (r['input_schema'] or {}), "output_schema": json.loads(r['output_schema']) if isinstance(r['output_schema'], str) else (r['output_schema'] or {}), "dependencies": json.loads(r['dependencies']) if isinstance(r['dependencies'], str) else (r['dependencies'] or {})} for r in rows]}

@router.get("/scopes/{scope_id}/schedules")
async def get_schedules_by_scope(scope_id: str):
    """ดึงตารางเวลาทั้งหมดที่อยู่ใน Scope นั้นๆ"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = """
        SELECT id, name, goal, execution_type, cron_expression, task_mode, restart_policy, is_sequential 
        FROM schedules WHERE scope_id = $1::uuid ORDER BY created_at DESC
    """
    rows = await conn.fetch(query, scope_id)
    await conn.close()
    
    return {
        "status": "success", 
        "data": [{
            "id": str(r['id']), 
            "name": r['name'], 
            "goal": r['goal'], 
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
    
@router.put("/tools/{tool_id}")
async def update_tool(
    tool_id: str,
    name: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    author_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    description_for_vector_db: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    input_schema: Optional[str] = Form(None),
    output_schema: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None) # 👈 ไฟล์เป็น Optional (เผื่อเขาแก้อย่างอื่นแต่ไม่เปลี่ยนไฟล์)
):
    try:
        update_data = {}
        if name is not None: update_data["name"] = name
        if language is not None: update_data["language"] = language
        if author_type is not None: update_data["author_type"] = author_type
        if description is not None: update_data["description"] = description
        if description_for_vector_db is not None: update_data["description_for_vector_db"] = description_for_vector_db
        if tags is not None: update_data["tags"] = json.loads(tags)
        if input_schema is not None: update_data["input_schema"] = input_schema
        if output_schema is not None: update_data["output_schema"] = output_schema

        # 🚀 ถ้าผู้ใช้แนบไฟล์ใหม่มา ให้โหลดไฟล์ขึ้น MinIO ก่อนเซฟลง Database
        if file:
            s3 = boto3.client(
                's3',
                endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://minio:9000'),
                aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
                aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
                region_name='us-east-1'
            )
            bucket = "ai-tool-scripts"
            
            # เช็คโฟลเดอร์จาก author_type ถ้ามีการส่งมา หรือดึงจาก DB
            current_author_type = update_data.get("author_type", "HUMAN") # fallback value
            folder = "traditional-logic" if current_author_type == "HUMAN" else "ai-inference"
            file_path = f"{folder}/{file.filename}"
            
            s3.upload_fileobj(file.file, bucket, file_path)
            update_data["script_url"] = f"s3a://{bucket}/{file_path}" # เพิ่ม URL ใหม่เข้าไปใน Dict ที่จะอัปเดต

        if not update_data:
            return {"status": "success", "message": "No data to update"}

        # ประกอบคำสั่ง SQL แบบ Dynamic
        set_clauses = []
        for i, k in enumerate(update_data.keys()):
            if k == "tags":
                set_clauses.append(f"{k} = ${i+2}::text[]") # ใส่ Cast ::text[] ให้ array
            elif k in ["input_schema", "output_schema"]:
                set_clauses.append(f"{k} = ${i+2}::jsonb") # ใส่ Cast ::jsonb ให้ schema
            else:
                set_clauses.append(f"{k} = ${i+2}")
                
        set_clause_str = ", ".join(set_clauses)
        values = list(update_data.values())
        
        conn = await asyncpg.connect(POSTGRES_DSN)
        query = f"UPDATE tools SET {set_clause_str} WHERE id = $1::uuid RETURNING id"
        updated_id = await conn.fetchval(query, tool_id, *values)
        await conn.close()
        
        if not updated_id:
            raise HTTPException(status_code=404, detail="Tool not found")
            
        return {"status": "success", "message": "Tool updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tools/{tool_id}")
async def delete_tool(tool_id: str):
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "DELETE FROM tools WHERE id = $1::uuid RETURNING id"
    await conn.fetchval(query, tool_id)
    await conn.close()
    return {"status": "success"}


@router.get("/tools/{tool_id}/preview")
async def preview_tool_file(tool_id: str):
    """API สำหรับดึงเนื้อหาไฟล์โค้ดของ Tool ออกมาดูตัวอย่าง"""
    try:
        # 1. ดึง script_url จาก Database
        conn = await asyncpg.connect(POSTGRES_DSN)
        script_url = await conn.fetchval("SELECT script_url FROM tools WHERE id = $1::uuid", tool_id)
        await conn.close()
        
        if not script_url:
            raise HTTPException(status_code=404, detail="Tool script not found")
            
        # 2. แปลง s3a://bucket/path ให้เป็น bucket และ key
        # ตัวอย่าง: s3a://ai-tool-scripts/traditional-logic/script.py
        parsed_url = urllib.parse.urlparse(script_url)
        bucket = parsed_url.netloc
        key = parsed_url.path.lstrip('/') # ตัด / ตัวหน้าสุดออก
        
        # 3. ดึงไฟล์จาก MinIO
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://minio:9000'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
            region_name='us-east-1'
        )
        
        response = s3.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read().decode('utf-8')
        
        return {"status": "success", "content": file_content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tools/{tool_id}/details")
async def get_tool_details(tool_id: str):
    """API สำหรับดึงรายละเอียดของ Tool มาแสดงในหน้า Modal แก้ไข"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    row = await conn.fetchrow("SELECT id, name, language, author_type, description, description_for_vector_db, tags, input_schema, output_schema FROM tools WHERE id = $1::uuid", tool_id)
    await conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    return {
        "status": "success", 
        "data": {
            "id": str(row['id']),
            "name": row['name'],
            "language": row['language'],
            "author_type": row['author_type'],
            "description": row['description'],
            "description_for_vector_db": row['description_for_vector_db'],
            "tags": row['tags'],
            "input_schema": json.loads(row['input_schema']) if isinstance(row['input_schema'], str) else (row['input_schema'] or {}),
            "output_schema": json.loads(row['output_schema']) if isinstance(row['output_schema'], str) else (row['output_schema'] or {})
        }
    }


# ==========================================
# Agent Reasoning APIs
# ==========================================
class AgentReasoningUpdate(BaseModel):
    logs: Dict[str, Any]

@router.get("/scopes/{scope_id}/reasoning")
async def get_scope_reasoning(scope_id: str):
    """ดึงข้อมูล Reasoning Log ของ Scope นั้นๆ"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "SELECT logs FROM agent_reasoning WHERE scope_id = $1::uuid"
    row = await conn.fetchrow(query, scope_id)
    await conn.close()
    
    logs = json.loads(row['logs']) if row and isinstance(row['logs'], str) else (row['logs'] if row else {})
    return {"status": "success", "data": {"logs": logs}}

@router.put("/scopes/{scope_id}/reasoning")
async def update_scope_reasoning(scope_id: str, data: AgentReasoningUpdate):
    """อัปเดตหรือสร้าง Reasoning Log ใหม่ (Upsert)"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = """
        INSERT INTO agent_reasoning (scope_id, logs) 
        VALUES ($1::uuid, $2::jsonb)
        ON CONFLICT (scope_id) 
        DO UPDATE SET logs = $2::jsonb, updated_at = CURRENT_TIMESTAMP
    """
    await conn.execute(query, scope_id, json.dumps(data.logs))
    await conn.close()
    return {"status": "success"}

@router.patch("/scopes/{scope_id}/reasoning")
async def patch_scope_reasoning(scope_id: str, data: AgentReasoningUpdate):
    """
    API สำหรับอัปเดต Reasoning Log แบบ Merge 
    (ใช้สำหรับอัปเดตทีละ Step โดยไม่ทับข้อมูลเก่าที่ AI เคยคิดไว้)
    """
    conn = await asyncpg.connect(POSTGRES_DSN)
    
    # 1. ดึงข้อมูลเก่ามาก่อน
    query_get = "SELECT logs FROM agent_reasoning WHERE scope_id = $1::uuid"
    row = await conn.fetchrow(query_get, scope_id)
    
    current_logs = {}
    if row and row['logs']:
        current_logs = json.loads(row['logs']) if isinstance(row['logs'], str) else row['logs']
    
    # 2. ฟังก์ชัน Merge Dictionary (รวมข้อมูลใหม่เข้ากับข้อมูลเก่าแบบเจาะลึก)
    def merge_dicts(dict1, dict2):
        for k, v in dict2.items():
            if isinstance(v, dict) and k in dict1 and isinstance(dict1[k], dict):
                merge_dicts(dict1[k], v)
            else:
                dict1[k] = v
        return dict1
        
    updated_logs = merge_dicts(current_logs, data.logs)
    
    # 3. บันทึกกลับลง Database (Upsert)
    query_upsert = """
        INSERT INTO agent_reasoning (scope_id, logs) 
        VALUES ($1::uuid, $2::jsonb)
        ON CONFLICT (scope_id) 
        DO UPDATE SET logs = $2::jsonb, updated_at = CURRENT_TIMESTAMP
    """
    await conn.execute(query_upsert, scope_id, json.dumps(updated_logs))
    await conn.close()
    
    return {"status": "success", "data": {"logs": updated_logs}}


@router.get("/scopes/{scope_id}/reasoning/markdown")
async def get_scope_reasoning_markdown(scope_id: str):
    """
    API สำหรับดึงข้อมูล JSON Reasoning และแปลงเป็น Markdown Text 
    เพื่อส่งไปเป็น Context ให้ LLM อ่านได้อย่างมีประสิทธิภาพ
    """
    conn = await asyncpg.connect(POSTGRES_DSN)
    query = "SELECT logs FROM agent_reasoning WHERE scope_id = $1::uuid"
    row = await conn.fetchrow(query, scope_id)
    await conn.close()
    
    if not row or not row['logs']:
        return {"status": "success", "data": ""}
        
    logs = json.loads(row['logs']) if isinstance(row['logs'], str) else row['logs']
    
    # ประกอบร่างเป็น Markdown String
    md = ""
    if "scope_name" in logs:
        md += f"# Scope name: {logs['scope_name']}\n"
    if "scope_goal" in logs:
        md += f"# Scope Goal: {logs['scope_goal']}\n\n"
        
    schedules = logs.get("schedules", {})
    for sch_id, sch_data in schedules.items():
        md += f"## Schedule Name: {sch_data.get('schedule_name', 'Unknown')}\n"
        if "schedule_goal" in sch_data:
            md += f"    - Schedule Goal: {sch_data['schedule_goal']}\n"
        if "planing_reasoning" in sch_data:
            md += f"    - Schedule Planing: {sch_data['planing_reasoning']}\n"
            
        # ลิสต์ Tool ที่ AI สร้างหรือเลือกใช้
        if "tools_created" in sch_data:
            md += f"    - Tool Code:\n"
            for t in sch_data["tools_created"]:
                md += f"        - {t.get('tool_name', 'Unknown Tool')} [{t.get('status', 'N/A')}]\n"
                
        # ลิสต์ Pipeline Task
        if "task_pipeline" in sch_data:
            md += f"    - Schedule Task pipeline:\n"
            for task in sch_data["task_pipeline"]:
                md += f"        - [Tool: {task.get('tool_id', 'N/A')}, Task: {task.get('task_type', 'N/A')}, Input Schema: {task.get('input_schema', 'N/A')}, Output Schema: {task.get('output_schema', 'N/A')}]\n"
        md += "\n"
        
    return {"status": "success", "data": md}