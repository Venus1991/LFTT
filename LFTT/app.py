from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort, send_file
import os
from datetime import datetime
import zipfile
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def safe_join_paths(*paths):
    """安全地连接路径，确保结果在UPLOAD_FOLDER内"""
    joined_path = os.path.join(*paths)
    abs_path = os.path.abspath(joined_path)
    upload_path = os.path.abspath(UPLOAD_FOLDER)
    if not abs_path.startswith(upload_path):
        abort(403)
    return joined_path

def get_directory_structure(root_path, relative_path=''):
    """递归获取目录结构"""
    items = []
    full_path = os.path.join(root_path, relative_path)
    
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        rel_path = os.path.join(relative_path, item)
        is_dir = os.path.isdir(item_path)
        
        items.append({
            'name': item,
            'path': rel_path.replace('\\', '/'),
            'is_dir': is_dir,
            'modified': datetime.fromtimestamp(os.path.getmtime(item_path))
        })
    
    return sorted(items, key=lambda x: (-x['is_dir'], x['name']))

@app.route('/')
@app.route('/browse/<path:subpath>')
def index(subpath=''):
    current_path = os.path.join(app.config['UPLOAD_FOLDER'], subpath)
    if not os.path.exists(current_path):
        abort(404)
    
    items = get_directory_structure(app.config['UPLOAD_FOLDER'], subpath)
    return render_template('index.html', 
                        items=items,
                        current_path=subpath,
                        parent_path=os.path.dirname(subpath))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
        
    if file:
        # 获取当前路径
        current_path = request.form.get('current_path', '')
        # 安全处理文件名
        filename = secure_filename(file.filename)
        # 构建完整的保存路径
        save_path = safe_join_paths(app.config['UPLOAD_FOLDER'], current_path)
        # 确保目标目录存在
        os.makedirs(save_path, exist_ok=True)
        # 保存文件
        file.save(os.path.join(save_path, filename))
        
    if current_path:
        return redirect(url_for('index', subpath=current_path))
    return redirect(url_for('index'))

@app.route('/download/<path:filepath>')
def download_file(filepath):
    # 安全地构建文件路径
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], directory), filename)

@app.route('/download_folder/<path:folderpath>')
def download_folder(folderpath):
    # 安全地构建文件夹路径
    folder_path = safe_join_paths(app.config['UPLOAD_FOLDER'], folderpath)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        abort(404)
    
    # 创建临时zip文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        zip_path = temp_file.name
        
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"{os.path.basename(folderpath)}.zip"
        )
    finally:
        # 确保临时文件被删除
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)