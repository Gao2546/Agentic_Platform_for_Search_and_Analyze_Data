from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 1. Import CORSMiddleware
from src.api import schedules, data_retrieval, scopes_management

app = FastAPI(title="Agentic Platform API", version="1.0.0")

# 2. ตั้งค่า CORS Middleware อนุญาตให้ Frontend เข้าถึงได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", # อนุญาตพอร์ตของ Vite (Local)
        "http://127.0.0.1:5173",
        "*" # (ถ้าทดสอบแล้วยังติด สามารถเปิดเป็น "*" เพื่อรับทุกที่ชั่วคราวได้)
    ],
    allow_credentials=True,
    allow_methods=["*"], # อนุญาตทุก Method (GET, POST, PUT, DELETE)
    allow_headers=["*"], # อนุญาตทุก Header
)

# เชื่อมต่อ Router ที่เราเขียนไว้
app.include_router(schedules.router)
app.include_router(data_retrieval.router)
app.include_router(scopes_management.router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "backend-api"}