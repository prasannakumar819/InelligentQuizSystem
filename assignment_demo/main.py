import os
import json
import re
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ---------- USER MANAGEMENT ----------
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def register():
    print("----- REGISTER -----")
    username = input("Username: ").strip()
    password = input("Password: ").strip()  # changed from getpass.getpass
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    if username in users:
        print("User already exists. Try login.")
        return None
    users[username] = {"password": password, "history": []}
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)
    print(f"User {username} registered successfully ✅")
    return username

def login():
    print("----- LOGIN -----")
    username = input("Username: ").strip()
    password = input("Password: ").strip()  # changed from getpass.getpass
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    if username in users and users[username]["password"] == password:
        print(f"Welcome back, {username} 👋")
        return username
    else:
        print("Invalid username or password ❌")
        return None

def save_progress(username, quiz_data, score, weak_topics):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    history = users[username].get("history", [])
    history.append({
        "score": score,
        "total_questions": len(quiz_data),
        "weak_topics": weak_topics,
        "quiz_data": quiz_data
    })
    users[username]["history"] = history
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)
    print("Progress saved successfully ✅")

def show_dashboard(username):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    history = users[username].get("history", [])
    print(f"\n===== {username}'s Dashboard =====")
    if not history:
        print("No quiz history yet 📄")
        return
    total_quizzes = len(history)
    avg_score = sum([h["score"] for h in history]) / sum([h["total_questions"] for h in history]) * 100
    print(f"Total Quizzes Taken: {total_quizzes}")
    print(f"Average Score: {avg_score:.2f}%")
    weak_topics_counter = {}
    for h in history:
        for topic, mistakes in h["weak_topics"].items():
            weak_topics_counter[topic] = weak_topics_counter.get(topic, 0) + mistakes
    print("Overall Weak Topics:")
    if weak_topics_counter:
        for topic, mistakes in weak_topics_counter.items():
            print(f"{topic} → {mistakes} mistake(s)")
    else:
        print("No weak topics yet! 🔥")

# ---------- LOGIN OR REGISTER ----------
while True:
    choice = input("Do you want to (1) Login or (2) Register? ")
    if choice == "1":
        user = login()
        if user: break
    elif choice == "2":
        user = register()
        if user: break

# Show dashboard
show_dashboard(user)

# ---------- CONFIGURE MODEL ----------
llm = Ollama(model="llama3:8b", request_timeout=300.0, temperature=0.0)
embed_model = OllamaEmbedding(model_name="nomic-embed-text")
Settings.llm = llm
Settings.embed_model = embed_model

# ---------- LOAD DOCUMENTS ----------
print("\nLoading documents...")
documents = SimpleDirectoryReader("assignment_demo/data").load_data()
print("Building index...")
index = VectorStoreIndex.from_documents(documents)
retriever = index.as_retriever(similarity_top_k=2)

# ---------- USER INPUT ----------
num_questions = int(input("\nEnter number of questions: "))
difficulty = input("Enter difficulty (easy/medium/hard): ").strip().lower()

# ---------- RETRIEVE CONTEXT ----------
query = "Generate quiz questions from the document"
nodes = retriever.retrieve(query)
context = "\n\n".join([node.text for node in nodes])
context = context[:4000]

# ---------- BUILD PROMPT ----------
prompt = f"""
You are an exam generator.
Generate {num_questions} {difficulty} level multiple choice questions
ONLY from the provided context.

Context:
{context}

Return STRICTLY in this JSON format:

[
  {{
    "question": "Question text",
    "topic": "Main topic of question",
    "options": {{
      "A": "Option A",
      "B": "Option B",
      "C": "Option C",
      "D": "Option D"
    }},
    "answer": "Correct option letter",
    "explanation": "Short explanation"
  }}
]

Only return JSON.
"""

print("\nGenerating Quiz...\n")
response = llm.complete(prompt)
quiz_text = response.text if hasattr(response, "text") else str(response)

# ---------- PARSE JSON ----------
match = re.search(r"\[\s*{.*?}\s*\]", quiz_text, re.DOTALL)
if not match:
    print("⚠️ Could not detect valid JSON."); exit()
try: quiz_data = json.loads(match.group(0))
except json.JSONDecodeError: print("⚠️ Invalid JSON format."); exit()
if len(quiz_data) != num_questions:
    print("⚠️ Model returned incorrect number of questions."); exit()

# ---------- QUIZ MODE ----------
score = 0
weak_topics = {}
print("\n========== START QUIZ ==========")
for i, q in enumerate(quiz_data):
    print(f"\nQ{i+1}: {q['question']}\nTopic: {q['topic']}")
    for key, value in q["options"].items(): print(f"{key}) {value}")
    user_answer = input("Your answer (A/B/C/D): ").strip().upper()
    if user_answer == q["answer"]:
        print("Correct! ✅"); score += 1
    else:
        print(f"Wrong! ❌ Correct answer: {q['answer']}")
        print(f"Explanation: {q['explanation']}")
        weak_topics[q["topic"]] = weak_topics.get(q["topic"], 0) + 1

print("\n========== QUIZ COMPLETED ==========")
print(f"Final Score: {score}/{len(quiz_data)}")

print("\n========== WEAK TOPICS ==========")
if weak_topics:
    for topic, count in weak_topics.items():
        print(f"{topic} → {count} mistake(s)")
else:
    print("No weak topics! 🔥 Excellent performance!")

# Save progress
save_progress(user, quiz_data, score, weak_topics)

# ---------- ADAPTIVE ROUND ----------
if weak_topics:
    print("\n========== ADAPTIVE ROUND ==========")
    weak_topic_list = ", ".join(weak_topics.keys())
    adaptive_prompt = f"""
You are an exam generator.
The student made mistakes in these topics:
{weak_topic_list}

Generate {len(weak_topics)} new {difficulty} level multiple choice questions
focused ONLY on these weak topics.

Return STRICTLY in JSON format:

[
  {{
    "question": "Question text",
    "topic": "Main topic of question",
    "options": {{
      "A": "Option A",
      "B": "Option B",
      "C": "Option C",
      "D": "Option D"
    }},
    "answer": "Correct option letter",
    "explanation": "Short explanation"
  }}
]

Only return JSON.
"""
    response = llm.complete(adaptive_prompt)
    adaptive_text = response.text if hasattr(response, "text") else str(response)
    match = re.search(r"\[.*\]", adaptive_text, re.DOTALL)
    if match:
        json_string = match.group(0).replace("“", '"').replace("”", '"').replace("\n", " ")
        try:
            adaptive_data = json.loads(json_string)
            print("\nAdaptive Questions Generated Successfully ✅")
        except json.JSONDecodeError:
            print("⚠️ Adaptive JSON invalid. Skipping adaptive round.")
            adaptive_data = []
    else:
        print("⚠️ No JSON detected in adaptive response.")
        adaptive_data = []
else:
    print("\nNo adaptive round needed! 🔥")
    adaptive_data = []

# ---------- EXPORT TO PDF ----------
def export_to_pdf(filename, quiz_data, score, weak_topics):
    doc = SimpleDocTemplate(filename)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Quiz Results", styles["Title"]))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"Final Score: {score}/{len(quiz_data)}", styles["Normal"]))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Weak Topics:", styles["Heading2"]))
    if weak_topics:
        for topic, count in weak_topics.items():
            elements.append(Paragraph(f"{topic} - {count} mistake(s)", styles["Normal"]))
    else: elements.append(Paragraph("No weak topics", styles["Normal"]))
    elements.append(Spacer(1, 0.5*inch))
    for q in quiz_data:
        elements.append(Paragraph(f"Q: {q['question']}", styles["Normal"]))
        elements.append(Paragraph(f"Correct Answer: {q['answer']}", styles["Normal"]))
        elements.append(Paragraph(f"Explanation: {q['explanation']}", styles["Normal"]))
        elements.append(Spacer(1, 0.3*inch))
    doc.build(elements)

output_path = os.path.join(os.getcwd(), f"{user}_quiz_results.pdf")
export_to_pdf(output_path, quiz_data, score, weak_topics)
print(f"\nPDF exported at: {output_path}")