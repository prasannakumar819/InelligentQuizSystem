from flask import Flask, render_template, request, redirect, session, url_for
import os
import json
import re
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.ollama import OllamaEmbedding

# ---------- LLM SETUP ----------
GROQ_API_KEY = "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"  # <-- Put your actual key here

llm = Groq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0.0
)

embed_model = OllamaEmbedding(model_name="nomic-embed-text")
Settings.llm = llm
Settings.embed_model = embed_model

# ---------- APP SETUP ----------
app = Flask(__name__)
app.secret_key = "supersecretkey"

USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# ---------- COURSE STRUCTURE ----------
COURSES_DIR = "courses"
def load_course_topics():
    courses = {}
    if not os.path.exists(COURSES_DIR):
        return courses
    for course_name in os.listdir(COURSES_DIR):
        course_path = os.path.join(COURSES_DIR, course_name)
        if os.path.isdir(course_path):
            topics = [f.replace(".txt", "") for f in os.listdir(course_path) if f.endswith(".txt")]
            courses[course_name] = topics
    return courses
COURSES = load_course_topics()

# ---------- DOCUMENT RETRIEVER ----------
def get_retriever(topic, difficulty):
    file_path = os.path.join(os.getcwd(), "data", topic, f"{difficulty}.txt")
    if not os.path.exists(file_path):
        print(f"⚠ File not found: {file_path}")
        return None
    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
    index = VectorStoreIndex.from_documents(documents)
    return index.as_retriever(similarity_top_k=2)

# ---------- ROADMAP TOPICS ----------
ROADMAP_TOPICS = [
    "Introduction",
    "Machine Learning",
    "Deep Learning",
    "Natural Language Processing"
]

# ---------- UTILS ----------

def save_progress(username, quiz_data, score, weak_topics):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    history = users[username].get("history", [])


    percentage = (score / len(quiz_data)) * 100

    history.append({
        "score": score,
        "total_questions": len(quiz_data),
        "percentage": percentage,
        "topic": session.get("current_topic"),
        "difficulty": session.get("current_difficulty"),
        "weak_topics": weak_topics
})

    users[username]["history"] = history

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ================= ROUTES ================= #

@app.route("/")
def home():
    return redirect(url_for("dashboard") if "username" in session else url_for("login"))

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        if username in users:
            return "User already exists ❌"

        roadmap_progress = {topic: {"easy":"locked","medium":"locked","hard":"locked","status":"locked"} for topic in ROADMAP_TOPICS}
        roadmap_progress[ROADMAP_TOPICS[0]]["easy"] = "unlocked"
        roadmap_progress[ROADMAP_TOPICS[0]]["status"] = "in_progress"

        users[username] = {
            "password": password,
            "history": [],
            "roadmap_progress": roadmap_progress
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)

        session["username"] = username
        return redirect(url_for("dashboard"))

    return render_template("register.html")

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        if username in users and users[username]["password"] == password:
            session["username"] = username
            return redirect(url_for("dashboard"))
        return "Invalid credentials ❌"
    return render_template("login.html")

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    if username not in users:
        session.clear()
        return redirect(url_for("login"))

    user_data = users[username]
    if "roadmap_progress" not in user_data:
        roadmap_progress = {topic: {"easy":"locked","medium":"locked","hard":"locked","status":"locked"} for topic in ROADMAP_TOPICS}
        roadmap_progress[ROADMAP_TOPICS[0]]["easy"] = "unlocked"
        roadmap_progress[ROADMAP_TOPICS[0]]["status"] = "in_progress"
        user_data["roadmap_progress"] = roadmap_progress
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)

    history = user_data.get("history", [])
    roadmap = user_data.get("roadmap_progress", {})
    completed = sum(1 for t in ROADMAP_TOPICS if roadmap.get(t, {}).get("status") == "completed")
    progress_percent = int((completed / len(ROADMAP_TOPICS)) * 100)

    return render_template("dashboard.html",
                           username=username,
                           history=history,
                           roadmap=roadmap,
                           topics=ROADMAP_TOPICS,
                           progress_percent=progress_percent)

# ---------- QUIZ SETUP ----------
@app.route("/quiz/<topic>/<difficulty>", methods=["GET", "POST"])
def quiz_setup(topic, difficulty):
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    roadmap = users[username]["roadmap_progress"]
    if roadmap.get(topic, {}).get(difficulty) != "unlocked":
        return "This level is locked 🔒"

    if request.method == "POST":
        num_questions = int(request.form["num_questions"])
        retriever = get_retriever(topic, difficulty)
        if retriever is None:
            return "Content not found."

        nodes = retriever.retrieve(f"Generate quiz questions about {topic}")
        context = "\n\n".join([n.text for n in nodes])[:4000]

        prompt = f"""
Generate {num_questions} {difficulty} level multiple choice questions ONLY from topic: {topic}
Context:
{context}

Return STRICT JSON:
[
  {{
    "question": "Question text",
    "topic": "{topic}",
    "options": {{"A": "Option A","B": "Option B","C": "Option C","D": "Option D"}},
    "answer": "Correct option letter"
  }}
]
"""
        response = llm.complete(prompt)
        quiz_text = getattr(response, "text", str(response))

        try:
            quiz_data = json.loads(quiz_text)
        except:
            match = re.search(r"\[.*\]", quiz_text, re.DOTALL)
            if not match:
                return "Model did not return valid JSON."
            quiz_data = json.loads(match.group(0))

        session["quiz_data"] = quiz_data
        session["current_topic"] = topic
        session["current_difficulty"] = difficulty

        return render_template("quiz_attempt.html", quiz=quiz_data, topic=topic, difficulty=difficulty)

    return render_template("quiz_setup.html", topic=topic, difficulty=difficulty)

# ---------- SUBMIT QUIZ ----------
@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    quiz_data = session.get("quiz_data")
    topic = session.get("current_topic")
    difficulty = session.get("current_difficulty")

    if not quiz_data or not topic or not difficulty:
        return redirect(url_for("dashboard"))

    score = 0
    weak_topics = {}
    wrong_questions = []

    # ---------------- SCORING ----------------
    for i, q in enumerate(quiz_data):
        user_answer = request.form.get(f"q{i}")

        if user_answer == q["answer"]:
            score += 1
        else:
            weak_topics[q["topic"]] = weak_topics.get(q["topic"], 0) + 1

            wrong_questions.append({
                "question": q["question"],
                "options": q["options"],
                "correct_answer": q["answer"],
                "user_answer": user_answer
            })

    percentage = (score / len(quiz_data)) * 100

    # ---------------- GENERATE EXPLANATIONS ----------------
    explanations = []

    if wrong_questions:
        explanation_prompt = f"""
You are an educational AI tutor.

For each question:
1. Explain why the correct answer is correct.
2. Explain why the user's answer is incorrect.
3. Keep explanation clear and concise (3-4 sentences).

Return STRICT JSON:
[
  {{
    "question": "question text",
    "explanation": "full explanation here"
  }}
]

Questions:
{json.dumps(wrong_questions, indent=2)}
"""

        try:
            explanation_response = llm.complete(explanation_prompt)
            explanation_text = getattr(explanation_response, "text", str(explanation_response))

            try:
                explanations = json.loads(explanation_text)
            except:
                match = re.search(r"\[.*\]", explanation_text, re.DOTALL)
                if match:
                    explanations = json.loads(match.group(0))

        except Exception as e:
            print("Explanation generation error:", e)
            explanations = []

    # ---------------- ROADMAP UPDATE ----------------
    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    roadmap = users[username]["roadmap_progress"]

    if percentage >= 70:
        if difficulty == "easy":
            roadmap[topic]["easy"] = "completed"
            roadmap[topic]["medium"] = "unlocked"
        elif difficulty == "medium":
            roadmap[topic]["medium"] = "completed"
            roadmap[topic]["hard"] = "unlocked"
        elif difficulty == "hard":
            roadmap[topic]["hard"] = "completed"
            roadmap[topic]["status"] = "completed"
            idx = ROADMAP_TOPICS.index(topic)
            if idx + 1 < len(ROADMAP_TOPICS):
                next_topic = ROADMAP_TOPICS[idx + 1]
                if roadmap[next_topic]["easy"] == "locked":
                    roadmap[next_topic]["easy"] = "unlocked"
                    roadmap[next_topic]["status"] = "in_progress"

    save_progress(username, quiz_data, score, weak_topics)

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

    session.pop("quiz_data", None)
    session.pop("current_topic", None)
    session.pop("current_difficulty", None)

    return render_template(
        "result.html",
        score=score,
        total=len(quiz_data),
        percentage=percentage,
        weak_topics=weak_topics,
        explanations=explanations
    )

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- ANALYTICS ----------
@app.route("/analytics")
def analytics():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    history = users[username].get("history", [])

    return render_template("analytics.html", history=history)
if __name__ == "__main__":
    app.run(debug=True)