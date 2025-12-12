from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests, json, os
from dotenv import load_dotenv

# ---------------- LOAD ENV ----------------
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

# ---------------- CONFIG ----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# ---------------- FIREBASE HELPERS ----------------
def save_user(uname, data):
    url = f"{FIREBASE_URL}/users/{uname}.json"
    requests.put(url, data=json.dumps(data))

def get_user(uname):
    url = f"{FIREBASE_URL}/users/{uname}.json"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json()
    return None

def update_history(uname, history):
    url = f"{FIREBASE_URL}/users/{uname}/history.json"
    requests.put(url, data=json.dumps(history))

# ---------------- PLANT CARE API ----------------
def plant_care_info(text):
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a plant care assistant. Answer only questions related to plants, "
                    "gardening, and plant care. If a question is not related to plants, politely refuse. "
                    "Always answer in English and use emojis."
                )
            },
            {"role": "user", "content": text}
        ]
    }

    r = requests.post(url, headers=headers, json=data)

    try:
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "⚠ API Error"

# ---------------- ROUTES ----------------
@app.route('/')
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"])

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        uname = request.form["username"].lower()
        pwd = request.form["password"]
        fullname = request.form["fullname"]

        if get_user(uname):
            flash("❌ Username already exists!", "danger")
            return redirect(url_for("signup"))

        data = {"password": pwd.lower(), "fullname": fullname, "history": []}
        save_user(uname, data)

        flash("✅ Signup successful!", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uname = request.form.get("username", "").lower()
        pwd = request.form.get("password", "").lower()

        user_data = get_user(uname)

        if user_data and user_data.get("password") == pwd:
            session["user"] = uname
            return redirect(url_for("home"))

        flash("❌ Wrong username or password", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop("user")
    flash("Logged out!", "success")
    return redirect(url_for("login"))

@app.route('/search', methods=["POST"])
def search():
    if "user" not in session:
        return redirect(url_for("login"))

    q = request.form["query"]
    ans = plant_care_info(q)

    user_data = get_user(session["user"])
    history = user_data.get("history", [])

    history.append(f"🌱 Q: {q}\n\n📝 A: {ans}")
    update_history(session["user"], history)

    return render_template("search.html", query=q, answer=ans)

@app.route('/history')
def history():
    if "user" not in session:
        return redirect(url_for("login"))

    user_data = get_user(session["user"])
    hist = user_data.get("history", [])

    return render_template("history.html", history=hist, user=session["user"])

# ---------------- DELETE ITEM ----------------
@app.route('/delete/<int:index>', methods=["POST"])
def delete_item(index):
    if "user" not in session:
        return redirect(url_for("login"))

    user = session["user"]
    data = get_user(user)
    history = data.get("history", [])

    if 0 <= index < len(history):
        history.pop(index)
        update_history(user, history)

    return redirect(url_for("history"))

# ---------------- REPLY ----------------
@app.route('/reply/<int:index>', methods=["POST"])
def reply(index):
    q = request.form["followup"]
    ans = plant_care_info(q)

    user = session["user"]
    user_data = get_user(user)
    history = user_data.get("history", [])

    history.append(f"🔁 Follow-up Q: {q}\n\n📝 A: {ans}")
    update_history(user, history)

    return redirect(url_for("history"))

# ---------------- REPLY MORE ----------------
@app.route('/reply_more/<int:index>', methods=["POST"])
def reply_more(index):
    q = request.form["followup_more"]
    ans = plant_care_info(q)

    user = session["user"]
    user_data = get_user(user)
    history = user_data.get("history", [])

    history.append(f"📌 More Info Q: {q}\n\n📝 A: {ans}")
    update_history(user, history)

    return redirect(url_for("history"))

if __name__ == "__main__":
    app.run(debug=True)
