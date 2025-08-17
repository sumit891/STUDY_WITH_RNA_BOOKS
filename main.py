import os
import json
from flask import Flask, render_template, request, redirect, flash, send_from_directory, url_for, session

app = Flask(__name__)
app.secret_key = "super_secret_key"

BASE_FOLDER = "uploads"
CATEGORIES = ["jee", "neet"]

# JSON file where we save uploaded books
BOOK_JSON = "Book.json"

# Allowed extensions
ALLOWED_DOC_EXTENSIONS = {"pdf"}
ALLOWED_IMG_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename, allowed_exts):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_exts

# Ensure folders exist
os.makedirs(BASE_FOLDER, exist_ok=True)
for cat in CATEGORIES:
    os.makedirs(os.path.join(BASE_FOLDER, cat), exist_ok=True)

# Load books
def load_books():
    if not os.path.exists(BOOK_JSON):
        return {cat: [] for cat in CATEGORIES}
    with open(BOOK_JSON, "r") as f:
        return json.load(f)

# Save books
def save_books(data):
    with open(BOOK_JSON, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").lower()
    books = load_books()

    # Search filter
    filtered = {}
    for category, items in books.items():
        filtered[category] = [
            item for item in items if query in item["file"].lower()
        ] if query else items

    return render_template("books.html", files=filtered, query=query, is_admin=("admin" in session))

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin":
            session["admin"] = True
            return redirect("/")
        else:
            flash("Invalid credentials")
    return '''
    <form method="post">
        <input type="text" name="username" placeholder="Username"/>
        <input type="password" name="password" placeholder="Password"/>
        <button type="submit">Login</button>
    </form>
    '''

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# ---------------- UPLOAD ----------------
@app.route("/upload", methods=["POST"])
def upload():
    if "admin" not in session:
        return "Unauthorized", 403

    category = request.form.get("category")
    if category not in CATEGORIES:
        return "Invalid category", 400

    book_file = request.files.get("book")
    cover_file = request.files.get("cover")

    if not book_file or not allowed_file(book_file.filename, ALLOWED_DOC_EXTENSIONS):
        return "Invalid book file", 400

    book_path = os.path.join(BASE_FOLDER, category, book_file.filename)
    book_file.save(book_path)

    cover_filename = None
    if cover_file and allowed_file(cover_file.filename, ALLOWED_IMG_EXTENSIONS):
        cover_path = os.path.join(BASE_FOLDER, category, cover_file.filename)
        cover_file.save(cover_path)
        cover_filename = cover_file.filename

    data = load_books()
    data[category].append({"file": book_file.filename, "image": cover_filename})
    save_books(data)

    flash("Book uploaded successfully!")
    return redirect("/")

# ---------------- VIEW (OPEN PDF in browser) ----------------
@app.route("/view/<category>/<filename>")
def view_file(category, filename):
    return send_from_directory(
        os.path.join(BASE_FOLDER, category),
        filename,
        as_attachment=False   # ✅ Inline open in browser
    )

# ---------------- DOWNLOAD (force download) ----------------
@app.route("/download/<category>/<filename>")
def download_file(category, filename):
    return send_from_directory(
        os.path.join(BASE_FOLDER, category),
        filename,
        as_attachment=True   # ✅ Force download
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
