import os
import uuid
import json
import random
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import base64

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
UPLOAD_FOLDER = 'static/pfp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure directories exist
os.makedirs('data', exist_ok=True)
os.makedirs('data/private_msgs', exist_ok=True)
os.makedirs('static/pfp', exist_ok=True)

# Initialize data files
def init_data_files():
    data_files = {
        'users.json': {'users': []},
        'msgs.json': {'messages': []}
    }
    for filename, default_data in data_files.items():
        if not os.path.exists(f'data/{filename}'):
            with open(f'data/{filename}', 'w') as f:
                json.dump(default_data, f)

init_data_files()

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_by_email(email):
    with open('data/users.json', 'r') as f:
        users_data = json.load(f)
    return next((user for user in users_data['users'] if user['email'] == email), None)

def get_user_by_username(username):
    with open('data/users.json', 'r') as f:
        users_data = json.load(f)
    return next((user for user in users_data['users'] if user['username'] == username), None)

def save_user(user):
    with open('data/users.json', 'r+') as f:
        users_data = json.load(f)
        users_data['users'].append(user)
        f.seek(0)
        json.dump(users_data, f, indent=2)

def update_user(original_email, updated_user):
    with open('data/users.json', 'r+') as f:
        users_data = json.load(f)
        users_data['users'] = [u if u['email'] != original_email else updated_user for u in users_data['users']]
        f.seek(0)
        json.dump(users_data, f, indent=2)

def get_public_messages():
    with open('data/msgs.json', 'r') as f:
        return json.load(f)['messages']

def add_public_message(message):
    with open('data/msgs.json', 'r+') as f:
        data = json.load(f)
        data['messages'].append(message)
        f.seek(0)
        json.dump(data, f, indent=2)

def get_private_messages(user1, user2):
    participants = sorted([user1, user2])
    filename = f"data/private_msgs/{participants[0]}-{participants[1]}.json"
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)['messages']
    return []

def add_private_message(user1, user2, message):
    participants = sorted([user1, user2])
    filename = f"data/private_msgs/{participants[0]}-{participants[1]}.json"
    if os.path.exists(filename):
        with open(filename, 'r+') as f:
            data = json.load(f)
            data['messages'].append(message)
            f.seek(0)
            json.dump(data, f, indent=2)
    else:
        with open(filename, 'w') as f:
            json.dump({
                'participants': participants,
                'messages': [message]
            }, f, indent=2)

def format_time(timestamp):
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%I:%M %p").lower().replace(" 0", " ")
    except:
        return timestamp

def format_message(text):
    return (text.replace('**', '<strong>', 1)
             .replace('**', '</strong>', 1)
             .replace('*', '<em>', 1)
             .replace('*', '</em>', 1))

def generate_avatar(username, size=100):
    random.seed(username)
    color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)
    img = Image.new('RGB', (size, size), color)
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", size//2)
    except:
        font = ImageFont.load_default()
    
    letter = username[0].upper() if username else "?"
    text_width, text_height = draw.textsize(letter, font=font)
    draw.text(
        ((size - text_width) / 2, (size - text_height) / 2),
        letter,
        font=font,
        fill=(255, 255, 255))
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

def get_avatar_url(user):
    if 'profile' in user and 'avatar' in user['profile'] and user['profile']['avatar']:
        return user['profile']['avatar']
    return generate_avatar(user['username'])

def get_user_color(username):
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', 
              '#98D8C8', '#F06292', '#7986CB', '#9575CD']
    return colors[ord(username[0]) % len(colors)] if username else '#CCCCCC'

# HTML Template
def base_html(content):
    dark_mode = session.get('dark_mode', False)
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CHAT SITE</title>
    <style>
        /* All CSS styles from previous example */
        :root {{
            --bg-color: #ffffff;
            --text-color: #000000;
            --msg-bubble: #f1f1f1;
            --header-bg: #4a76a8;
            --header-text: #ffffff;
            --input-bg: #f9f9f9;
            --input-border: #ddd;
            --button-bg: #4a76a8;
            --button-text: #ffffff;
            --button-hover: #3a5f8a;
            --link-color: #4a76a8;
            --error-color: #ff3333;
            --separator-color: #eee;
        }}

        .dark-mode {{
            --bg-color: #1a1a1a;
            --text-color: #ffffff;
            --msg-bubble: #333333;
            --header-bg: #2c3e50;
            --input-bg: #2d2d2d;
            --input-border: #444;
            --button-bg: #2c3e50;
            --button-hover: #1a2636;
            --link-color: #4a90e2;
            --separator-color: #444;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-color);
            transition: all 0.3s ease;
        }}

        .header {{
            background-color: var(--header-bg);
            color: var(--header-text);
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}

        /* ... (rest of CSS styles) ... */

        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            object-fit: cover;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 20px;
        }}
        
        .profile-header .avatar {{
            width: 100px;
            height: 100px;
            font-size: 50px;
        }}
    </style>
</head>
<body class="{'dark-mode' if dark_mode else ''}">
    <div class="header">
        <h1>CHAT SITE</h1>
        <div class="nav-icons">
            <a href="/" title="Home">🏠</a>
            <a href="/settings" title="Settings">⚙️</a>
            <a href="/info" title="Info">ℹ️</a>
            {'<a href="/logout" title="Logout">🚪</a>' if 'email' in session else '<a href="/login" title="Login">🔑</a>'}
        </div>
    </div>
    <div class="container">
        {content}
    </div>
    <script>
        // Dark mode toggle
        document.addEventListener('DOMContentLoaded', function() {{
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {{
                themeToggle.addEventListener('change', function() {{
                    document.body.classList.toggle('dark-mode');
                    fetch('/toggle-theme', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{dark_mode: this.checked}})
                    }});
                }});
            }}
            
            // Message sending
            window.sendMessage = function() {{
                const input = document.getElementById('message-input');
                const message = input.value.trim();
                if (!message) return;
                
                fetch('/send-message', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ content: message }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.status === 'success') {{
                        const messagesDiv = document.getElementById('messages');
                        const newMsg = document.createElement('div');
                        newMsg.className = 'message-container';
                        newMsg.innerHTML = `
                            <div class="message-header">
                                <div class="avatar" style="background-color: ${{getUserColor(data.message.author)}}">
                                    ${{data.message.author[0].toUpperCase()}}
                                </div>
                                <span>${{data.message.author}}</span>
                            </div>
                            <div class="message-content">${{data.message.content}}</div>
                            <div class="message-time">${{data.message.timestamp}}</div>
                        `;
                        messagesDiv.appendChild(newMsg);
                        input.value = '';
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }}
                }});
            }};
            
            function getUserColor(username) {{
                const colors = [
                    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
                    '#98D8C8', '#F06292', '#7986CB', '#9575CD'
                ];
                const index = username.charCodeAt(0) % colors.length;
                return colors[index];
            }}
        }});
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def index():
    if 'email' not in session:
        return redirect('/login')
    
    current_user = get_user_by_email(session['email'])
    if not current_user:
        session.clear()
        return redirect('/login')
    
    messages = get_public_messages()
    for message in messages:
        user = get_user_by_email(message['author'])
        message['author'] = user['username'] if user else 'Unknown'
        message['content'] = format_message(message['content'])
        message['timestamp'] = format_time(message['timestamp'])
    
    with open('data/users.json', 'r') as f:
        users = json.load(f)['users']
    
    content = f"""
    <div class="chat-container">
        <div class="sidebar">
            <h3>Online Users</h3>
            <ul class="user-list">
                {' '.join(f'''
                <li class="user-item">
                    <div class="avatar" style="background-color: {get_user_color(user['username'])}">
                        {user['username'][0].upper()}
                    </div>
                    <span class="user-name">{user['username']}</span>
                    <button class="start-chat" onclick="startPrivateChat('{user['email']}')">Chat</button>
                </li>
                ''' for user in users if user['email'] != session['email'])}
            </ul>
        </div>
        <div class="chat-area">
            <div class="messages" id="messages">
                {' '.join(f'''
                <div class="message-container">
                    <div class="message-header">
                        <div class="avatar" style="background-color: {get_user_color(msg['author'])}">
                            {msg['author'][0].upper()}
                        </div>
                        <span>{msg['author']}</span>
                    </div>
                    <div class="message-content">{msg['content']}</div>
                    <div class="message-time">{msg['timestamp']}</div>
                </div>
                ''' for msg in messages)}
            </div>
            <div class="input-area">
                <textarea class="message-input" id="message-input" placeholder="Type your message..."></textarea>
                <button class="send-button" onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>
    """
    return render_template_string(base_html(content))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect('/')
    
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = get_user_by_email(email)
        if not user or user['password'] != password:
            error = "Invalid email or password"
        else:
            session['email'] = email
            session['username'] = user['username']
            session['dark_mode'] = user['settings']['dark_mode']
            return redirect('/')
    
    content = f"""
    <div class="login-container">
        <h2>Login</h2>
        <form action="/login" method="POST">
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            {'<div class="error-message">' + error + '</div>' if error else ''}
            <button type="submit" class="form-submit">Login</button>
        </form>
        <div class="form-footer">
            Don't have an account? <a href="/register">Register</a>
        </div>
    </div>
    """
    return render_template_string(base_html(content))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'email' in session:
        return redirect('/')
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        profile_pic = request.files.get('profile_pic')
        
        if get_user_by_email(email):
            error = "Email already registered"
        elif get_user_by_username(username):
            error = "Username already taken"
        else:
            avatar_path = None
            if profile_pic and profile_pic.filename:
                if profile_pic.content_length > MAX_FILE_SIZE:
                    error = "File too large (max 2MB)"
                elif not allowed_file(profile_pic.filename):
                    error = "Invalid file type (only JPG, PNG, GIF allowed)"
                else:
                    filename = secure_filename(f"{username}.{profile_pic.filename.rsplit('.', 1)[1].lower()}")
                    profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    avatar_path = f"/pfp/{filename}"
            
            if not error:
                new_user = {
                    'id': str(uuid.uuid4()),
                    'username': username,
                    'email': email,
                    'password': password,
                    'profile': {
                        'avatar': avatar_path,
                        'joined_at': datetime.now().isoformat()
                    },
                    'settings': {
                        'dark_mode': False
                    }
                }
                save_user(new_user)
                session['email'] = email
                session['username'] = username
                return redirect('/')
    
    content = f"""
    <div class="register-container">
        <h2>Register</h2>
        <form action="/register" method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <div class="form-group">
                <label for="profile_pic">Profile Picture (optional)</label>
                <input type="file" id="profile_pic" name="profile_pic" accept="image/*">
            </div>
            {'<div class="error-message">' + error + '</div>' if error else ''}
            <button type="submit" class="form-submit">Register</button>
        </form>
        <div class="form-footer">
            Already have an account? <a href="/login">Login</a>
        </div>
    </div>
    """
    return render_template_string(base_html(content))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/settings')
def settings():
    if 'email' not in session:
        return redirect('/login')
    
    current_user = get_user_by_email(session['email'])
    if not current_user:
        session.clear()
        return redirect('/login')
    
    avatar_style = f"background-color: {get_user_color(current_user['username'])}"
    avatar_letter = current_user['username'][0].upper() if current_user['username'] else '?'
    
    content = f"""
    <div class="profile-container">
        <div class="profile-header">
            <div class="avatar" style="{avatar_style}">{avatar_letter}</div>
            <div>
                <h2 class="profile-username">{current_user['username']}</h2>
                <p class="profile-email">{current_user['email']}</p>
            </div>
        </div>
        <form class="settings-form" action="/update-profile" method="POST" enctype="multipart/form-data">
            <div class="settings-option">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" value="{current_user['username']}" required>
            </div>
            <div class="settings-option">
                <label for="profile_pic">Profile Picture</label>
                <input type="file" id="profile_pic" name="profile_pic" accept="image/*">
            </div>
            <div class="settings-option theme-toggle">
                <label>Dark Mode</label>
                <label class="switch">
                    <input type="checkbox" id="theme-toggle" {'checked' if session.get('dark_mode', False) else ''}>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="settings-actions">
                <button type="submit" class="form-submit">Save Changes</button>
            </div>
        </form>
    </div>
    """
    return render_template_string(base_html(content))

@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'email' not in session:
        return redirect('/login')
    
    current_email = session['email']
    current_user = get_user_by_email(current_email)
    if not current_user:
        session.clear()
        return redirect('/login')
    
    username = request.form.get('username')
    profile_pic = request.files.get('profile_pic')
    
    # Check if username is taken by another user
    existing_user = get_user_by_username(username)
    if existing_user and existing_user['email'] != current_email:
        return "Username already taken", 400
    
    # Handle profile picture upload
    avatar_path = current_user['profile']['avatar']
    if profile_pic and profile_pic.filename:
        if profile_pic.content_length > MAX_FILE_SIZE:
            return "File too large (max 2MB)", 400
        if not allowed_file(profile_pic.filename):
            return "Invalid file type (only JPG, PNG, GIF allowed)", 400
        
        # Delete old profile picture if it exists
        if avatar_path and os.path.exists(avatar_path.lstrip('/')):
            os.remove(avatar_path.lstrip('/'))
        
        filename = secure_filename(f"{username}.{profile_pic.filename.rsplit('.', 1)[1].lower()}")
        profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        avatar_path = f"/pfp/{filename}"
    
    # Update user data
    updated_user = {
        **current_user,
        'username': username,
        'profile': {
            **current_user['profile'],
            'avatar': avatar_path
        }
    }
    
    update_user(current_email, updated_user)
    session['username'] = username
    return redirect('/settings')

@app.route('/toggle-theme', methods=['POST'])
def toggle_theme():
    if 'email' not in session:
        return jsonify({'status': 'error'}), 401
    
    data = request.get_json()
    dark_mode = data.get('dark_mode', False)
    session['dark_mode'] = dark_mode
    
    # Update user preference
    user = get_user_by_email(session['email'])
    if user:
        user['settings']['dark_mode'] = dark_mode
        update_user(session['email'], user)
    
    return jsonify({'status': 'success'})

@app.route('/info')
def info():
    if 'email' not in session:
        return redirect('/login')
    
    content = """
    <div class="info-container">
        <h2>About CHAT SITE</h2>
        <p>Welcome to CHAT SITE, a simple chat application built with Flask.</p>
        
        <h3>Features</h3>
        <ul>
            <li>Public chat room for all users</li>
            <li>Private messaging between users</li>
            <li>User profiles with dynamic avatars</li>
            <li>Light/dark mode toggle</li>
            <li>Basic text formatting (bold, italic)</li>
        </ul>
        
        <h3>How to Use</h3>
        <p>1. Register an account or login if you already have one</p>
        <p>2. Join the public chat or start a private conversation</p>
        <p>3. Customize your profile in the settings</p>
        
        <h3>Technical Details</h3>
        <p>This application is built with:</p>
        <ul>
            <li>Python Flask backend</li>
            <li>Vanilla HTML/CSS/JavaScript frontend</li>
            <li>JSON-based data storage</li>
            <li>Dynamic avatar generation</li>
        </ul>
    </div>
    """
    return render_template_string(base_html(content))

@app.route('/pfp/<filename>')
def serve_pfp(filename):
    return send_from_directory('static/pfp', filename)

@app.route('/send-message', methods=['POST'])
def send_message():
    if 'email' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    content = data.get('content')
    is_private = data.get('is_private', False)
    recipient = data.get('recipient')
    
    if not content:
        return jsonify({'status': 'error', 'message': 'Message content required'}), 400
    
    user = get_user_by_email(session['email'])
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    message = {
        'id': str(uuid.uuid4()),
        'author': session['email'],
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'edited': False
    }
    
    if is_private and recipient:
        add_private_message(session['email'], recipient, message)
    else:
        add_public_message(message)
    
    return jsonify({
        'status': 'success',
        'message': {
            'author': user['username'],
            'content': format_message(content),
            'timestamp': format_time(message['timestamp'])
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
