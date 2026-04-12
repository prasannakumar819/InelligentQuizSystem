🧠 AI-Powered Adaptive Learning & Quiz System

An intelligent roadmap-based quiz platform built using Flask + LlamaIndex + Groq LLM + Ollama Embeddings.

This system dynamically generates quizzes using AI and unlocks topics progressively based on user performance.

🚀 Features
🔐 User Authentication (Register / Login)
📚 Structured Learning Roadmap
🧠 AI-generated MCQ quizzes
🎯 Difficulty Levels (Easy → Medium → Hard)
🔓 Sequential Topic Unlocking
📊 Performance-based Progression
📈 Quiz History Tracking
🧩 Weak Topic Detection
🎨 Modern Animated Dashboard UI
🏗️ Project Architecture
User → Flask Backend → LlamaIndex → Groq LLM
                         ↓
                  Vector Retrieval
                         ↓
                  AI Quiz Generation
                         ↓
                  Roadmap Progress Update
📁 Project Structure
.
├── app.py
├── users.json
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── quiz_setup.html
│   ├── quiz_attempt.html
│   └── result.html
├── data/
│   ├── Introduction/
│   │   ├── easy.txt
│   │   ├── medium.txt
│   │   └── hard.txt
│   ├── Machine Learning/
│   ├── Deep Learning/
│   └── Natural Language Processing/
└── README.md
🧠 How The Roadmap System Works

Each topic contains:

{
  "easy": "locked | unlocked | completed",
  "medium": "locked | unlocked | completed",
  "hard": "locked | unlocked | completed",
  "status": "locked | in_progress | completed"
}
🔓 Unlock Logic
First topic → Easy unlocked by default
Score ≥ 70%:
Easy → unlock Medium
Medium → unlock Hard
Hard → mark topic completed
Completing Hard → unlock next topic

This creates a structured adaptive learning flow.

🤖 AI Quiz Generation Flow
User selects topic & difficulty

LlamaIndex retrieves relevant content from:

data/<topic>/<difficulty>.txt
Context is sent to Groq LLaMA 3.1 model
Model generates structured JSON quiz
Quiz is parsed and rendered dynamically
Score is calculated and roadmap updated
🛠️ Technologies Used
Python
Flask
LlamaIndex
Groq (LLaMA 3.1 8B Instant)
Ollama Embeddings (nomic-embed-text)
HTML5
CSS3 (Glassmorphism UI)
⚙️ Installation Guide
1️⃣ Clone Repository
git clone <your-repo-url>
cd project-folder
2️⃣ Create Virtual Environment
python -m venv venv

Activate:

Windows

venv\Scripts\activate

Mac/Linux

source venv/bin/activate
3️⃣ Install Dependencies
pip install flask llama-index groq llama-index-embeddings-ollama
4️⃣ Set API Key

Inside app.py:

os.environ["GROQ_API_KEY"] = "your_api_key_here"

Or set in terminal:

Windows

set GROQ_API_KEY=your_key

Mac/Linux

export GROQ_API_KEY=your_key
5️⃣ Run The App
python app.py

Open in browser:

http://127.0.0.1:5000
📊 Dashboard Overview
Displays learning roadmap
Shows unlocked and locked topics
Tracks quiz history
Shows user performance
📈 Future Improvements
🏆 Leaderboard System
📊 Admin Analytics Dashboard
🧾 Certificate Generation
☁️ Cloud Deployment (AWS / Render)
🗄️ Database Integration (MongoDB / PostgreSQL)
📱 Mobile Responsive Enhancement
👨‍💻 Project Purpose

This project demonstrates:

AI-driven content generation
Adaptive learning logic
LLM integration in web applications
Retrieval-Augmented Generation (RAG)
Progressive unlocking systems
Full-stack AI application architecture
📜 License

This project is for educational and demonstration purposes.