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

# Permissive CORS handling for frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structural base directory paths for mounting
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(current_dir)
frontend_path = os.path.join(base_dir, "frontend")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class TaskInput(BaseModel):
    task_description: str
    energy_level: str

@app.post("/api/analyze-task")
async def analyze_task(payload: TaskInput):
    api_key = os.getenv("GEMINI_API_KEY", "")
    task_lower = payload.task_description.lower()
    
    # ---- 1. LIVE DYNAMIC AI PIPELINE ----
    if api_key:
        try:
            # Fixed REST URL path structure
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            prompt = f"""
            You are a professional life coach and behavioral strategist.
            Analyze the user's task and break it down into relevant, real-world actionable micro-steps.
            
            User's Task: "{payload.task_description}"
            Current Energy State: "{payload.energy_level}"

            CRITICAL RULES:
            1. Your answer MUST be completely unique and relevant to the user's input words. If they talk about a presentation, wedding, or coding, give steps specifically for that. 
            2. Tailor the breakdown steps contextually to match their energy level.

            Return a valid JSON object matching this exact structure:
            {{
                "original_task": "{payload.task_description}",
                "user_energy_level": "{payload.energy_level}",
                "recommended_action_strategy": "Dynamic Analysis Plan",
                "suggested_micro_tasks": [
                    {{
                        "task_title": "Actionable step title matching their exact goal",
                        "estimated_minutes": 15,
                        "justification": "Why this specific step helps their unique situation right now"
                    }}
                ]
            }}
            """
            
            request_body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            
            headers = {"Content-Type": "application/json"}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=request_body, headers=headers)
                
                if response.status_code == 200:
                    response_data = response.json()
                    raw_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
                    
                    if raw_text.startswith("```"):
                        raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]
                        
                    return json.loads(raw_text.strip())
        except Exception as e:
            print(f"Live Pipeline Connection Exception: {str(e)}")
            pass

    # ---- 2. DYNAMIC MATCHING ENGINE (Zero-Fail Contextual Backup Matrix) ----
    
    # UNUSUAL INPUT / GIBBERISH COUNTER
    if len(task_lower.strip()) < 5 or not any(char.isalpha() for char in task_lower) or task_lower.strip() in ["abcd", "xyz", "qwer", "1234"]:
        strategy = "Clarity Realignment Protocol"
        tasks = [
            {"task_title": "Pause and define one clear, tiny objective", "estimated_minutes": 2, "justification": "Your current input seems a bit unorganized. Action steps require a concrete task target to map out plan flows."},
            {"task_title": "Type a simple 3-word action description in the box (e.g., 'Clean my room')", "estimated_minutes": 3, "justification": "Lowering the thought footprint to a basic phrase resets starting paralysis instantly."}
        ]

    # WEDDING / EVENT CONTEXT
    elif any(word in task_lower for word in ["wedding", "marriage", "ceremony", "party", "function", "tomorrow"]):
        if "Low" in payload.energy_level:
            strategy = "Five-Minute Event Wrap"
            tasks = [
                {"task_title": "Hang up your outfit and place your shoes by the door", "estimated_minutes": 5, "justification": "Low energy demands effortless tasks to eliminate morning exit panic."},
                {"task_title": "Set a direct alarm notification for your departure target", "estimated_minutes": 5, "justification": "Automating your timeline guarantees zero mental strain tonight."}
            ]
        elif "High" in payload.energy_level:
            strategy = "Peak Event Execution Drive"
            tasks = [
                {"task_title": "Iron your formal attire and pack all accessories cleanly", "estimated_minutes": 20, "justification": "Capitalizes on high energy states to handle premium presentation details."},
                {"task_title": "Confirm travel reservations, navigation paths, and gift checking", "estimated_minutes": 15, "justification": "Ensures logistical deep execution is completely locked down ahead of time."}
            ]
        else:
            strategy = "Balanced Event Milestone Sprint"
            tasks = [
                {"task_title": "Review the ceremony schedule and arrival parameters", "estimated_minutes": 10, "justification": "Aligning your timing constraints creates a steady, comfortable flow."},
                {"task_title": "Organize your entry items, card contents, or gift packages", "estimated_minutes": 15, "justification": "Standard focus levels are perfectly suited for handling detail sorting."}
            ]
    
    # ACADEMIC / COLLEGE / PRESENTATION CONTEXT
    elif any(word in task_lower for word in ["assignment", "project", "submit", "exam", "study", "test", "college", "presentation"]):
        if "Low" in payload.energy_level:
            strategy = "Five-Minute Academic Spark"
            tasks = [
                {"task_title": "Open your project file and scan the first requirement line", "estimated_minutes": 5, "justification": "Sustains momentum by lowering starting friction to absolute zero."},
                {"task_title": "Jot down a quick 3-bullet list mapping out the next steps", "estimated_minutes": 5, "justification": "Clears starting anxiety by visualizing a micro-progress track."},
                {"task_title": "Locate and open your presentation slide template tool", "estimated_minutes": 5, "justification": "Prepares your environment so you are set up for success later."},
                {"task_title": "Draft just the title slide and introduction heading text", "estimated_minutes": 5, "justification": "Secures an easy win to break visual mental blocks."}
            ]
        elif "High" in payload.energy_level:
            strategy = "Peak Academic Execution Drive"
            tasks = [
                {"task_title": "Deep dive code structure and link your frontend layout to backend views", "estimated_minutes": 30, "justification": "Utilizes high focus spikes to conquer intense architectural logic tasks."},
                {"task_title": "Build out the core content slides detailing your project architecture", "estimated_minutes": 20, "justification": "Maintains a high production output rate to capture the technical depth cleanly."},
                {"task_title": "Refactor interface modules and clear your runtime console strings", "estimated_minutes": 15, "justification": "Polishes the system code for a flawless live demo presentation."},
                {"task_title": "Run a full presentation dress rehearsal from start to finish", "estimated_minutes": 15, "justification": "Locks in your pacing and delivery structure for tomorrow's judges."}
            ]
        else:
            strategy = "Balanced Academic Milestone Sprint"
            tasks = [
                {"task_title": "Review the assignment grading rubric and compliance requirements", "estimated_minutes": 10, "justification": "Ensures complete structural alignment before deeper development assets are locked."},
                {"task_title": "Flesh out the basic documentation structural outline headings", "estimated_minutes": 20, "justification": "Maintains uniform progress without triggering cognitive burnout cycles."},
                {"task_title": "Draft the architectural overview slide and add key feature screenshots", "estimated_minutes": 15, "justification": "Visually showcases your technical milestones step by step."},
                {"task_title": "Verify submission links and test your app build end-to-end", "estimated_minutes": 10, "justification": "Guarantees that your live link works perfectly for final evaluation."}
            ]
        
    # CODING / APP DEVELOPMENT CONTEXT
    elif any(word in task_lower for word in ["code", "bug", "app", "frontend", "backend", "github", "run", "program"]):
        if "Low" in payload.energy_level:
            strategy = "Five-Minute Coding Recovery"
            tasks = [
                {"task_title": "Boot your IDE editor window and open the file containing the script crash", "estimated_minutes": 5, "justification": "Clears starting friction instantly with zero cognitive workload overhead."},
                {"task_title": "Locate and isolate the specific terminal line throwing the error flag", "estimated_minutes": 5, "justification": "Breaks logic tracking into bite-sized, atomic visual tasks."}
            ]
        elif "High" in payload.energy_level:
            strategy = "Peak Developer Execution Drive"
            tasks = [
                {"task_title": "Reconstruct failing controller logic pathways with direct connection arrays", "estimated_minutes": 30, "justification": "Leverages sharp cognitive clarity spikes to debug structural problems."},
                {"task_title": "Compile deployment profiles and clear out obsolete validation dependencies", "estimated_minutes": 20, "justification": "Ensures optimal pipeline runtime speeds during live evaluations."}
            ]
        else:
            strategy = "Balanced Code Iteration Sprint"
            tasks = [
                {"task_title": "Isolate the core structural runtime modules using explicit logging streams", "estimated_minutes": 15, "justification": "Isolating variables provides high clarity for standard focus states."},
                {"task_title": "Draft a clear pseudocode logical layout for the patch architecture", "estimated_minutes": 15, "justification": "Organizing logic outlines ensures rapid, zero-error manual composition loops."}
            ]

    # GENERAL DEFAULT FALLBACK
    else:
        if "Low" in payload.energy_level:
            strategy = "Atomic Core Alignment"
            tasks = [
                {"task_title": f"Open up the primary digital workspace file folder for '{payload.task_description}'", "estimated_minutes": 5, "justification": "Low energy needs immediate action markers with absolute minimum overhead."},
                {"task_title": "Clear any redundant tabs out of your current visual desktop workspace", "estimated_minutes": 5, "justification": "Minimizing environmental distractions stabilizes cognitive target metrics."}
            ]
        elif "High" in payload.energy_level:
            strategy = "High-Velocity Target Execution"
            tasks = [
                {"task_title": f"Execute the heaviest structural milestone block for '{payload.task_description}'", "estimated_minutes": 25, "justification": "Maximizes deep work execution ratios while focus indicators are at their peak."},
                {"task_title": "Perform an internal feature evaluation checklist on your execution block", "estimated_minutes": 15, "justification": "Guarantees a clean quality pass across the pipeline core."}
            ]
        else:
            strategy = "Standard Progressive Milestone Sprint"
            tasks = [
                {"task_title": f"Isolate the first core step necessary to handle '{payload.task_description}'", "estimated_minutes": 15, "justification": "Standard focus levels are perfectly optimized for task structuring loops."},
                {"task_title": "Dedicate a clean ten-minute execution run toward completing your layout", "estimated_minutes": 10, "justification": "Building short, uninterrupted momentum breaks starting paralysis naturally."}
            ]

    return {
        "original_task": payload.task_description,
        "user_energy_level": payload.energy_level,
        "recommended_action_strategy": strategy,
        "suggested_micro_tasks": tasks
    }

@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(frontend_path, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h2>HabitFlow Frontend HTML template file not found!</h2>"