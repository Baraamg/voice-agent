# 🎤 VoiceAgent - Voice to Insight System

A scalable voice-to-insight system that converts audio recordings into structured insights using AI-powered transcription and natural language processing.

---

## ✅ Task Requirements & Implementation

### 🧠 System Architecture

* Created full system diagram using Mermaid in [README.md](#-system-architecture-diagram-mermaid)
* Modular design with separate services for transcription, NLP, and database
* Background task queue for audio processing
* SQLite for data persistence

### 🧩 Core Components

1. **Audio Ingestion**

   * Accepts WAV/MP3/M4A via `/upload_audio` endpoint
   * Files stored in `uploads/` directory
   * File validation & size checks in [`FileHandler`](app/utils/file_handler.py)

2. **Transcription**

   * Groq Whisper integration in [`TranscriptionService`](app/services/transcription.py)
   * Fallback handling and error recovery
   * Async processing

3. **NLP Analysis**

   * Groq LLM integration in [`NLPService`](app/services/nlp.py)
   * Structured JSON output with required fields
   * Multiple model fallbacks

4. **API Interface**

   * FastAPI backend in [`main.py`](app/main.py)
   * All required endpoints implemented
   * Background processing queue
   * Health checks

5. **Frontend**

   * Full Streamlit UI in [`streamlit_app.py`](streamlit_app.py)
   * File upload & results display
   * Real-time processing status
   * Search & filtering

### 🔧 Added Features

* Docker support with [Dockerfile](Dockerfile) and [docker-compose.yml](docker-compose.yml)
* Extensive error handling and logging
* API key setup script
* Modular code organization
* Sample audio files included

---

## 🧭 Quick Start

### 🔧 Setup (Local)

```bash
# Clone repo
git clone https://github.com/Techiewicky/voiceagent.git
cd voiceagent-system

# Create virtual env
python -m venv venv

# Windows
venv\Scripts\activate 

# macOS/Linux
source venv/bin/activate 

# Install dependencies
pip install -r requirements.txt

# Create folders
mkdir uploads data static templates

```



# Configure Environment 

```
# Windows
copy .env.example .env  
# macOS/Linux
cp .env.example .env    
```
# 2. ⚠️ IMPORTANT: Set API Key in .env file

### [YOU CAN FIND IT HERE](https://www.notion.so/IMPORTANT-Set-API-Key-in-env-file-23835cbce5dc8090bbc2db44b9128bb6?source=copy_link)

### ▶️ Run

```bash
# Terminal 1 - API Server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Streamlit Frontend
streamlit run streamlit_app.py --server.port 8501
```

* API: [http://localhost:8000](http://localhost:8000)
* Streamlit UI: [http://localhost:8501](http://localhost:8501)

---


## 📊 System Architecture Diagram (Mermaid)


![System Architecture](System%20diagram.png)


### ✅ [Click here for Adjustable Digram Link](https://www.mermaidchart.com/app/projects/59bb039b-329b-4c2c-9986-a17f1f56c730/diagrams/b3498056-5d61-4af0-b3eb-1acb6614c3a0/share/invite/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkb2N1bWVudElEIjoiYjM0OTgwNTYtNWQ2MS00YWYwLWIzZWItMWFjYjY2MTRjM2EwIiwiYWNjZXNzIjoiRWRpdCIsImlhdCI6MTc1MzIyNTYxMH0.prI5coa9VIDaAa42tzLrwbqe7kfz9eDLFQXGaIRYJx0)



> ✅ Tip: Use the Mermaid live editor at [https://mermaid.live](https://mermaid.live) to adjust layout.

---

## 🧪 Testing Tools
* Use **Streamlit** UI at `http://localhost:8501` for simple upload/test
* Use `Sample Audio.wav` (included) to test the website!

