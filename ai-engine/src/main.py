import asyncio
from fastapi import FastAPI, BackgroundTasks
import httpx
from pydantic import BaseModel
import io
import os
import json
import re
import ast
from typing import Callable, Any, Dict
from core.llm import call_llm_agent
import logging

app = FastAPI(title="AI Agentic Engine")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend-api:8000/api/v1/projects")

ScheduleArchitect = open("prompts/ScheduleArchitect.md").read()
step1_system_prompt = open("prompts/ToolResearcher&DeveloperStep1.md").read()
step2_system_prompt = open("prompts/ToolResearcher&DeveloperStep2.md").read()
TaskOrchestrator = open("prompts/TaskOrchestrator.md").read()

logging.basicConfig(level=logging.INFO)
logging.info("🚀 AI Agentic Engine is starting up...")

# logging.info(f"ScheduleArchitect Prompt Loaded: {ScheduleArchitect if ScheduleArchitect else '❌'}")
# logging.info(f"Step1 System Prompt Loaded: {step1_system_prompt if step1_system_prompt else '❌'}")
# logging.info(f"Step2 System Prompt Loaded: {step2_system_prompt if step2_system_prompt else '❌'}")
# logging.info(f"TaskOrchestrator Prompt Loaded: {TaskOrchestrator if TaskOrchestrator else '❌'}")

# ==========================================
# 1. Core Utilities (AI JSON Parser & Router)
# ==========================================
def parse_ai_json_response(raw_ai_text: str) -> dict:
    """
    ดึงข้อมูล JSON ออกจากข้อความดิบที่ AI พ่นออกมา 
    พร้อมระบบซ่อมแซม JSON อัตโนมัติ (Robust Fallbacks)
    """
    try:
        # 1. ทำความสะอาด Markdown blocks (```json ... ```)
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_ai_text, re.DOTALL)
        if json_match:
            clean_json_str = json_match.group(1).strip()
        else:
            clean_json_str = raw_ai_text.strip()
        logging.info(f"🔍 Extracted JSON string: {clean_json_str[:]}")  # แสดงแค่ 200 ตัวแรก
        return json.loads(clean_json_str, strict=False)
        
    except json.JSONDecodeError as e:
        logging.warning(f"Standard JSON parsing failed: {e}. Attempting auto-repair...")
        try:
            fixed_comma_str = re.sub(r',\s*([\]}])', r'\1', clean_json_str)
            logging.info(f"🔧 Fixed JSON string: {fixed_comma_str[:]}")
            return json.loads(fixed_comma_str, strict=False)
        except json.JSONDecodeError:
            try:
                python_like_str = re.sub(r'\btrue\b', 'True', clean_json_str)
                python_like_str = re.sub(r'\bfalse\b', 'False', python_like_str)
                python_like_str = re.sub(r'\bnull\b', 'None', python_like_str)
                try:
                    repaired_data = ast.literal_eval(python_like_str)
                    logging.info(f"🔨 Repaired data using ast.literal_eval: {repaired_data}")
                    return repaired_data
                except SyntaxError:
                    escaped_str = python_like_str.replace('\n', '\\n')
                    repaired_data = ast.literal_eval(escaped_str)
                    logging.info(f"🔨 Repaired data using ast.literal_eval: {repaired_data}")
                    return repaired_data
            except Exception as repair_error:
                logging.error(f"❌ All fallback repairs failed: {repair_error}")
                raise ValueError(f"AI Output is fundamentally invalid JSON. Error: {e}")

class AsyncActionRouter:
    def __init__(self):
        self._routes: Dict[str, Callable] = {}

    def register(self, action_name: str, handler: Callable):
        self._routes[action_name] = handler

    async def execute(self, action_name: str, **kwargs) -> Any:
        handler = self._routes.get(action_name)
        if not handler:
            raise NotImplementedError(f"No module registered for action: {action_name}")
        return await handler(**kwargs)

pipeline_router = AsyncActionRouter()

# ==========================================
# 1.5 Agent Reasoning Helper Functions
# ==========================================
async def update_agent_reasoning(scope_id: str, logs_data: dict):
    """ส่ง PATCH Request เพื่ออัปเดต Reasoning เข้าไปแบบ Merge"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            await client.patch(f"{BACKEND_URL}/scopes/{scope_id}/reasoning", json={"logs": logs_data})
    except Exception as e:
        logging.warning(f"⚠️ Failed to update reasoning for scope {scope_id}: {e}")

async def get_agent_reasoning_markdown(scope_id: str) -> str:
    """ส่ง GET Request เพื่อดึงประวัติการคิดรูปแบบ Markdown ไปแนบ Prompt"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(f"{BACKEND_URL}/scopes/{scope_id}/reasoning/markdown")
            if resp.status_code == 200:
                return resp.json().get("data", "")
    except Exception as e:
        logging.warning(f"⚠️ Failed to get markdown reasoning for scope {scope_id}: {e}")
    return ""

# ==========================================
# 2. Registered Modules (The Brains)
# ==========================================
async def handle_schedule_planning(scope_id: str, goal: str, agent_reasoning: str):
    logging.info(f"[Module 1 & 2] Planning schedules for Scope: {scope_id} | Goal: {goal}")
    llm_response = await call_llm_agent(
        system_prompt=ScheduleArchitect if ScheduleArchitect else "You are an expert schedule planner for data tasks.",
        user_prompt=f"Scope ID: {scope_id}\nGoal: {goal}\n\nPlease output a JSON array of schedules...",
        agent_reasoning=agent_reasoning
    )
    return parse_ai_json_response(llm_response)

async def handle_tool_resolution(schedule_goal: str, agent_reasoning: str):
    logging.info(f"[Module 3] Step 1: Formulating Search Query for goal: {schedule_goal}")
    
    # Step 1: สร้าง Search Query และ Tags
    step1_user_prompt = f"Schedule Goal: {schedule_goal}\nGenerate JSON with 'search_query' and 'tags'."
    llm_search_params = await call_llm_agent(step1_system_prompt, step1_user_prompt, agent_reasoning)
    search_params = parse_ai_json_response(llm_search_params)
    
    # Step 2: ยิง API ค้นหา
    logging.info(f"   -> 🔍 Searching Backend for tags: {search_params['tags']}")
    rag_tools_json = "[]"
    async with httpx.AsyncClient() as client:
        try:
            search_resp = await client.post(
                f"{BACKEND_URL}/tools/search", 
                json={"query": search_params["search_query"], "tags": search_params["tags"], "limit": 3}
            )
            search_resp.raise_for_status()
            search_results = search_resp.json().get("data", [])
            rag_tools_json = json.dumps(search_results, indent=2)
        except Exception as e:
            logging.warning(f"   -> ⚠️ Search failed or no tools found.")

    # Step 3: ให้ LLM ตัดสินใจ
    logging.info(f"[Module 3] Step 3: Deciding to Reuse or Create New Tools...")
    step2_user_prompt = f"Schedule Goal: {schedule_goal}\nRetrieved Tools from Database: {rag_tools_json}\n If None of the existing tools are a good fit, create a new one."
    
    llm_decision = await call_llm_agent(step2_system_prompt, step2_user_prompt, agent_reasoning)
    parsed_tool_decisions = parse_ai_json_response(llm_decision)
    resolved_tools = []
    
    # Step 4: ดำเนินการอัปโหลดหรือนำมาใช้ซ้ำ
    async with httpx.AsyncClient(timeout=60.0) as client:
        for decision in parsed_tool_decisions:
            if decision.get("action") == "CREATE_NEW":
                details = decision["new_tool_details"]
                filename = f"{details['name']}.{'py' if details['language'].lower() == 'python' else 'go'}"
                file_content = details["source_code"].encode("utf-8")
                
                data = {
                    "name": details["name"],
                    "language": details["language"],
                    "author_type": "AI_GENERATED",
                    "description": details.get("description", ""),
                    "description_for_vector_db": details.get("description_for_vector_db", ""),
                    "tags": json.dumps(details.get("tags", [])),
                    "input_schema": json.dumps(details.get("input_schema", {})),
                    "output_schema": json.dumps(details.get("output_schema", {})),
                    "dependencies": json.dumps(details.get("dependencies", {})) # 👈 เพิ่มบรรทัดนี้
                }
                files = {"file": (filename, file_content, "text/plain")}
                
                try:
                    resp = await client.post(f"{BACKEND_URL}/tools/upload", data=data, files=files)
                    resp.raise_for_status()
                    resolved_tools.append({
                        "tool_id": resp.json().get("tool_id"),
                        "tool_name": details["name"],
                        "status": "CREATE_NEW",
                        "input_schema": details.get("input_schema"),
                        "output_schema": details.get("output_schema")
                    })
                except Exception as e:
                    logging.error(f"      ❌ Failed to upload tool: {e}")
            
            elif decision.get("action") == "USE_EXISTING":
                resolved_tools.append({
                    "tool_id": decision["tool_id"],
                    "tool_name": decision.get("tool_name", f"Reused Tool {decision['tool_id'][:8]}"),
                    "status": "USE_EXISTING",
                    "input_schema": None,
                    "output_schema": None
                })
    return resolved_tools

async def handle_task_orchestration(schedule_goal: str, tool_ids: list, agent_reasoning: str):
    print(f"[Module 4] Orchestrating DAG for tools: {tool_ids}")
    llm_response = await call_llm_agent(
        system_prompt=TaskOrchestrator if TaskOrchestrator else "You are a task orchestration agent.",
        user_prompt=f"Schedule Goal: {schedule_goal}\nApproved Tool IDs: {tool_ids}\n\nPlease output a JSON array of tasks...",
        agent_reasoning=agent_reasoning
    )
    return parse_ai_json_response(llm_response)

pipeline_router.register("PLAN_SCHEDULE", handle_schedule_planning)
pipeline_router.register("RESOLVE_TOOLS", handle_tool_resolution)
pipeline_router.register("ORCHESTRATE_TASK", handle_task_orchestration)


# ==========================================
# 3. Core Orchestrators (Background Tasks)
# ==========================================
async def process_schedule_planning(scope_id: str, goal: str):
    """ร้อยเรียง Flow การสร้าง Schedule"""
    try:
        # เริ่มตั้งไข่ Reasoning Log 
        await update_agent_reasoning(scope_id, {"scope_goal": goal, "schedules": {}})
        reasoning_md = await get_agent_reasoning_markdown(scope_id)

        # 1. ให้ AI วางแผน Schedules
        schedules_list = await pipeline_router.execute(
            "PLAN_SCHEDULE", scope_id=scope_id, goal=goal, agent_reasoning=reasoning_md
        )
        
        # 2. เซฟลง Database
        async with httpx.AsyncClient(timeout=300.0) as client:
            for sch in schedules_list:
                payload = {
                    "name": sch["name"],
                    "goal": sch.get("schedule_goal", sch["name"]),
                    "task_mode": sch["task_mode"],
                    "execution_type": sch["execution_type"],
                    "cron_expression": sch.get("cron_expression"),
                    "is_sequential": sch.get("is_sequential", True)
                }
                
                resp = await client.post(f"{BACKEND_URL}/scopes/{scope_id}/schedules", json=payload)
                resp.raise_for_status()
                new_schedule_id = resp.json().get("schedule_id")
                
                # บันทึกสิ่งที่ AI คิดลง Reasoning {Step 1}
                await update_agent_reasoning(scope_id, {
                    "schedules": {
                        new_schedule_id: {
                            "schedule_name": sch["name"],
                            "schedule_goal": payload["goal"],
                            "planing_reasoning": "AI planned this schedule to fulfill the scope goal.",
                            "step1_completed": True
                        }
                    }
                })
                logging.info(f"✅ Created Schedule: {sch['name']} (ID: {new_schedule_id})")
        
    except Exception as e:
        logging.error(f"❌ [AI Engine Error] Schedule Planning failed: {str(e)}")

async def process_task_orchestration(scope_id: str, schedule_id: str, schedule_goal: str):
    """ร้อยเรียง Flow การหา Tool และสร้าง Task Pipeline"""
    try:
        # ดึง Context ปัจจุบันก่อนเริ่มหา Tool
        reasoning_md = await get_agent_reasoning_markdown(scope_id)

        # 1. เรียก Module 3 หา/สร้าง Tools
        approved_tools = await pipeline_router.execute(
            "RESOLVE_TOOLS", schedule_goal=schedule_goal, agent_reasoning=reasoning_md
        )
        
        # บันทึกเครื่องมือที่ตัดสินใจใช้ลง Reasoning {Step 2}
        await update_agent_reasoning(scope_id, {
            "schedules": {
                schedule_id: {
                    "tools_created": approved_tools,
                    "step2_completed": True
                }
            }
        })
        
        # ดึง Context ใหม่อีกรอบ ให้ AI เห็น Tool ที่ตัวเองเพิ่งหามา
        reasoning_md = await get_agent_reasoning_markdown(scope_id)

        # 2. เรียก Module 4 ผูกเป็น Tasks
        tasks_list = await pipeline_router.execute(
            "ORCHESTRATE_TASK", schedule_goal=schedule_goal, tool_ids=approved_tools, agent_reasoning=reasoning_md
        )
        
        # บันทึก Pipeline การวาง Task ลง Reasoning {Step 3}
        await update_agent_reasoning(scope_id, {
            "schedules": {
                schedule_id: {
                    "task_pipeline": tasks_list,
                    "step3_completed": True
                }
            }
        })
        
        # 3. ยิง API เซฟ Tasks ลง Database ตัวจริง
        task_id_map = {} 
        async with httpx.AsyncClient(timeout=60.0) as client:
            for index, task in enumerate(tasks_list):
                real_depends_on = None
                temp_depends_on = task.get("depends_on_task_id")
                
                if temp_depends_on and temp_depends_on in task_id_map:
                    real_depends_on = task_id_map[temp_depends_on]
                
                payload = {
                    "task_type": task.get("task_type", "TRADITIONAL_LOGIC"),
                    "tool_id": task.get("tool_id"),
                    "engine_type": task.get("engine_type", "AIRFLOW_DAG"),
                    "depends_on_task_id": real_depends_on,
                    "execution_order": index + 1,
                    "arguments": task.get("arguments", {}),
                    "ui_position": {"x": 150 + (index * 250), "y": 150 + (index % 2 * 50)} 
                }
                
                resp = await client.post(f"{BACKEND_URL}/schedules/{schedule_id}/tasks", json=payload)
                resp.raise_for_status()
                
                real_task_id = resp.json().get("task_id")
                if task.get("temp_task_id"):
                    task_id_map[task.get("temp_task_id")] = real_task_id
                    
        logging.info(f"✅ Successfully orchestrated {len(tasks_list)} tasks for Schedule {schedule_id}")
        
    except Exception as e:
        logging.error(f"❌ [AI Engine Error] Task Orchestration failed: {str(e)}")


# ==========================================
# 4. FastAPI Endpoints
# ==========================================
class ScopePlanRequest(BaseModel):
    scope_id: str
    goal: str

class TaskOrchestrateRequest(BaseModel):
    scope_id: str        # 👈 เพิ่ม scope_id มารับที่นี่ด้วย
    schedule_id: str
    schedule_goal: str

@app.post("/api/v1/generate/schedules")
async def generate_schedules(req: ScopePlanRequest, bg_tasks: BackgroundTasks):
    bg_tasks.add_task(process_schedule_planning, req.scope_id, req.goal)
    return {"status": "processing", "message": "AI is planning schedules..."}

@app.post("/api/v1/generate/tasks")
async def generate_tasks(req: TaskOrchestrateRequest, bg_tasks: BackgroundTasks):
    # 👈 ส่ง scope_id เพิ่มเข้าไปให้ Process รับทราบด้วย
    bg_tasks.add_task(process_task_orchestration, req.scope_id, req.schedule_id, req.schedule_goal)
    return {"status": "processing", "message": "AI is resolving tools and building tasks..."}