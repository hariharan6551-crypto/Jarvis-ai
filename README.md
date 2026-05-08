# J.A.R.V.I.S v2.0 — AI Operating System Copilot

> **Windows Copilot + Iron Man JARVIS + AI Agent + RPA Automation — Combined.**

An advanced AI desktop assistant with voice control, browser automation, Chrome profile management, OCR vision, multi-step task planning, and a futuristic JARVIS-style UI.

## ✨ Features

### Core Capabilities
- 🎙️ **Voice Control** — Say "Jarvis" + command (continuous listening)
- 🧠 **AI-Powered Reasoning** — Gemini/OpenAI/Claude/Ollama multi-provider
- 🖥️ **Full PC Control** — Open/close apps, volume, brightness, media, system
- 🌐 **Browser Automation** — Chrome profile detection & auto-login
- 👁️ **Vision + OCR** — Read screen text, find & click UI elements
- 📋 **Multi-Step Planning** — Complex commands decomposed into executable steps
- 💾 **Memory System** — SQLite history + ChromaDB semantic search
- 🔄 **Workflow Engine** — Retry logic, error recovery, progress tracking
- 📚 **Preference Learning** — Remembers your frequently used apps and habits

### What You Can Say
```
"Jarvis, open Chrome and select Mersal Hariharan account"
"Jarvis, search YouTube for Python tutorials"
"Jarvis, increase volume and open Spotify"
"Jarvis, take a screenshot"
"Jarvis, what's the CPU usage?"
"Jarvis, open VS Code"
"Jarvis, lock the computer"
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Chrome (for profile automation)

### Installation
```bash
cd C:\Users\harih\Desktop\Jarvis

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Install Playwright browsers (optional, for deep browser automation)
playwright install chromium

# Install frontend dependencies
cd ..\frontend
npm install

# Configure your API key
# Edit .env and set GEMINI_API_KEY
```

### Launch
```bash
# Option 1: Double-click JARVIS.bat
# Option 2: Python launcher
python launcher.py
# Option 3: Manual
cd backend && python main.py     # Terminal 1
cd frontend && npm run dev       # Terminal 2
cd frontend && npx electron .    # Terminal 3
```

## 🏗️ Architecture

```
Backend (FastAPI + WebSocket)
├── AI Provider (Gemini/OpenAI/Claude/Ollama)
├── Task Planner (multi-step command decomposition)
├── Automation Engine (pyautogui + Win32)
├── Browser Engine (Chrome profiles + Playwright)
├── Vision Engine (Tesseract OCR + screen reading)
├── Workflow Engine (retry + error recovery)
├── Memory Engine (SQLite + ChromaDB)
└── Voice Engine (Whisper STT + Edge TTS)

Frontend (Electron + React + Vite)
├── JARVIS Cyber UI (dark neon HUD)
├── AI Core Orb (animated state indicator)
├── Chrome Profile Panel (auto-detected)
├── Voice Waveform (real-time visualization)
├── Chat Interface (conversation history)
└── System Dashboard (CPU/RAM/Disk/Battery)
```

## 🔧 Configuration

Edit `.env` in the project root:
```
GEMINI_API_KEY=your_key_here
DEFAULT_AI_PROVIDER=gemini
DEFAULT_AI_MODEL=gemini-1.5-flash
TTS_PROVIDER=edge
EDGE_TTS_VOICE=en-US-GuyNeural
USER_NAME=Hari
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/command` | POST | Execute a text command |
| `/api/tts` | POST | Text-to-speech |
| `/api/status` | GET | System status |
| `/api/browser/profiles` | GET | Chrome profiles |
| `/api/browser/open-profile` | POST | Open Chrome with profile |
| `/api/vision/screen-text` | GET | OCR screen reading |
| `/api/vision/active-window` | GET | Active window info |
| `/ws` | WebSocket | Real-time communication |

## 📁 Project Structure

```
Jarvis/
├── backend/
│   ├── ai/          # AI providers, intent, task planner
│   ├── automation/  # Desktop, browser, vision, workflows
│   ├── config/      # Settings
│   ├── core/        # Logger
│   ├── memory/      # SQLite, ChromaDB, preferences
│   ├── services/    # Orchestrator
│   └── voice/       # Whisper STT, Edge TTS
├── frontend/
│   ├── electron/    # Desktop app
│   └── src/         # React UI components
└── scripts/         # Launchers & startup
```

---
**Version 2.0.0** — Built with ❤️ for Hari
