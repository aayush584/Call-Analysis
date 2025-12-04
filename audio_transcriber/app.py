from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import uuid
import json
import mimetypes
from typing import Optional, List
from pydantic import BaseModel
from pathlib import Path

# Get the directory where app.py is located
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Audio Transcription & Summarization")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"

TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)

# Custom questions file
CUSTOM_QUESTIONS_FILE = DATA_DIR / "custom_questions.json"

# Static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Store job status
jobs = {}

# Lazy loading
transcriber = None
evaluator = None

def get_transcriber():
    global transcriber
    if transcriber is None:
        from transcriber import AudioTranscriber
        transcriber = AudioTranscriber()
    return transcriber

def get_evaluator():
    global evaluator
    if evaluator is None:
        from evaluator import CallEvaluator
        evaluator = CallEvaluator()
    return evaluator


# Pydantic Models
class QuestionModel(BaseModel):
    id: str
    category: str
    question: str
    description: str = ""
    weight: int = 3
    enabled: bool = True


class QuestionUpdate(BaseModel):
    category: Optional[str] = None
    question: Optional[str] = None
    description: Optional[str] = None
    weight: Optional[int] = None
    enabled: Optional[bool] = None


class CategoryModel(BaseModel):
    name: str
    description: str = ""
    icon: str = "fa-question"
    color: str = "#6366f1"


def load_custom_questions():
    """Load custom questions from file or return defaults"""
    if CUSTOM_QUESTIONS_FILE.exists():
        with open(CUSTOM_QUESTIONS_FILE, 'r') as f:
            return json.load(f)
    else:
        # Return default questions
        from questions_config import PREDEFINED_QUESTIONS, QUESTION_CATEGORIES
        return {
            "questions": [
                {**q, "enabled": True} for q in PREDEFINED_QUESTIONS
            ],
            "categories": QUESTION_CATEGORIES
        }


def save_custom_questions(data):
    """Save custom questions to file"""
    with open(CUSTOM_QUESTIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ============== QUESTION MANAGEMENT ENDPOINTS ==============

@app.get("/api/questions")
async def get_questions():
    """Get all questions (custom or default)"""
    return load_custom_questions()


@app.post("/api/questions")
async def add_question(question: QuestionModel):
    """Add a new question"""
    data = load_custom_questions()
    
    # Check if ID already exists
    if any(q['id'] == question.id for q in data['questions']):
        raise HTTPException(status_code=400, detail="Question ID already exists")
    
    data['questions'].append(question.dict())
    save_custom_questions(data)
    
    return {"message": "Question added successfully", "question": question.dict()}


@app.put("/api/questions/{question_id}")
async def update_question(question_id: str, update: QuestionUpdate):
    """Update an existing question"""
    data = load_custom_questions()
    
    question_idx = next((i for i, q in enumerate(data['questions']) if q['id'] == question_id), None)
    
    if question_idx is None:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Update only provided fields
    update_dict = update.dict(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            data['questions'][question_idx][key] = value
    
    save_custom_questions(data)
    
    return {"message": "Question updated successfully", "question": data['questions'][question_idx]}


@app.delete("/api/questions/{question_id}")
async def delete_question(question_id: str):
    """Delete a question"""
    data = load_custom_questions()
    
    original_len = len(data['questions'])
    data['questions'] = [q for q in data['questions'] if q['id'] != question_id]
    
    if len(data['questions']) == original_len:
        raise HTTPException(status_code=404, detail="Question not found")
    
    save_custom_questions(data)
    
    return {"message": "Question deleted successfully"}


@app.post("/api/questions/{question_id}/toggle")
async def toggle_question(question_id: str):
    """Toggle question enabled/disabled"""
    data = load_custom_questions()
    
    question = next((q for q in data['questions'] if q['id'] == question_id), None)
    
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question['enabled'] = not question.get('enabled', True)
    save_custom_questions(data)
    
    return {"message": "Question toggled", "enabled": question['enabled']}


@app.post("/api/questions/reorder")
async def reorder_questions(question_ids: List[str]):
    """Reorder questions based on provided ID list"""
    data = load_custom_questions()
    
    # Create a map of questions by ID
    questions_map = {q['id']: q for q in data['questions']}
    
    # Reorder based on provided list
    reordered = []
    for qid in question_ids:
        if qid in questions_map:
            reordered.append(questions_map[qid])
            del questions_map[qid]
    
    # Add any remaining questions not in the list
    reordered.extend(questions_map.values())
    
    data['questions'] = reordered
    save_custom_questions(data)
    
    return {"message": "Questions reordered successfully"}


@app.post("/api/questions/reset")
async def reset_questions():
    """Reset to default questions"""
    if CUSTOM_QUESTIONS_FILE.exists():
        os.remove(CUSTOM_QUESTIONS_FILE)
    
    return {"message": "Questions reset to defaults", "data": load_custom_questions()}


# ============== CATEGORY MANAGEMENT ==============

@app.post("/api/categories")
async def add_category(category: CategoryModel):
    """Add a new category"""
    data = load_custom_questions()
    
    if category.name in data['categories']:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    data['categories'][category.name] = {
        "description": category.description,
        "icon": category.icon,
        "color": category.color
    }
    
    save_custom_questions(data)
    
    return {"message": "Category added successfully"}


@app.delete("/api/categories/{category_name}")
async def delete_category(category_name: str):
    """Delete a category (questions in this category will be moved to 'General')"""
    data = load_custom_questions()
    
    if category_name not in data['categories']:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Move questions to General
    for q in data['questions']:
        if q.get('category') == category_name:
            q['category'] = 'General'
    
    del data['categories'][category_name]
    save_custom_questions(data)
    
    return {"message": "Category deleted successfully"}


# ============== AUDIO PROCESSING ENDPOINTS ==============

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file and return job ID"""
    
    allowed_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    job_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "message": "File uploaded successfully",
        "file_path": str(file_path),
        "filename": file.filename,
        "result": None
    }
    
    return {"job_id": job_id, "message": "File uploaded successfully"}


@app.post("/process/{job_id}")
async def process_audio(job_id: str, background_tasks: BackgroundTasks):
    """Start processing the uploaded audio"""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if jobs[job_id]["status"] == "processing":
        raise HTTPException(status_code=400, detail="Job already processing")
    
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["progress"] = 0
    jobs[job_id]["message"] = "Starting processing..."
    
    background_tasks.add_task(process_audio_task, job_id)
    
    return {"message": "Processing started"}


def process_audio_task(job_id: str):
    """Background task to process audio"""
    trans = get_transcriber()
    try:
        file_path = jobs[job_id]["file_path"]
        
        # Step 1: Load models
        jobs[job_id]["progress"] = 5
        jobs[job_id]["message"] = "Loading models..."
        
        # Models are lazily loaded inside the transcriber; this just ensures the
        # singleton instance is created.
        
        # Step 2: Diarization
        jobs[job_id]["progress"] = 15
        jobs[job_id]["message"] = "Running speaker diarization..."
        
        diarization = trans.run_diarization(file_path)
        
        # Step 3: Transcription
        jobs[job_id]["progress"] = 30
        jobs[job_id]["message"] = "Transcribing audio segments..."
        
        def update_transcription_progress(p):
            jobs[job_id]["progress"] = 30 + int(p * 30)
            jobs[job_id]["message"] = f"Transcribing... {int(p * 100)}%"
        
        transcript = trans.transcribe_segments(
            file_path,
            diarization,
            progress_callback=update_transcription_progress
        )
        
        # Step 4: Summarization
        jobs[job_id]["progress"] = 65
        jobs[job_id]["message"] = "Generating summary..."
        
        summary, formatted = trans.summarize(transcript)
        
        # Step 5: Question Evaluation - Use only ENABLED questions
        jobs[job_id]["progress"] = 75
        jobs[job_id]["message"] = "Evaluating call quality..."
        
        # Get enabled questions only
        questions_data = load_custom_questions()
        enabled_questions = [q for q in questions_data['questions'] if q.get('enabled', True)]
        
        eval_instance = get_evaluator()
        evaluation = eval_instance.evaluate_questions(formatted, summary, enabled_questions)
        
        # Step 6: Get stats
        jobs[job_id]["progress"] = 95
        jobs[job_id]["message"] = "Finalizing..."
        
        speaker_stats = trans.get_speaker_stats(transcript)
        
        # Complete
        jobs[job_id]["progress"] = 100
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "Processing complete!"
        jobs[job_id]["result"] = {
            "job_id": job_id,
            "transcript": transcript,
            "formatted_transcript": formatted,
            "summary": summary,
            "speaker_stats": speaker_stats,
            "filename": jobs[job_id]["filename"],
            "evaluation": evaluation,
            "audio_url": f"/audio/{job_id}"
        }
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error: {str(e)}"
        import traceback
        traceback.print_exc()
        print(f"Error processing {job_id}: {e}")
    finally:
        # After each job, aggressively clear inference-time memory while keeping
        # the heavy models (ASR, diarization, LLM backend) resident.
        if hasattr(trans, "_clear_inference_memory"):
            trans._clear_inference_memory()


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "result": job.get("result")
    }


@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Delete job and associated files"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if "file_path" in jobs[job_id]:
        try:
            os.remove(jobs[job_id]["file_path"])
        except:
            pass
    
    del jobs[job_id]
    return {"message": "Job deleted"}


@app.get("/audio/{job_id}")
async def get_audio(job_id: str, download: bool = Query(False)):
    """Stream or download the original uploaded audio for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Audio available after processing completes")
    
    file_path = job.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    media_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    response = FileResponse(file_path, media_type=media_type)
    
    if download:
        filename = job.get("filename") or Path(file_path).name
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    return response


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    print(f"Base directory: {BASE_DIR}")
    print(f"Templates directory: {TEMPLATES_DIR}")
    print(f"Static directory: {STATIC_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000) 