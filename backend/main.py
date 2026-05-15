"""
Jarvis AI Tutor - FastAPI Backend
An interactive AI tutor powered by Qwen2.5:7b-instruct
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx

# Base directory for all user data
BASE_DIR = Path("D:/ai/ai-tutor")

app = FastAPI(title="Jarvis AI Tutor")

# CORS for LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama endpoint
OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:7b-instruct"


# ==================== Pydantic Models ====================

class LoginRequest(BaseModel):
    username: str


class TopicRequest(BaseModel):
    username: str
    topic: str
    goal: str  # e.g., "pass Security+ cert" or "learn AI automation"


class QuizRequest(BaseModel):
    username: str
    topic: str
    module: str
    question_count: int = 5


class AnswerRequest(BaseModel):
    username: str
    topic: str
    module: str
    question_id: str
    answer: str
    is_quiz: bool = False


class ChatRequest(BaseModel):
    username: str
    message: str
    context: Optional[Dict[str, Any]] = None


class OnboardingStartRequest(BaseModel):
    username: str
    topic: str


class OnboardingAnswerRequest(BaseModel):
    username: str
    topic: str
    question_id: str
    answer: str
    question_text: str


# ==================== Memory System ====================

class MemorySystem:
    """Manages user-specific memory files similar to Claude Code's CLAUDE.md system"""

    MEMORY_TYPES = ["user_profile", "feedback", "project", "reference"]

    def __init__(self, username: str):
        self.username = username
        self.user_dir = BASE_DIR / username
        self.memory_dir = self.user_dir / "memory"
        self.lesson_plans_dir = self.user_dir / "lesson_plans"
        self.progress_file = self.user_dir / "progress.json"
        self._ensure_directories()

    def _ensure_directories(self):
        """Create user directories if they don't exist"""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.lesson_plans_dir.mkdir(parents=True, exist_ok=True)

    def _get_memory_path(self, memory_type: str) -> Path:
        """Get path to a memory file"""
        if memory_type == "user_profile":
            return self.memory_dir / "user_profile.md"
        elif memory_type == "feedback":
            return self.memory_dir / "feedback.md"
        elif memory_type == "project":
            return self.memory_dir / "project.md"
        elif memory_type == "reference":
            return self.memory_dir / "reference.md"
        return self.memory_dir / f"{memory_type}.md"

    def read_memory(self, memory_type: str) -> str:
        """Read a memory file"""
        path = self._get_memory_path(memory_type)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_memory(self, memory_type: str, content: str):
        """Write to a memory file"""
        path = self._get_memory_path(memory_type)
        path.write_text(content, encoding="utf-8")

    def append_memory(self, memory_type: str, entry: str):
        """Append an entry to a memory file"""
        path = self._get_memory_path(memory_type)
        existing = self.read_memory(memory_type)
        if existing:
            # Add separator between entries
            content = existing + "\n\n---\n\n" + entry
        else:
            content = entry
        self.write_memory(memory_type, content)

    def read_all_memories(self) -> Dict[str, str]:
        """Read all memory files"""
        return {
            mt: self.read_memory(mt)
            for mt in self.MEMORY_TYPES
        }

    def get_progress(self) -> Dict[str, Any]:
        """Get user's learning progress"""
        if not self.progress_file.exists():
            return {"topics": {}, "current_topic": None, "completed_modules": []}
        return json.loads(self.progress_file.read_text(encoding="utf-8"))

    def save_progress(self, progress: Dict[str, Any]):
        """Save user's learning progress"""
        self.progress_file.write_text(
            json.dumps(progress, indent=2),
            encoding="utf-8"
        )

    def get_lesson_plan(self, topic: str) -> Optional[str]:
        """Get a saved lesson plan for a topic"""
        # Sanitize topic for filename
        safe_topic = topic.replace("/", "_").replace("\\", "_").replace(":", "_")
        path = self.lesson_plans_dir / f"{safe_topic}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def save_lesson_plan(self, topic: str, plan: str):
        """Save a lesson plan"""
        safe_topic = topic.replace("/", "_").replace("\\", "_").replace(":", "_")
        path = self.lesson_plans_dir / f"{safe_topic}.md"
        path.write_text(plan, encoding="utf-8")


# ==================== Ollama Client ====================

async def call_ollama(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
    """Call Ollama API and get response"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature}
                }
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except httpx.ConnectError as e:
            raise HTTPException(status_code=503, detail=f"Cannot connect to Ollama: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama error: {e}")


# ==================== Assessment System ====================

async def generate_onboarding_questions(topic: str, context: str = "") -> List[Dict[str, Any]]:
    """Generate multiple choice onboarding questions for a topic"""

    system_prompt = """You are Jarvis, an AI tutor conducting an onboarding assessment.
Generate 6-10 multiple choice questions to assess the user's current knowledge level.

Rules:
- Each question has exactly 4 options (A, B, C, D)
- Only ONE option is correct
- Questions should range from beginner to intermediate difficulty
- Cover different subtopics within the main topic
- Format each question as JSON with: id, question, options (object with A,B,C,D), correct_answer, subtopic

Output ONLY a JSON array of questions. No other text."""

    user_prompt = f"""Topic: {topic}
{f"Context: {context}" if context else ""}

Generate 8 multiple choice questions to assess knowledge level."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await call_ollama(messages, temperature=0.3)

    # Parse JSON from response
    import re
    import logging
    logging.info(f"Raw response: {response[:500]}...")

    json_match = re.search(r'\[.*\]', response, re.DOTALL)
    if json_match:
        try:
            questions = json.loads(json_match.group())
            logging.info(f"Parsed {len(questions)} questions")
            return questions
        except json.JSONDecodeError as e:
            logging.error(f"JSON parse error: {e}")
            logging.error(f"JSON string: {json_match.group()[:200]}")

    # Fallback: return empty if parsing fails
    return []


async def generate_curriculum(topic: str, goal: str, assessment_results: Dict[str, Any]) -> str:
    """Generate a lesson plan based on topic, goal, and assessment results"""

    system_prompt = """You are Jarvis, an AI tutor creating personalized lesson plans.

Create a structured curriculum that:
1. Focuses on areas the user needs to learn (based on assessment gaps)
2. Builds from fundamentals to advanced concepts
3. Includes practical exercises
4. Has clear module boundaries with quiz checkpoints
5. Is tailored to the user's stated goal

Format the lesson plan as Markdown with:
- # Topic Name
- ## Goal
- ## Assessment Summary (what they know vs need to learn)
- ## Modules (numbered, with topics and learning objectives)
- ## Estimated Time per Module
- ## Prerequisites (if any)
- ## Resources (optional recommendations)"""

    weak_areas = ", ".join(assessment_results.get("weak_areas", []))
    strong_areas = ", ".join(assessment_results.get("strong_areas", []))

    user_prompt = f"""Topic: {topic}
Goal: {goal}

Assessment Results:
- Strong areas: {strong_areas if strong_areas else "None identified"}
- Areas to focus on: {weak_areas if weak_areas else "Full curriculum needed"}

Create a personalized lesson plan."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    return await call_ollama(messages, temperature=0.5)


async def generate_module_content(topic: str, module: str, module_content: str) -> str:
    """Generate teaching content for a specific module"""

    system_prompt = """You are Jarvis, an engaging AI tutor.

Teach the module content:
- Use clear, conversational explanations
- Include examples and analogies
- Break complex concepts into digestible parts
- Use formatting (bold, lists, code blocks) for clarity
- End with a brief summary of key points

Be encouraging and supportive. Acknowledge that learning takes time."""

    user_prompt = f"""Topic: {topic}
Module: {module}

Content to cover:
{module_content}

Teach this module in an engaging way."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    return await call_ollama(messages, temperature=0.7)


async def generate_quiz(topic: str, module: str, content: str, question_count: int = 5) -> List[Dict[str, Any]]:
    """Generate a quiz for a module"""

    system_prompt = """You are Jarvis, an AI tutor creating quiz questions.

Generate multiple choice questions to test understanding:
- Each question has exactly 4 options (A, B, C, D)
- Only ONE option is correct
- Questions should test comprehension, not just recall
- Include at least one scenario-based question

Output ONLY a JSON array with: id, question, options (object with A,B,C,D), correct_answer, explanation"""

    user_prompt = f"""Topic: {topic}
Module: {module}

Content covered:
{content}

Generate {question_count} quiz questions."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await call_ollama(messages, temperature=0.3)

    import re
    json_match = re.search(r'\[.*\]', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return []


async def evaluate_answer(question: Dict, user_answer: str) -> Dict[str, Any]:
    """Evaluate a quiz answer and provide feedback"""

    is_correct = user_answer.strip().upper() == question.get("correct_answer", "").upper()

    system_prompt = """You are Jarvis, providing helpful feedback on quiz answers.

Be encouraging whether the answer is right or wrong.
If wrong, explain why and teach the concept.
If right, reinforce why it's correct."""

    user_prompt = f"""Question: {question.get('question')}
Options: {question.get('options')}
Correct Answer: {question.get('correct_answer')}
User's Answer: {user_answer}
Explanation: {question.get('explanation', '')}

Provide feedback."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    feedback = await call_ollama(messages, temperature=0.5)

    return {
        "is_correct": is_correct,
        "correct_answer": question.get("correct_answer"),
        "feedback": feedback
    }


# ==================== API Routes ====================

@app.get("/api/health")
async def health_check():
    """Check if the API is running"""
    return {"status": "ok", "model": MODEL}


@app.post("/api/login")
async def login(request: LoginRequest):
    """Login as a user - creates user directory if new"""
    memory = MemorySystem(request.username)

    # Check if user exists
    profile = memory.read_memory("user_profile")
    is_new = not bool(profile)

    if is_new:
        # Create initial user profile
        profile_content = f"""---
name: {request.username}
created: {datetime.now().isoformat()}
---

# User Profile: {request.username}

Learning journey started on {datetime.now().strftime('%Y-%m-%d')}."""
        memory.write_memory("user_profile", profile_content)

    return {
        "username": request.username,
        "is_new": is_new,
        "progress": memory.get_progress()
    }


@app.post("/api/start-onboarding")
async def start_onboarding(request: OnboardingStartRequest):
    """Start onboarding for a topic"""
    memory = MemorySystem(request.username)

    # Save the topic to user profile
    profile = memory.read_memory("user_profile")
    if f"Topic: {request.topic}" not in profile:
        memory.append_memory("user_profile", f"\n## Current Focus: {request.topic}")

    # Generate questions
    questions = await generate_onboarding_questions(request.topic)

    # Store questions in memory for this session (we'll use progress.json)
    progress = memory.get_progress()
    progress["onboarding"] = {
        "topic": request.topic,
        "questions": questions,
        "answers": {},
        "completed": False
    }
    memory.save_progress(progress)

    return {
        "questions": questions,
        "total": len(questions)
    }


@app.post("/api/onboarding/answer")
async def onboarding_answer(request: OnboardingAnswerRequest):
    """Record an onboarding answer"""
    memory = MemorySystem(request.username)
    progress = memory.get_progress()

    if "onboarding" not in progress:
        raise HTTPException(status_code=400, detail="Onboarding not started")

    # Record the answer
    progress["onboarding"]["answers"][request.question_id] = {
        "answer": request.answer,
        "question_text": request.question_text,
        "correct": None  # We'll calculate after all answers
    }
    memory.save_progress(progress)

    return {"recorded": True}


@app.post("/api/onboarding/complete")
async def complete_onboarding(request: OnboardingStartRequest):
    """Complete onboarding and analyze results"""
    memory = MemorySystem(request.username)
    progress = memory.get_progress()

    if "onboarding" not in progress:
        raise HTTPException(status_code=400, detail="Onboarding not started")

    onboarding = progress["onboarding"]
    questions = onboarding.get("questions", [])
    answers = onboarding.get("answers", {})

    # Analyze results
    correct_count = 0
    weak_areas = []
    strong_areas = []
    subtopic_results = {}

    for q in questions:
        qid = q.get("id")
        if qid in answers:
            user_answer = answers[qid].get("answer", "")
            is_correct = user_answer.strip().upper() == q.get("correct_answer", "").upper()

            subtopic = q.get("subtopic", "General")
            if subtopic not in subtopic_results:
                subtopic_results[subtopic] = {"correct": 0, "total": 0}
            subtopic_results[subtopic]["total"] += 1
            if is_correct:
                subtopic_results[subtopic]["correct"] += 1
                correct_count += 1

    # Determine weak vs strong areas
    for subtopic, results in subtopic_results.items():
        accuracy = results["correct"] / results["total"] if results["total"] > 0 else 0
        if accuracy < 0.5:
            weak_areas.append(subtopic)
        elif accuracy >= 0.8:
            strong_areas.append(subtopic)

    # Save assessment summary
    assessment = {
        "topic": request.topic,
        "total_questions": len(questions),
        "correct": correct_count,
        "accuracy": correct_count / len(questions) if questions else 0,
        "weak_areas": weak_areas,
        "strong_areas": strong_areas,
        "subtopic_results": subtopic_results,
        "completed_at": datetime.now().isoformat()
    }

    progress["onboarding"]["completed"] = True
    progress["onboarding"]["assessment"] = assessment
    progress["topics"] = progress.get("topics", {})
    progress["topics"][request.topic] = {
        "assessment": assessment,
        "status": "assessed"
    }
    memory.save_progress(progress)

    # Save to feedback memory
    feedback_entry = f"""---
date: {datetime.now().isoformat()}
type: assessment
topic: {request.topic}
---

## Onboarding Assessment Results

**Accuracy:** {assessment['accuracy']:.0%} ({assessment['correct']}/{assessment['total_questions']})

**Strong Areas:** {', '.join(strong_areas) if strong_areas else 'None identified'}

**Areas to Focus On:** {', '.join(weak_areas) if weak_areas else 'All areas need attention'}

This assessment will inform the personalized lesson plan."""

    memory.append_memory("feedback", feedback_entry)

    return assessment


@app.post("/api/generate-curriculum")
async def generate_curriculum_endpoint(request: TopicRequest):
    """Generate and save a curriculum for a topic"""
    memory = MemorySystem(request.username)
    progress = memory.get_progress()

    # Get assessment results
    topic_data = progress.get("topics", {}).get(request.topic, {})
    assessment = topic_data.get("assessment", {})

    # Generate curriculum
    curriculum = await generate_curriculum(request.topic, request.goal, assessment)

    # Save lesson plan
    memory.save_lesson_plan(request.topic, curriculum)

    # Update progress
    progress["topics"][request.topic]["curriculum"] = curriculum
    progress["topics"][request.topic]["status"] = "planned"
    progress["current_topic"] = request.topic
    memory.save_progress(progress)

    return {"curriculum": curriculum}


@app.get("/api/curriculum/{username}/{topic}")
async def get_curriculum(username: str, topic: str):
    """Get a saved curriculum"""
    memory = MemorySystem(username)
    curriculum = memory.get_lesson_plan(topic)
    if curriculum:
        return {"curriculum": curriculum}
    raise HTTPException(status_code=404, detail="Curriculum not found")


@app.post("/api/module/content")
async def get_module_content(request: BaseModel):
    """Get teaching content for a module"""
    # Parse request manually since we're using a generic BaseModel
    data = request.model_dump() if hasattr(request, 'model_dump') else request.dict()

    content = await generate_module_content(
        data.get("topic", ""),
        data.get("module", ""),
        data.get("module_content", "")
    )

    return {"content": content}


@app.post("/api/quiz/generate")
async def generate_quiz_endpoint(request: QuizRequest):
    """Generate a quiz for a module"""
    memory = MemorySystem(request.username)
    curriculum = memory.get_lesson_plan(request.topic)

    quiz = await generate_quiz(
        request.topic,
        request.module,
        curriculum or f"Module: {request.module}",
        request.question_count
    )

    return {"quiz": quiz}


@app.post("/api/quiz/evaluate")
async def evaluate_quiz_answer(request: AnswerRequest):
    """Evaluate a quiz answer"""
    # Parse the question from context or regenerate
    # For now, we'll need the full question in the request
    question = request.context.get("question", {}) if request.context else {}

    result = await evaluate_answer(question, request.answer)

    # Track wrong answers for re-teaching
    if not result["is_correct"]:
        memory = MemorySystem(request.username)
        progress = memory.get_progress()

        if "needs_reteach" not in progress:
            progress["needs_reteach"] = []

        progress["needs_reteach"].append({
            "topic": request.topic,
            "module": request.module,
            "question": question.get("question", ""),
            "timestamp": datetime.now().isoformat()
        })
        memory.save_progress(progress)

    return result


@app.post("/api/module/complete")
async def complete_module(request: BaseModel):
    """Mark a module as completed"""
    data = request.model_dump() if hasattr(request, 'model_dump') else request.dict()

    memory = MemorySystem(data.get("username"))
    progress = memory.get_progress()

    topic = data.get("topic")
    module = data.get("module")

    if "completed_modules" not in progress:
        progress["completed_modules"] = []

    progress["completed_modules"].append({
        "topic": topic,
        "module": module,
        "completed_at": datetime.now().isoformat()
    })

    if "topics" not in progress:
        progress["topics"] = {}
    if topic not in progress["topics"]:
        progress["topics"][topic] = {}

    progress["topics"][topic]["current_module"] = module
    progress["topics"][topic]["status"] = "in_progress"

    memory.save_progress(progress)

    return {"success": True}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat with Jarvis for teaching/learning"""
    memory = MemorySystem(request.username)

    # Build context from memories
    memories = memory.read_all_memories()
    progress = memory.get_progress()

    # Get relevant context
    topic_context = ""
    if request.context and request.context.get("topic"):
        topic_data = progress.get("topics", {}).get(request.context["topic"], {})
        curriculum = topic_data.get("curriculum", "")
        if curriculum:
            topic_context = f"\n\nCurriculum context:\n{curriculum[:2000]}"

    # Build conversation history from session (simplified - just current message)
    system_prompt = """You are Jarvis, an engaging and supportive AI tutor.

Your role:
- Teach concepts clearly with examples and analogies
- Adapt to the learner's level
- Be encouraging and patient
- Use formatting (bold, lists, code blocks) for clarity
- Ask probing questions to check understanding
- Connect new concepts to what they already know

Keep responses focused and digestible. Break complex topics into steps."""

    user_message = request.message
    if topic_context:
        user_message += topic_context

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    response = await call_ollama(messages, temperature=0.7)

    # Save to project memory (learning session log)
    memory.append_memory("project", f"""---
date: {datetime.now().isoformat()}
type: learning_session
topic: {request.context.get('topic', 'General')}
---

**User:** {request.message[:200]}

**Jarvis:** {response[:500]}...""")

    return {"response": response}


@app.get("/api/users/{username}/progress")
async def get_user_progress(username: str):
    """Get user's learning progress"""
    memory = MemorySystem(username)
    return memory.get_progress()


@app.get("/api/users/{username}/memories")
async def get_user_memories(username: str):
    """Get all user memories"""
    memory = MemorySystem(username)
    return memory.read_all_memories()


# ==================== Frontend Serving ====================

# Mount the frontend static files
FRONTEND_DIR = BASE_DIR / "frontend" / "dist"

@app.get("/")
async def serve_index():
    """Serve the React app"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        status_code=404,
        content={"error": "Frontend not built. Run: cd frontend && npm install && npm run build"}
    )


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 for LAN access
    uvicorn.run(app, host="0.0.0.0", port=8000)
