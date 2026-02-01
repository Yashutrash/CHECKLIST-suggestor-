from flask import Flask, request, jsonify, g, send_file
from suggestion_engine import SuggestionEngine
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import pandas as pd
import io
import os

app = Flask(__name__)
CORS(app)
engine = SuggestionEngine()
app.config['SECRET_KEY'] = 'supersecretkey'  
DATABASE = 'users.db'

# --- User Auth Helpers ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )''')
        
        # Create table for accepted suggestions
        db.execute('''CREATE TABLE IF NOT EXISTS accepted_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT,
            confidence REAL,
            inspection_type TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Create table for AI-generated issues
        db.execute('''CREATE TABLE IF NOT EXISTS ai_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_title TEXT NOT NULL,
            issue_description TEXT,
            checklist_item TEXT,
            inspection_type TEXT,
            severity TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- JWT Decorator ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[-1]
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            g.current_user = data
        except Exception as e:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not hasattr(g, 'current_user') or g.current_user.get('role') != role:
                return jsonify({'message': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

# --- Auth Endpoints ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'inspector')
    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400
    db = get_db()
    try:
        db.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                   (username, generate_password_hash(password), role))
        db.commit()
        return jsonify({'message': 'User registered successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Username already exists'}), 409

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user and check_password_hash(user[2], password):
        token = jwt.encode({
            'username': user[1],
            'role': user[3],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token, 'role': user[3]})
    return jsonify({'message': 'Invalid credentials'}), 401

# --- Accepted Suggestions Endpoints ---
@app.route('/api/accepted-suggestions', methods=['GET'])
@token_required
def get_accepted_suggestions():
    db = get_db()
    suggestions = db.execute('''
        SELECT item, action, reason, confidence, inspection_type, created_by, created_at 
        FROM accepted_suggestions 
        ORDER BY created_at DESC
    ''').fetchall()
    
    return jsonify({
        'accepted_suggestions': [
            {
                'item': row[0],
                'action': row[1],
                'reason': row[2],
                'confidence': row[3],
                'inspection_type': row[4],
                'created_by': row[5],
                'created_at': row[6]
            }
            for row in suggestions
        ]
    })

@app.route('/api/accept-suggestion', methods=['POST'])
@token_required
@role_required('manager')
def accept_suggestion():
    data = request.get_json()
    item = data.get('item')
    action = data.get('action')
    reason = data.get('reason')
    confidence = data.get('confidence')
    inspection_type = data.get('inspection_type')
    
    if not item:
        return jsonify({'message': 'Suggestion item is required'}), 400
    
    db = get_db()
    db.execute('''
        INSERT INTO accepted_suggestions (item, action, reason, confidence, inspection_type, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (item, action, reason, confidence, inspection_type, g.current_user['username']))
    db.commit()
    
    return jsonify({'message': 'Suggestion accepted successfully'})

# --- AI Issue Generation Endpoints ---
@app.route('/api/generate-issues', methods=['POST'])
@token_required
@role_required('manager')
def generate_issues():
    data = request.get_json()
    checklist_items = data.get('checklist_items', [])
    inspection_type = data.get('inspection_type')
    
    if not inspection_type:
        return jsonify({'message': 'Inspection type is required'}), 400
    
    # Generate AI issues based on checklist items and inspection type
    issues = engine.generate_issues_from_checklist(checklist_items, inspection_type)
    
    # Store generated issues in database
    db = get_db()
    for issue in issues:
        db.execute('''
            INSERT INTO ai_issues (issue_title, issue_description, checklist_item, inspection_type, severity, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            issue['title'],
            issue['description'],
            issue.get('checklist_item', ''),
            inspection_type,
            issue.get('severity', 'medium'),
            issue.get('confidence', 0.7)
        ))
    db.commit()
    
    return jsonify({
        'issues': issues,
        'message': f'Generated {len(issues)} new issues based on checklist items and inspection type'
    })

@app.route('/api/ai-issues', methods=['GET'])
@token_required
def get_ai_issues():
    inspection_type = request.args.get('inspection_type')
    db = get_db()
    
    if inspection_type:
        issues = db.execute('''
            SELECT issue_title, issue_description, checklist_item, inspection_type, severity, confidence, created_at
            FROM ai_issues 
            WHERE inspection_type = ?
            ORDER BY created_at DESC
        ''', (inspection_type,)).fetchall()
    else:
        issues = db.execute('''
            SELECT issue_title, issue_description, checklist_item, inspection_type, severity, confidence, created_at
            FROM ai_issues 
            ORDER BY created_at DESC
        ''').fetchall()
    
    return jsonify({
        'ai_issues': [
            {
                'title': row[0],
                'description': row[1],
                'checklist_item': row[2],
                'inspection_type': row[3],
                'severity': row[4],
                'confidence': row[5],
                'created_at': row[6]
            }
            for row in issues
        ]
    })

# --- Example Protected Endpoint ---
@app.route('/api/manager-only', methods=['GET'])
@token_required
@role_required('manager')
def manager_only():
    return jsonify({'message': f"Hello, manager {g.current_user['username']}!"})

# --- Existing Endpoints (unchanged) ---
@app.route('/api/suggest-checklist', methods=['POST'])
def suggest_checklist():
    data = request.get_json()
    inspection_type = data.get('inspection_type')
    current_template_items = data.get('current_template_items', [])
    if not inspection_type:
        return jsonify({'error': 'inspection_type is required'}), 400
    suggestions = engine.get_suggestions(inspection_type, current_template_items)
    return jsonify({
        'inspection_type': inspection_type,
        'current_template_items': current_template_items,
        'suggestions': suggestions,
        'explanation': 'Suggestions are generated using advanced pattern recognition, clustering, and association rule mining on historical inspection data.'
    })

@app.route('/api/item-trends', methods=['GET'])
def item_trends():
    checklist_item_text = request.args.get('checklist_item_text')
    if not checklist_item_text:
        return jsonify({'error': 'checklist_item_text is required'}), 400
    trends = engine.get_item_trends(checklist_item_text)
    return jsonify({'item': checklist_item_text, 'trends': trends})

@app.route('/api/common-issues', methods=['GET'])
def common_issues():
    inspection_type = request.args.get('inspection_type')
    if not inspection_type:
        return jsonify({'error': 'inspection_type is required'}), 400
    issues = engine.get_common_issues(inspection_type)
    return jsonify({'inspection_type': inspection_type, 'common_issues': issues})

UPLOAD_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- CSV/Excel Upload Endpoint ---
@app.route('/api/upload-inspection-data', methods=['POST'])
@token_required
@role_required('manager')
def upload_inspection_data():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'mock_inspection_data.' + ext)
        file.save(filepath)
        # Optionally, convert Excel to CSV for backend use
        if ext == 'xlsx':
            df = pd.read_excel(filepath)
            df.to_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'mock_inspection_data.csv'), index=False)
        # Reload suggestion engine with new data
        engine.df = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'mock_inspection_data.csv'))
        return jsonify({'message': 'File uploaded and data updated successfully'})
    return jsonify({'message': 'Invalid file type'}), 400

# --- Export Suggestions as CSV ---
@app.route('/api/export-suggestions', methods=['POST'])
@token_required
@role_required('manager')
def export_suggestions():
    data = request.get_json()
    inspection_type = data.get('inspection_type')
    current_template_items = data.get('current_template_items', [])
    suggestions = engine.get_suggestions(inspection_type, current_template_items)
    df = pd.DataFrame(suggestions)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='suggestions.csv'
    )

# --- Analytics: Pass/Fail Trends Over Time ---
@app.route('/api/analytics/pass-fail-trends', methods=['GET'])
@token_required
@role_required('manager')
def pass_fail_trends():
    inspection_type = request.args.get('inspection_type')
    if not inspection_type:
        return jsonify({'error': 'inspection_type is required'}), 400
    trends = engine.get_pass_fail_trends(inspection_type)
    return jsonify({'inspection_type': inspection_type, 'trends': trends})

# --- Analytics: Top Failing Items ---
@app.route('/api/analytics/top-failing-items', methods=['GET'])
@token_required
@role_required('manager')
def top_failing_items():
    inspection_type = request.args.get('inspection_type')
    if not inspection_type:
        return jsonify({'error': 'inspection_type is required'}), 400
    items = engine.get_top_failing_items(inspection_type)
    return jsonify({'inspection_type': inspection_type, 'top_failing_items': items})

# --- Health Check Endpoint ---
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.utcnow().isoformat()})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000) 