import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv

# Load local environment settings for local development
load_dotenv()

# Securely fetch the API Key from the system environment variables
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

app = FastAPI(title="HabitFlow AI Engine")

# Permissive CORS handling to allow local browser interactions cleanly
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

# Mount Static Files (Serves your background image habitflow.jpg)
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# ---- Pydantic Schemas for Structured Output Validation ----
class MicroTask(BaseModel):
    task_title: str
    estimated_minutes: int
    justification: str

class BehavioralPlan(BaseModel):
    original_task: str
    user_energy_level: str
    recommended_action_strategy: str
    suggested_micro_tasks: List[MicroTask]

class TaskInput(BaseModel):
    task_description: str
    energy_level: str

# ---- Main Processing Core Route ----
@app.post("/api/analyze-task")
async def analyze_task(payload: TaskInput):
    # Verify that the API Key is present before attempting generation
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(status_code=500, detail="Gemini API Key is missing from the server environment setup.")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""
        You are the behavioral coach engine for HabitFlow. 
        Analyze the following task and energy state to build a tailored micro-task plan.
        
        User's Task: "{payload.task_description}"
        Current Energy State: "{payload.energy_level}"

        CRITICAL EXECUTION RULES:
        - If Energy contains 'Low', 'Exhausted', or 'bare minimum': Apply the 'Five-Minute Rule'. Make the very first step absurdly simple (e.g., 'Open the file', 'Read just one line'). Keep total estimated minutes very low.
        - If Energy contains 'Medium' or 'Standard': Provide standard, structured, manageable milestones.
        - If Energy contains 'High' or 'Peak': Provide high-impact engineering chunks that challenge them to make massive progress immediately.

        Return a valid JSON object matching this exact structure:
        {{
            "original_task": "{payload.task_description}",
            "user_energy_level": "{payload.energy_level}",
            "recommended_action_strategy": "Name of the psychological strategy used here",
            "suggested_micro_tasks": [
                {{
                    "task_title": "Actionable step title",
                    "estimated_minutes": 5,
                    "justification": "Why this step matches their current energy"
                }}
            ]
        }}
        """

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"CRITICAL LOGGED EXCEPTION: {str(e)}")
        
        # Adaptive Fallback Engine in case of API limits or server network failure
        if "Low" in payload.energy_level:
            fallback_strategy = "Five-Minute Rule"
            micro_tasks = [
                {
                    "task_title": "Open your workspace file and review the layout",
                    "estimated_minutes": 5,
                    "justification": "Settle starting friction with zero overhead."
                },
                {
                    "task_title": "Write down just a single line of pseudocode",
                    "estimated_minutes": 5,
                    "justification": "Low energy needs atomic milestones."
                }
            ]
        elif "High" in payload.energy_level:
            fallback_strategy = "Peak Execution Drive"
            micro_tasks = [
                {
                    "task_title": "Isolate and deep-dive into the core logic chunk",
                    "estimated_minutes": 25,
                    "justification": "Maximize deep focus while your energy levels are high."
                },
                {
                    "task_title": "Refactor or optimize structural edge cases",
                    "estimated_minutes": 15,
                    "justification": "Push through complex implementations with high stamina."
                }
            ]
        else:
            fallback_strategy = "Balanced Milestone Sprint"
            micro_tasks = [
                {
                    "task_title": "Break down the core task into clear logic chunks",
                    "estimated_minutes": 15,
                    "justification": "Standard focus is ideal for structured progress."
                },
                {
                    "task_title": "Commit to working for just ten minutes straight",
                    "estimated_minutes": 10,
                    "justification": "Once momentum starts, finishing paralysis drops naturally."
                }
            ]
        
        return {
            "original_task": payload.task_description,
            "user_energy_level": payload.energy_level,
            "recommended_action_strategy": f"{fallback_strategy} (Adaptive Fallback Mode)",
            "suggested_micro_tasks": micro_tasks
        }

# Serves the frontend index.html structure directly on the root web address
@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(frontend_path, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h2>HabitFlow Frontend index.html template file not found!</h2>"