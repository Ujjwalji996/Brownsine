from flask import Flask, request, redirect, url_for, render_template, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
ALLOWED_EXT = set(['jpg','jpeg','png','gif','webp','mp4','mov','avi','webm','txt','pdf','zip','html','htm'])

app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

def file_type(filename):
    ext = filename.rsplit('.',1)[-1].lower() if '.' in filename else ''
    if ext in ['jpg','jpeg','png','gif','webp']:
        return 'image'
    if ext in ['mp4','mov','avi','webm']:
        return 'video'
    if ext in ['html','htm']:
        return 'html'
    if ext in ['txt']:
        return 'text'
    return 'doc'

def target_subfolder(fname):
    t = file_type(fname)
    if t == 'image': return 'images'
    if t == 'video': return 'videos'
    if t == 'html': return 'html'
    if t == 'text': return 'text'
    return 'docs'

@app.route('/')
def index():
    files = []
    for sub in os.listdir(STORAGE_DIR):
        subpath = os.path.join(STORAGE_DIR, sub)
        if not os.path.isdir(subpath): continue
        for fname in os.listdir(subpath):
            path = os.path.join(subpath, fname)
            stat = os.stat(path)
            files.append({
                "name": fname,
                "size": int(stat.st_size/1024),
                "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "type": file_type(fname),
                "subfolder": sub
            })
    files = sorted(files, key=lambda x: x['date'], reverse=True)
    return render_template('index_v2.html', files=files)

@app.route('/storage/<sub>/<path:filename>')
def storage_file(sub, filename):
    return send_from_directory(os.path.join(STORAGE_DIR, sub), filename)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    files = request.files.getlist('file')
    for f in files:
        if f.filename == '': 
            continue
        filename = secure_filename(f.filename)
        sub = target_subfolder(filename)
        save_dir = os.path.join(STORAGE_DIR, sub)
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        # avoid overwrite by suffix
        base, ext = os.path.splitext(filename)
        i = 1
        while os.path.exists(save_path):
            filename = f"{base}({i}){ext}"
            save_path = os.path.join(save_dir, filename)
            i += 1
        f.save(save_path)
    return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete_files():
    data = request.get_json()
    files = data.get("files", [])
    for item in files:
        sub = item.get('sub')
        name = item.get('name')
        path = os.path.join(STORAGE_DIR, sub, name)
        if os.path.exists(path):
            os.remove(path)
    return jsonify({"status": "ok"})

@app.route('/rename', methods=['POST'])
def rename_file():
    data = request.get_json()
    old = data.get("old_name")
    new = data.get("new_name")
    sub = data.get("sub")
    if not old or not new or not sub:
        return jsonify({"status":"error","msg":"missing names"}), 400
    old_path = os.path.join(STORAGE_DIR, sub, old)
    new_secure = secure_filename(new)
    new_sub = target_subfolder(new_secure)
    new_dir = os.path.join(STORAGE_DIR, new_sub)
    os.makedirs(new_dir, exist_ok=True)
    new_path = os.path.join(new_dir, new_secure)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        return jsonify({"status":"ok","new_sub":new_sub})
    return jsonify({"status":"error","msg":"old file not found"}), 404

if __name__ == '__main__':
    os.makedirs(STORAGE_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)