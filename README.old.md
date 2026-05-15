# Jarvis AI Tutor

A personal AI tutor powered by Qwen2.5:7b-instruct, featuring a Claude Code-style memory system.

## Features

- **Multi-user support** - Each family member has their own learning profile
- **Knowledge assessment** - 6-10 MCQs per topic to gauge understanding
- **Personalized curricula** - Lesson plans tailored to your goals and knowledge gaps
- **Claude Code-style memory** - User profiles, feedback, project, and reference memories
- **Interactive lessons** - Chat with Jarvis to learn concepts
- **Module quizzes** - Test understanding with automatic grading and re-teach flags
- **Persistent progress** - Pick up where you left off

## Architecture

```
D:\ai\ai-tutor\
├── backend/           # FastAPI server
│   ├── main.py
│   └── requirements.txt
├── frontend/          # React app
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── {username}/        # User data (created automatically)
    └── memory/
        ├── user_profile.md
        ├── feedback.md
        ├── project.md
        └── reference.md
```

## Prerequisites

1. **Ollama** installed and running with `qwen2.5:7b-instruct` pulled
2. **Python 3.9+** for backend
3. **Node.js 18+** for frontend

## Installation

### 1. Install Backend Dependencies

```bash
cd D:\ai\ai-tutor\backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd D:\ai\ai-tutor\frontend
npm install
npm run build
```

## Running

### Option 1: Run Backend Only (for development)

```bash
cd D:\ai\ai-tutor\backend
python main.py
```

Then open http://localhost:8000 in your browser.

### Option 2: Start Script (Recommended)

Create a batch file `start.bat` in `D:\ai\ai-tutor\`:

```batch
@echo off
echo Starting Jarvis AI Tutor...
cd /d D:\ai\ai-tutor\backend
start "Jarvis Backend" python main.py
timeout /t 3
cd /d D:\ai\ai-tutor\frontend
echo Frontend is built and served by backend
echo.
echo Jarvis is running at: http://localhost:8000
echo Press any key to stop...
pause > nul
```

## LAN Access

The server binds to `0.0.0.0:8000`, making it accessible on your local network.

1. Find your machine's IP: `ipconfig` (look for IPv4 Address)
2. Family members can access: `http://YOUR_IP:8000`

## Memory System

Each user has 4 memory files (like Claude Code):

| File | Purpose |
|------|---------|
| `user_profile.md` | User info, created date, learning focus |
| `feedback.md` | Assessment results, what worked/didn't |
| `project.md` | Learning session logs, progress notes |
| `reference.md` | Resources, links, external references |

## Usage Flow

1. **Login** - Enter your name (no password)
2. **Choose topic** - What do you want to learn?
3. **Assessment** - Answer 6-10 MCQs to gauge knowledge
4. **Review results** - See strong areas and focus areas
5. **Generate curriculum** - Personalized lesson plan created
6. **Learn** - Chat with Jarvis about each module
7. **Quiz** - Test your understanding at module end
8. **Continue** - Wrong answers flagged for re-teaching

## Troubleshooting

**"Cannot connect to Ollama"**
- Make sure Ollama is running: `ollama serve`
- Check model is pulled: `ollama pull qwen2.5:7b-instruct`

**"Frontend not built"**
- Run: `cd frontend && npm install && npm run build`

**Can't access from other devices**
- Check Windows Firewall allows port 8000
- Verify your IP with `ipconfig`
