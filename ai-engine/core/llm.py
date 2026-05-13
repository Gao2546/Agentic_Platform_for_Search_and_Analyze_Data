import os
import asyncio
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# 1. ตั้งค่า Client
# หากใช้ OpenAI ของจริง ไม่ต้องใส่ base_url ก็ได้
# แต่ถ้าใช้ Local LLM (เช่น LM Studio, vLLM) ให้กำหนด base_url ชี้ไปที่ Localhost
client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY", "sk-xxx..."), # ใส่ API Key หรือ "dummy" สำหรับ Local
    base_url="https://openrouter.ai/api/v1" # ปลดคอมเมนต์บรรทัดนี้ถ้าใช้ Local LLM ที่รองรับ OpenAI Standard
)
logging.basicConfig(level=logging.INFO)
logging.info("✅ LLM Client initialized")
logging.info(f"🔍 API Base URL: {client.base_url}")
logging.info(f"🔑 API Key: {'Set' if client.api_key else 'Not Set'}")

async def call_llm_agent(system_prompt: str, user_prompt: str, agent_reasoning: str) -> str:
    try:
        logging.info("🤖 LLM is thinking...")
        
        # 2. เรียกใช้งาน Chat Completions
        response = await client.chat.completions.create(
            model="deepseek/deepseek-v4-flash",#"tencent/hy3-preview:free", deepseek/deepseek-v4-flash
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "name": "agent_reasoning", "content": agent_reasoning} if agent_reasoning else {},
                {"role": "user", "content": user_prompt}
            ],
            # temperature=0.0, # ค่าความสร้างสรรค์ (0.0 - 2.0)
            # max_tokens=2048*10, # จำนวน Token สูงสุดที่ยอมให้ตอบกลับ
            # response_format={"type": "json_object"} # บังคับให้ออกเป็น JSON (โมเดลต้องรองรับ)
        )
        
        # 3. ดึงข้อความตอบกลับออกมา
        ai_message = response.choices[0].message.content
        logging.info(f"✅ LLM Response received: {ai_message[:]}...") # แสดงแค่ 200 ตัวแรก
        return ai_message

    except Exception as e:
        logging.error(f"❌ Error calling LLM: {str(e)}")
        return "{}"