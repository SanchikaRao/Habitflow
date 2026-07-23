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

# 1. PATH RESOLUTION (Absolute path to root 'frontend' directory)
current_dir = os.path.dirname(os.path.abspath(__file__))  # Points to .../app
base_dir = os.path.dirname(current_dir)                    # Points to root
frontend_path = os.path.join(base_dir, "frontend")         # Points to .../frontend

# 2. MOUNT STATIC FILES (Serves habitflow.jpg via /static/ habitflow.jpg)
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class TaskInput(BaseModel):
    task_description: str
    energy_level: str

@app.post("/api/analyze-task")
async def analyze_task(payload: TaskInput):
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    # 3. LIVE GEMINI PIPELINE
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            prompt = f"""
            You are a professional life coach and behavioral strategist.
            Analyze the user's task and break it down into relevant, real-world actionable micro-steps.
            
            User's Task: "{payload.task_description}"
            Current Energy State: "{payload.energy_level}"

            CRITICAL RULES:
            1. Your answer MUST be completely unique and highly relevant to the specific user input words.
            2. Tailor the breakdown steps contextually to match their exact energy level.
            """
            
            request_body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "OBJECT",
                        "properties": {
                            "original_task": {"type": "STRING"},
                            "user_energy_level": {"type": "STRING"},
                            "recommended_action_strategy": {"type": "STRING"},
                            "suggested_micro_tasks": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "task_title": {"type": "STRING"},
                                        "estimated_minutes": {"type": "INTEGER"},
                                        "justification": {"type": "STRING"}
                                    },
                                    "required": ["task_title", "estimated_minutes", "justification"]
                                }
                            }
                        },
                        "required": ["original_task", "user_energy_level", "recommended_action_strategy", "suggested_micro_tasks"]
                    }
                }
            }
            
            headers = {"Content-Type": "application/json"}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=request_body, headers=headers)
                
                if response.status_code == 200:
                    response_data = response.json()
                    raw_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
                    
                    # Clean markdown code backticks if Gemini wraps output
                    if raw_text.startswith("```"):
                        raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                        
                    return json.loads(raw_text)
                else:
                    # Print error log and proceed safely to Fallback Matrix
                    print(f"Gemini API Error Status {response.status_code}: {response.text}")
                    
        except Exception as e:
            print(f"Live Pipeline Exception: {str(e)}")
    else:
        print("GEMINI_API_KEY missing from environment variables. Running Fallback Mode.")

    # 4. DYNAMIC FALLBACK MATRIX (Guarantees response within 1 second)
    task_lower = payload.task_description.lower()
    
    if len(task_lower.strip()) < 5 or not any(char.isalpha() for char in task_lower):
        strategy = "Clarity Realignment Protocol"
        tasks = [
            {"task_title": "Pause and define one clear, tiny objective", "estimated_minutes": 2, "justification": "Your current input seems unorganized."},
            {"task_title": "Type a simple 3-word action description", "estimated_minutes": 3, "justification": "Resets starting paralysis."}
        ]
    else:
        strategy = f"Standard {payload.energy_level.capitalize()} Energy Milestone Sprint"
        tasks = [{"task_title": f"Isolate the first step for '{payload.task_description}'", "estimated_minutes": 10, "justification": f"Optimized for {payload.energy_level} workflow."}]

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