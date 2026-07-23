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
    # Open connection pool on server startup (Increased timeout to 20s to prevent ReadTimeout)
    http_client = httpx.AsyncClient(timeout=20.0)
    print("LOG: [Lifespan] HTTPX AsyncClient connection pool initialized with 20s timeout.")
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

    # 1. Clean inputs to prevent JSON escape breaking
    clean_task = payload.task_description.replace('"', "'").strip()
    clean_energy = payload.energy_level.replace('"', "'").strip()

    print("=" * 60)
    print(f"LOG: Request received for task: '{clean_task}'")
    print(f"LOG: Energy level: '{clean_energy}'")
    print(f"LOG: GEMINI_API_KEY loaded? {'YES' if api_key else 'NO'}")

    # 2. LIVE GEMINI PIPELINE
    if api_key and http_client:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

            prompt = f"""
            You are a professional life coach and behavioral strategist.
            Analyze the user's task and break it down into relevant, real-world actionable micro-steps.
            
            User's Task: "{clean_task}"
            Current Energy State: "{clean_energy}"

            CRITICAL RULES:
            1. Respond ONLY with valid, raw JSON.
            2. If Energy State contains '5-Min Rule' or 'Low', EVERY step MUST have 'estimated_minutes' of 5 or less.

            JSON STRUCTURE:
            {{
              "original_task": "{clean_task}",
              "user_energy_level": "{clean_energy}",
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

            request_body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }

            headers = {"Content-Type": "application/json"}

            print("LOG: Sending POST request to Gemini API...")
            response = await http_client.post(url, json=request_body, headers=headers)
            print(f"LOG: Gemini API HTTP Response Status Code: {response.status_code}")

            if response.status_code == 200:
                response_data = response.json()
                raw_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()

                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

                parsed_json = json.loads(raw_text)
                print("LOG: Successfully parsed Gemini JSON! Returning live AI breakdown.")
                print("=" * 60)
                return parsed_json
            else:
                print(f"ERROR: Gemini API returned status {response.status_code}: {response.text}")

        except Exception as e:
            print(f"EXCEPTION: Error in live pipeline execution: {str(e)}")
            traceback.print_exc()

    # 3. DYNAMIC FALLBACK MATRIX
    print("LOG: Entering Fallback Matrix execution.")
    task_lower = clean_task.lower()
    energy_lower = clean_energy.lower()

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
        clean_energy_name = clean_energy.split('/')[0].strip()
        strategy = f"Standard {clean_energy_name} Milestone Sprint"
        tasks = [{
            "task_title": f"Isolate the first step for '{clean_task}'",
            "estimated_minutes": fallback_time,
            "justification": f"Optimized for your {clean_energy_name} energy state."
        }]

    print("LOG: Returning Fallback Matrix response.")
    print("=" * 60)
    return {
        "original_task": clean_task,
        "user_energy_level": clean_energy,
        "recommended_action_strategy": strategy,
        "suggested_micro_tasks": tasks
    }


# 4. SERVE FRONTEND AT ROOT "/"
@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(frontend_path, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h2>HabitFlow Frontend HTML file not found!</h2>"