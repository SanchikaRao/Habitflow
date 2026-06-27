import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="HabitFlow AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class TaskInput(BaseModel):
    task_description: str
    energy_level: str

@app.post("/api/analyze-task")
async def analyze_task(payload: TaskInput):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key is missing from Render environment setup.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"Analyze the task: '{payload.task_description}' for energy level: '{payload.energy_level}' and return JSON."

    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=request_body)
        
        # IF IT FAILS: Instead of falling back, return the raw error details immediately!
        if response.status_code != 200:
            return {
                "recommended_action_strategy": f"API Error Code: {response.status_code}",
                "original_task": "Google Gateway Rejection Log",
                "suggested_micro_tasks": [
                    {
                        "task_title": "Raw Server Response Message:",
                        "estimated_minutes": response.status_code,
                        "justification": f"{response.text}"
                    }
                ]
            }
            
        response_data = response.json()
        raw_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
        return json.loads(raw_text)