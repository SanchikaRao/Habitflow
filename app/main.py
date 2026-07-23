import os
import json
import httpx
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Global client holder for connection pooling
http_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    # Open connection pool on server startup (reused across all requests)
    http_client = httpx.AsyncClient(timeout=8.0)
    print("LOG: [Lifespan] HTTPX AsyncClient connection pool initialized.")
    yield
    # Clean up client on server shutdown
    await http_client.aclose()
    print("LOG: [Lifespan] HTTPX AsyncClient closed.")

app = FastAPI(title="HabitFlow AI Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. PATH RESOLUTION
current_dir = os.path.dirname(os.path.abspath(__file__))  # Points to .../app
base_dir = os.path.dirname(current_dir)                    # Points to root
frontend_path = os.path.join(base_dir, "frontend")         # Points to .../frontend

# 2. MOUNT STATIC FILES
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class TaskInput(BaseModel):
    task_description: str
    energy_level: str

@app.post("/api/analyze-task")
async def analyze_task(payload: TaskInput):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    print("=" * 60)
    print(f"LOG: Request received for task: '{payload.task_description}'")
    print(f"LOG: GEMINI_API_KEY loaded? {'YES' if api_key else 'NO (Empty String)'}")
    print(f"LOG: http_client active? {http_client is not None}")
    
    # 3. LIVE GEMINI PIPELINE
    if api_key and http_client:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            # ... (Inside your try block) ...
            
            prompt = f"""
            You are a professional life coach and behavioral strategist.
            Analyze the user's task and break it down into relevant, real-world actionable micro-steps.
            
            User's Task: "{payload.task_description}"
            Current Energy State: "{payload.energy_level}"

            CRITICAL RULES:
            1. Respond ONLY with valid, raw JSON.
            2. If the Energy State includes "5-Min Rule", NO task can have an 'estimated_minutes' greater than 5.
            
            JSON STRUCTURE:
            {{
              "original_task": "{payload.task_description}",
              "user_energy_level": "{payload.energy_level}",
              "recommended_action_strategy": "short strategy name",
              "suggested_micro_tasks": [
                {{
                  "task_title": "step title",
                  "estimated_minutes": 5,
                  "justification": "why this helps"
                }}
              ]
            }}
            """
            
            # ... (Keep your HTTP request code the same here) ...

    # ==========================================================
    # 4. DYNAMIC FALLBACK MATRIX (Now with dynamic time mapping!)
    # ==========================================================
    print("LOG: Entering Fallback Matrix execution.")
    task_lower = payload.task_description.lower()
    energy_lower = payload.energy_level.lower()
    
    # Dynamically assign fallback time based on the energy level string
    if "low" in energy_lower or "5-min" in energy_lower:
        fallback_time = 5
    elif "high" in energy_lower:
        fallback_time = 15
    else:
        fallback_time = 10
    
    if len(task_lower.strip()) < 5 or not any(char.isalpha() for char in task_lower):
        strategy = "Clarity Realignment Protocol"
        tasks = [
            {"task_title": "Pause and define one clear, tiny objective", "estimated_minutes": 2, "justification": "Your current input seems unorganized."},
            {"task_title": "Type a simple 3-word action description", "estimated_minutes": 3, "justification": "Resets starting paralysis."}
        ]
    else:
        # Clean up the strategy title so it reads better
        clean_energy_name = payload.energy_level.split('/')[0].strip()
        strategy = f"Standard {clean_energy_name} Milestone Sprint"
        
        tasks = [{
            "task_title": f"Isolate the first step for '{payload.task_description}'", 
            "estimated_minutes": fallback_time, 
            "justification": f"Optimized for your {clean_energy_name} energy state."
        }]

    print("LOG: Returning Fallback Matrix response.")
    print("=" * 60)
    return {
        "original_task": payload.task_description,
        "user_energy_level": payload.energy_level,
        "recommended_action_strategy": strategy,
        "suggested_micro_tasks": tasks
    }
# 5. SERVE FRONTEND AT ROOT "/"
@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(frontend_path, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h2>HabitFlow Frontend HTML file not found!</h2>"