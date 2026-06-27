import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# Load local environment settings
load_dotenv()

app = FastAPI(title="HabitFlow AI Engine")

# Permissive CORS handling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up structural base paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, "frontend")

# Mount Static Files
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# ---- Pydantic Schemas ----
class TaskInput(BaseModel):
    task_description: str
    energy_level: str

# ---- Main Processing Core Route (Overhauled for Direct HTTPS) ----
@app.post("/api/analyze-task")
async def analyze_task(payload: TaskInput):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key is missing from Render environment setup.")

    # Direct Google REST API endpoint for Gemini 1.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    You are the behavioral coach engine for HabitFlow. 
    Analyze the following task and energy state to build a tailored micro-task plan.
    
    User's Task: "{payload.task_description}"
    Current Energy State: "{payload.energy_level}"

    CRITICAL EXECUTION RULES:
    - If Energy contains 'Low': Apply the 'Five-Minute Rule'. Make the first step absurdly simple.
    - If Energy contains 'Medium': Provide standard, structured, manageable milestones.
    - If Energy contains 'High': Provide high-impact engineering chunks.

    Return a valid JSON object matching this exact structure:
    {{
        "original_task": "{payload.task_description}",
        "user_energy_level": "{payload.energy_level}",
        "recommended_action_strategy": "Name of strategy used",
        "suggested_micro_tasks": [
            {{
                "task_title": "Actionable step title",
                "estimated_minutes": 5,
                "justification": "Why this matches energy"
            }}
        ]
    }}
    """

    # Build the strict raw payload Google expects
    request_body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        # Use a timeout-resilient HTTP client to make the raw post request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=request_body)
            
            if response.status_code != 200:
                print(f"Google API Error Code: {response.status_code} - Log: {response.text}")
                raise Exception(f"Google Endpoint rejected token request status: {response.status_code}")
                
            response_data = response.json()
            
            # Extract the generated text block inside Google's nested response structure
            raw_text = response_data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(raw_text)

    except Exception as e:
        print(f"CRITICAL LOGGED EXCEPTION: {str(e)}")
        
        # Adaptive Fallback Engine
        if "Low" in payload.energy_level:
            fallback_strategy = "Five-Minute Rule"
            micro_tasks = [
                {"task_title": "Open your planner or notes app", "estimated_minutes": 5, "justification": "Settle starting friction with zero overhead."},
                {"task_title": "Review the basic schedule timeline", "estimated_minutes": 5, "justification": "Low energy needs atomic milestones."}
            ]
        elif "High" in payload.energy_level:
            fallback_strategy = "Peak Execution Drive"
            micro_tasks = [
                {"task_title": "Deep dive into core preparation work", "estimated_minutes": 25, "justification": "Maximize deep focus while your energy levels are high."}
            ]
        else:
            fallback_strategy = "Balanced Milestone Sprint"
            micro_tasks = [
                {"task_title": "Break down the core elements into manageable steps", "estimated_minutes": 15, "justification": "Standard focus is ideal for structured progress."},
                {"task_title": "Dedicate ten minutes to setting up your workspace", "estimated_minutes": 10, "justification": "Once momentum starts, finishing paralysis drops naturally."}
            ]
        
        return {
            "original_task": payload.task_description,
            "user_energy_level": payload.energy_level,
            "recommended_action_strategy": f"{fallback_strategy}",
            "suggested_micro_tasks": micro_tasks
        }

# Serves the frontend directly on the root web address
@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(frontend_path, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h2>HabitFlow Frontend index.html template file not found!</h2>"