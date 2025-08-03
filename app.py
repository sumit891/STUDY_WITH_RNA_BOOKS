
from flask import Flask, render_template, request, redirect, flash, send_from_directory, url_for, session
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret')

BASE_FOLDER = 'uploads'
CATEGORIES = ['jee', 'neet']
ALLOWED_DOC_EXTENSIONS = {'pdf', 'epub', 'txt', 'doc', 'docx'}
ALLOWED_IMG_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024

# Ensure category folders exist
for category in CATEGORIES:
    os.makedirs(os.path.join(BASE_FOLDER, category), exist_ok=True)

def allowed_file(filename, types):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in types

@app.route('/', methods=['GET'])
def home():
    query = request.args.get('q', '').lower()
    categorized_files = {}
    for category in CATEGORIES:
        folder_path = os.path.join(BASE_FOLDER, category)
        all_files = os.listdir(folder_path)
        books = []
        for f in all_files:
            if allowed_file(f, ALLOWED_DOC_EXTENSIONS):
                if query and query not in f.lower():
                    continue
                base = os.path.splitext(f)[0]
                img = next((img for img in all_files if img.startswith(base) and allowed_file(img, ALLOWED_IMG_EXTENSIONS)), None)
                books.append({'file': f, 'image': img})
        categorized_files[category] = books
    return render_template("Book.html", files=categorized_files, is_admin=session.get('admin') == True, query=query)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin'] = True
            flash('✅ Logged in as admin')
            return redirect('/')
        else:
            flash('❌ Incorrect password')
            return redirect('/admin')
    return render_template("admin_login.html")

@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash("Logged out successfully")
    return redirect('/')

@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('admin'):
        flash('Unauthorized')
        return redirect('/admin')
    
    doc = request.files.get('book')
    img = request.files.get('cover')
    category = request.form.get('category')

    if category not in CATEGORIES:
        flash("Invalid category")
        return redirect('/')
    
    if doc and allowed_file(doc.filename, ALLOWED_DOC_EXTENSIONS):
        docname = doc.filename
        docpath = os.path.join(BASE_FOLDER, category, docname)
        doc.save(docpath)

        if img and allowed_file(img.filename, ALLOWED_IMG_EXTENSIONS):
            ext = os.path.splitext(img.filename)[1]
            imgname = os.path.splitext(docname)[0] + ext
            img.save(os.path.join(BASE_FOLDER, category, imgname))

        flash('✅ Book and cover uploaded!')
    else:
        flash('❌ Invalid book file')
    
    return redirect('/')

@app.route('/uploads/<category>/<filename>')
def download_file(category, filename):
    if category not in CATEGORIES:
        return "Invalid category", 404
    return send_from_directory(os.path.join(BASE_FOLDER, category), filename)

if __name__ == '__main__':
    app.run(debug=True)
