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

# Permissive CORS handling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up structural base paths
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(current_dir)
frontend_path = os.path.join(base_dir, "frontend")

# Mount Static Files safely
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class TaskInput(BaseModel):
    task_description: str
    energy_level: str

@app.post("/api/analyze-task")
async def analyze_task(payload: TaskInput):
    # YOUR DIRECT VALIDATED KEY COPIED HERE
    api_key = "AQ.Ab8RN6KI5yM4fpPr7FV04TURmVArMMWbkgCOzYWQ33mMh4ZLDw"

    # Direct Google REST API URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Strict behavioral coach prompt instructions
    prompt = f"""
    You are the behavioral coach engine for HabitFlow. 
    Analyze the following task and energy state to build a tailored micro-task plan.
    
    User's Task: "{payload.task_description}"
    Current Energy State: "{payload.energy_level}"

    CRITICAL EXECUTION RULES:
    - You must analyze the input words dynamically. If the task is about a wedding, give wedding steps. If it is about coding, give coding steps. 
    - Match the steps to their energy level contextually.

    Return a valid JSON object matching this exact structure:
    {{
        "original_task": "{payload.task_description}",
        "user_energy_level": "{payload.energy_level}",
        "recommended_action_strategy": "Name of real strategy used",
        "suggested_micro_tasks": [
            {{
                "task_title": "Actionable step title",
                "estimated_minutes": 10,
                "justification": "Why this matches energy"
            }}
        ]
    }}
    """

    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=request_body)
            
            # IF THE SYSTEM WORKS: Parse and clear the text
            if response.status_code == 200:
                response_data = response.json()
                raw_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
                
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text.rsplit("\n", 1)[0]
                    
                return json.loads(raw_text.strip())
            
            # IF GOOGLE CORES REJECT IT: Force the exact error onto the web screen immediately!
            else:
                return {
                    "original_task": f"Google Server Error: Status {response.status_code}",
                    "user_energy_level": payload.energy_level,
                    "recommended_action_strategy": "API Connection Refused",
                    "suggested_micro_tasks": [
                        {
                            "task_title": "Google Gateway Rejection Log Details:",
                            "estimated_minutes": response.status_code,
                            "justification": f"Server Response: {response.text}"
                        }
                    ]
                }
                
    except Exception as e:
        # NETWORK SYSTEM CRASH: Force the raw local python exception onto the screen
        return {
            "original_task": "Local System Error Exception",
            "user_energy_level": payload.energy_level,
            "recommended_action_strategy": "Network Failure",
            "suggested_micro_tasks": [
                {
                    "task_title": "Python Exception Trace:",
                    "estimated_minutes": 500,
                    "justification": f"Error Log: {str(e)}"
                }
            ]
        }

# Serves the frontend web UI file layout
@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(frontend_path, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h2>HabitFlow Frontend HTML template file not found!</h2>"