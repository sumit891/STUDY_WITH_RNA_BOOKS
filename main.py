import os
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, send_from_directory

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Categories
CATEGORIES = ["jee", "neet"]

# Books database file
BOOKS_JSON = "books.json"

# Local uploads (for covers only)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
for c in CATEGORIES:
    os.makedirs(os.path.join(UPLOAD_FOLDER, c), exist_ok=True)


# ------------------ Utility ------------------
def load_books():
    if not os.path.exists(BOOKS_JSON):
        return {c: [] for c in CATEGORIES}
    with open(BOOKS_JSON, "r") as f:
        return json.load(f)


def save_books(data):
    with open(BOOKS_JSON, "w") as f:
        json.dump(data, f, indent=2)


books_data = load_books()


# ------------------ Routes ------------------

@app.route("/")
def index():
    query = request.args.get("q", "").lower()
    filtered = {c: [] for c in CATEGORIES}

    for c, books in books_data.items():
        for b in books:
            if query in b["file"].lower():
                filtered[c].append(b)

    return render_template("Books.html", files=filtered, query=query, is_admin=("admin" in session))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password == "admin123":  # change password
            session["admin"] = True
            return redirect(url_for("index"))
        else:
            flash("Invalid password")
    return render_template("admin.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


# ------------------ Upload ------------------

@app.route("/upload", methods=["POST"])
def upload_file():
    if "admin" not in session:
        return "Unauthorized", 403

    category = request.form.get("category")
    if category not in CATEGORIES:
        return "Invalid category", 400

    file = request.files.get("book")
    cover = request.files.get("cover")

    if not file:
        return "No file uploaded", 400

    # -------- Upload PDF to GoFile --------
    try:
        r = requests.post("https://upload.gofile.io/uploadFile", files={"file": (file.filename, file.stream)})
        res = r.json()
        if res.get("status") != "ok":
            return f"GoFile upload failed: {res}", 500
        download_page = res["data"]["downloadPage"]
        direct_link = res["data"]["directLink"] if "directLink" in res["data"] else None
    except Exception as e:
        return f"Error uploading to GoFile: {e}", 500

    # -------- Save cover locally --------
    cover_name = None
    if cover:
        cover_name = cover.filename
        cover_path = os.path.join(UPLOAD_FOLDER, category, cover_name)
        cover.save(cover_path)

    # -------- Save record --------
    books_data[category].append({
        "file": file.filename,
        "gofile_page": download_page,
        "direct_link": direct_link,
        "image": cover_name
    })
    save_books(books_data)

    flash("✅ Book uploaded successfully")
    return redirect(url_for("index"))


# ------------------ Serve Files ------------------

@app.route("/view/<category>/<filename>")
def view_file(category, filename):
    if category not in CATEGORIES:
        return "Invalid category", 404

    for book in books_data.get(category, []):
        if book["file"] == filename:
            try:
                r = requests.get(book["direct_link"], stream=True)
                if r.status_code != 200:
                    return "Error fetching file", 500
                return Response(
                    r.iter_content(chunk_size=8192),
                    content_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename={filename}"}
                )
            except Exception as e:
                return f"Error fetching file: {e}", 500
    return "File not found", 404


@app.route("/download/<category>/<filename>")
def download_file(category, filename):
    if category not in CATEGORIES:
        return "Invalid category", 404

    for book in books_data.get(category, []):
        if book["file"] == filename:
            try:
                r = requests.get(book["direct_link"], stream=True)
                if r.status_code != 200:
                    return "Error fetching file", 500
                return Response(
                    r.iter_content(chunk_size=8192),
                    content_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            except Exception as e:
                return f"Error fetching file: {e}", 500
    return "File not found", 404


@app.route("/cover/<category>/<filename>")
def cover_file(category, filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, category), filename)


# ------------------ Run ------------------

if __name__ == "__main__":
    app.run(debug=True)
