# -*- coding: utf-8 -*-
import os
import json
import requests
import secrets
import time
from datetime import datetime, date, timedelta
from flask import Flask, render_template_string, request, session, redirect, jsonify, flash
from functools import wraps
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ===== CONSTANTS =====
ADMIN_PASSWORD_FILE = "/tmp/admin_password.json"
KEYS_FILE = "/tmp/api_keys.json"
SETTINGS_FILE = "/tmp/api_settings.json"
ANALYTICS_FILE = "/tmp/analytics.json"
BLACKLIST_FILE = "/tmp/blacklist.json"
RATE_LIMIT_FILE = "/tmp/rate_limits.json"
CUSTOM_APIS_FILE = "/tmp/custom_apis.json"
UI_SETTINGS_FILE = "/tmp/ui_settings.json"

SECRET_KEY = secrets.token_hex(32)
VERSION = "3.0.0"
MAX_KEYS_PER_USER = 100
API_NAME = "Xenon API Management System"

DEFAULT_SETTINGS = {
    "maintenance_mode": False,
    "allow_public_access": True,
    "rate_limit_per_minute": 60,
    "enable_logging": True,
    "cache_enabled": True,
    "cache_duration": 300,
    "blacklist_enabled": True,
    "auto_block_threshold": 50,
    "enable_credit": True,
    "credit_text": "@Xenon33cyber",
    "system_name": "Xenon API Management System",
    "system_short_name": "Xenon API",
    "footer_text": "Developed by @Xenon33cyber",
    "primary_color": "#00ff41",
    "secondary_color": "#00aa33",
    "bg_color": "#0a0a0a"
}

DEFAULT_UI = {
    "logo_text": "XENON",
    "logo_icon": "fa-skull",
    "header_title": "Xenon API Management System",
    "header_subtitle": "Premium API Management Platform",
    "dashboard_title": "Control Panel",
    "stats_labels": {
        "keys": "Total API Keys",
        "requests": "Total Requests",
        "daily": "Today's Requests",
        "custom": "Custom APIs"
    },
    "key_gen_title": "Generate New API Key",
    "key_gen_name_placeholder": "e.g., premium_user",
    "key_gen_limit_placeholder": "0 = Unlimited",
    "key_gen_type_label": "API Type",
    "key_gen_submit_text": "Create API Key",
    "custom_api_title": "Add Custom API",
    "custom_api_name_placeholder": "e.g., number, telegram",
    "custom_api_url_placeholder": "https://api.example.com?query=",
    "custom_api_add_text": "Add API",
    "keys_table_title": "Active API Keys",
    "keys_table_headers": ["Key Name", "Type", "Usage", "Expiry", "Status", "Live Endpoint", "Actions"],
    "settings_title": "Advanced Settings",
    "settings_system_title": "System Configuration",
    "settings_analytics_title": "Analytics & Logs",
    "footer_credit": "Powered by @Xenon33cyber",
    "toast_copied": "URL copied to clipboard! ✅",
    "toast_error": "Failed to copy. Please select and copy manually.",
    "login_title": "⚡ XENON API MANAGEMENT",
    "login_subtitle": "Secure & Encrypted Access",
    "login_placeholder": "> Enter Master Password_",
    "login_button_text": "Access Core",
    "login_forgot_text": "Forgot Access?",
    "login_credit_text": "🔐 Secured by @Xenon33cyber",
    "glitch_effect": True,
    "matrix_rain": True,
    "typing_animation": True,
    "hacker_style": True
}

app.secret_key = SECRET_KEY

# ===== HELPERS =====
def load_data(filepath, default_data):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except:
        pass
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    save_data(filepath, default_data)
    return default_data

def save_data(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def get_admin_password():
    data = load_data(ADMIN_PASSWORD_FILE, {"password": "admin"})
    return data.get("password", "admin")

def set_admin_password(new_password):
    save_data(ADMIN_PASSWORD_FILE, {"password": new_password, "last_changed": datetime.now().isoformat()})

def get_keys():
    data = load_data(KEYS_FILE, {})
    today_str = str(date.today())
    updated = False
    for k, v in data.items():
        if v.get('last_used_date') != today_str:
            v['used'] = 0
            v['last_used_date'] = today_str
            updated = True
    if updated:
        save_data(KEYS_FILE, data)
    return data

def get_analytics():
    return load_data(ANALYTICS_FILE, {
        "total_requests": 0,
        "daily_requests": {},
        "api_usage": {},
        "error_logs": [],
        "user_agents": {},
        "top_ips": {}
    })

def update_analytics(api_key, api_type, status, ip, user_agent):
    analytics = get_analytics()
    analytics["total_requests"] += 1
    today = str(date.today())
    if today not in analytics["daily_requests"]:
        analytics["daily_requests"][today] = 0
    analytics["daily_requests"][today] += 1
    if api_type not in analytics["api_usage"]:
        analytics["api_usage"][api_type] = 0
    analytics["api_usage"][api_type] += 1
    if user_agent:
        if user_agent not in analytics["user_agents"]:
            analytics["user_agents"][user_agent] = 0
        analytics["user_agents"][user_agent] += 1
    if ip:
        if ip not in analytics["top_ips"]:
            analytics["top_ips"][ip] = 0
        analytics["top_ips"][ip] += 1
    save_data(ANALYTICS_FILE, analytics)

def log_error(error_type, message, api_key=None, query=None):
    analytics = get_analytics()
    analytics["error_logs"].append({
        "timestamp": datetime.now().isoformat(),
        "type": error_type,
        "message": message,
        "api_key": api_key,
        "query": query
    })
    if len(analytics["error_logs"]) > 500:
        analytics["error_logs"] = analytics["error_logs"][-500:]
    save_data(ANALYTICS_FILE, analytics)

def get_blacklist():
    return load_data(BLACKLIST_FILE, {"ips": [], "keys": []})

def get_custom_apis():
    return load_data(CUSTOM_APIS_FILE, {})

def save_custom_api(api_name, api_url):
    custom_apis = get_custom_apis()
    custom_apis[api_name] = api_url
    save_data(CUSTOM_APIS_FILE, custom_apis)

def delete_custom_api(api_name):
    custom_apis = get_custom_apis()
    if api_name in custom_apis:
        del custom_apis[api_name]
        save_data(CUSTOM_APIS_FILE, custom_apis)
        return True
    return False

def get_ui_settings():
    ui = load_data(UI_SETTINGS_FILE, DEFAULT_UI)
    for key, value in DEFAULT_UI.items():
        if key not in ui:
            ui[key] = value
    return ui

def save_ui_settings(ui_data):
    save_data(UI_SETTINGS_FILE, ui_data)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r},{g},{b}"
    return "0,255,65"

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def rate_limit_check(ip):
    rate_limits = load_data(RATE_LIMIT_FILE, {})
    current_minute = int(time.time() / 60)
    if ip not in rate_limits:
        rate_limits[ip] = {"minute": current_minute, "count": 0}
    if rate_limits[ip]["minute"] != current_minute:
        rate_limits[ip] = {"minute": current_minute, "count": 0}
    rate_limits[ip]["count"] += 1
    save_data(RATE_LIMIT_FILE, rate_limits)
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    return rate_limits[ip]["count"] <= settings.get("rate_limit_per_minute", 60)

# ===== HTML TEMPLATES =====
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>XENON Login</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Courier New',monospace;background:{{settings.bg_color}};min-height:100vh;display:flex;align-items:center;justify-content:center;color:{{settings.primary_color}}}.glass{background:rgba(10,10,10,0.95);backdrop-filter:blur(20px);border:1px solid rgba({{rgb_primary}},0.2);border-radius:20px;padding:40px 30px;max-width:420px;width:100%}.logo-icon{text-align:center;font-size:56px;color:{{settings.primary_color}};margin-bottom:10px}.login-title{text-align:center;font-size:24px;font-weight:800;color:{{settings.primary_color}};letter-spacing:2px;margin-bottom:6px}.login-subtitle{text-align:center;color:{{settings.secondary_color}};font-size:13px;letter-spacing:4px;margin-bottom:30px}.form-group{margin-bottom:18px}.form-control{width:100%;padding:12px 16px;background:rgba({{rgb_primary}},0.03);border:1px solid rgba({{rgb_primary}},0.12);border-radius:10px;color:{{settings.primary_color}};font-size:14px;font-family:'Courier New',monospace}.form-control:focus{outline:none;border-color:{{settings.primary_color}}}.btn{width:100%;padding:14px;border:1px solid {{settings.primary_color}};border-radius:10px;background:rgba({{rgb_primary}},0.05);color:{{settings.primary_color}};font-weight:700;cursor:pointer;font-family:'Courier New',monospace;font-size:14px;letter-spacing:3px;text-transform:uppercase}.btn:hover{background:{{settings.primary_color}};color:{{settings.bg_color}}}.alert{padding:10px 14px;border-radius:8px;margin-bottom:15px;font-size:12px}.alert-danger{background:rgba(255,0,0,0.08);color:#ff4444;border-color:rgba(255,0,0,0.15)}
</style>
</head>
<body>
<div class="glass">
<div class="logo-icon"><i class="fas {{ui.logo_icon}}"></i></div>
<div class="login-title">{{ui.login_title}}</div>
<div class="login-subtitle">{{ui.login_subtitle}}</div>
{% with messages=get_flashed_messages(with_categories=true) %}
{% if messages %}{% for category,message in messages %}
<div class="alert alert-{{category}}">{{message}}</div>
{% endfor %}{% endif %}{% endwith %}
<form method="POST">
<div class="form-group"><input type="password" name="password" class="form-control" placeholder="{{ui.login_placeholder}}" required autofocus></div>
<button type="submit" class="btn"><i class="fas fa-unlock-alt"></i> {{ui.login_button_text}}</button>
</form>
</div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head><title>XENON Dashboard</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Courier New',monospace;background:{{settings.bg_color}};color:{{settings.primary_color}}}.container{max-width:1400px;margin:0 auto;padding:15px}.glass{background:rgba(10,10,10,0.95);border:1px solid rgba({{rgb_primary}},0.12);border-radius:16px;padding:20px;margin-bottom:20px}.header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;padding:15px 20px}.logo{display:flex;align-items:center;gap:12px}.logo i{font-size:30px;color:{{settings.primary_color}}}.logo h1{font-size:22px;color:{{settings.primary_color}}}.btn{padding:8px 16px;border:1px solid {{settings.primary_color}};border-radius:8px;background:transparent;color:{{settings.primary_color}};cursor:pointer;font-family:'Courier New',monospace;text-decoration:none;display:inline-flex;align-items:center;gap:6px}.btn:hover{background:{{settings.primary_color}};color:{{settings.bg_color}}}.btn-danger{border-color:#ff4444;color:#ff4444}.btn-danger:hover{background:#ff4444;color:#fff}.btn-warning{border-color:#ffa500;color:#ffa500}.btn-warning:hover{background:#ffa500;color:#000}.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px}.stat-card{background:rgba(10,10,10,0.95);padding:15px;border-radius:12px;border:1px solid rgba({{rgb_primary}},0.08);text-align:center}.stat-number{font-size:24px;font-weight:700;color:{{settings.primary_color}}}.stat-label{font-size:11px;color:{{settings.secondary_color}};text-transform:uppercase}.form-group{margin-bottom:15px}.form-control{width:100%;padding:10px 14px;background:rgba({{rgb_primary}},0.03);border:1px solid rgba({{rgb_primary}},0.12);border-radius:8px;color:{{settings.primary_color}};font-family:'Courier New',monospace}.table-container{overflow-x:auto}table{width:100%;border-collapse:collapse}th{background:rgba({{rgb_primary}},0.04);padding:10px 12px;text-align:left;font-size:10px;text-transform:uppercase;color:{{settings.secondary_color}}}td{padding:10px 12px;border-bottom:1px solid rgba({{rgb_primary}},0.04);font-size:12px}.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:10px;font-weight:600}.badge-active{background:rgba({{rgb_primary}},0.12);color:{{settings.primary_color}}}.badge-expired{background:rgba(255,0,0,0.08);color:#ff4444}.flex{display:flex;gap:10px;flex-wrap:wrap}.flex-between{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap}.mt-20{margin-top:20px}.mb-20{margin-bottom:20px}.section-title{color:{{settings.primary_color}};font-size:18px;margin-bottom:15px}
</style>
</head>
<body>
<div class="container">
<div class="header glass">
<div class="logo"><i class="fas {{ui.logo_icon}}"></i><div><h1>{{ui.header_title}}</h1></div></div>
<div class="flex"><a href="/change_password" class="btn btn-warning"><i class="fas fa-key"></i> Change Password</a><a href="/logout" class="btn btn-danger"><i class="fas fa-sign-out-alt"></i> Logout</a></div>
</div>
{% with messages=get_flashed_messages(with_categories=true) %}
{% if messages %}{% for category,message in messages %}<div class="alert alert-{{category}}">{{message}}</div>{% endfor %}{% endif %}
{% endwith %}
<div class="stats-grid">
<div class="stat-card"><div class="stat-number">{{keys|length}}</div><div class="stat-label">Total Keys</div></div>
<div class="stat-card"><div class="stat-number">{{analytics.total_requests|default(0)}}</div><div class="stat-label">Total Requests</div></div>
<div class="stat-card"><div class="stat-number">{{analytics.daily_requests.get(today,0)|default(0)}}</div><div class="stat-label">Today's Requests</div></div>
<div class="stat-card"><div class="stat-number">{{custom_apis|length}}</div><div class="stat-label">Custom APIs</div></div>
</div>
<div class="glass"><h3 class="section-title"><i class="fas fa-plus-circle"></i> Generate Key</h3>
<form method="POST" action="/generate">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div class="form-group"><input type="text" name="key_name" class="form-control" placeholder="Key Name" required></div>
<div class="form-group"><input type="number" name="limit" class="form-control" placeholder="Daily Limit (0=unlimited)" required></div>
<div class="form-group"><input type="date" name="expiry" class="form-control" required></div>
<div class="form-group"><select name="type" class="form-control">{% for api_name in custom_apis.keys() %}<option value="{{api_name}}">{{api_name|upper}}</option>{% endfor %}</select></div>
</div>
<button type="submit" class="btn" style="width:100%;justify-content:center;height:48px"><i class="fas fa-key"></i> Create Key</button>
</form></div>
<div class="glass"><h3 class="section-title"><i class="fas fa-plug"></i> Add Custom API</h3>
<form method="POST" action="/add_custom_api">
<div style="display:grid;grid-template-columns:1fr 1fr auto;gap:10px">
<div class="form-group"><input type="text" name="api_name" class="form-control" placeholder="api_name" required></div>
<div class="form-group"><input type="url" name="api_url" class="form-control" placeholder="https://api.example.com?query=" required></div>
<button type="submit" class="btn"><i class="fas fa-plus"></i> Add</button>
</div>
</form>
{% for api_name,api_url in custom_apis.items() %}
<div style="display:flex;justify-content:space-between;padding:8px 12px;border-left:2px solid {{settings.primary_color}};margin-top:6px">
<span>{{api_name|upper}}</span><span style="font-size:11px;color:{{settings.secondary_color}}">{{api_url}}</span>
<form method="POST" action="/delete_custom_api"><input type="hidden" name="api_name" value="{{api_name}}"><button type="submit" class="btn btn-danger btn-sm">Delete</button></form>
</div>
{% endfor %}
</div>
<div class="glass"><h3 class="section-title"><i class="fas fa-database"></i> API Keys</h3>
<div class="table-container"><table>
<thead><tr><th>Name</th><th>Type</th><th>Usage</th><th>Expiry</th><th>Status</th><th>Actions</th></tr></thead>
<tbody>{% for k,v in keys.items() %}
<tr><td><strong>{{k}}</strong></td><td><span class="badge badge-active">{{v.api_type|upper}}</span></td><td>{{v.used}}/{% if v.limit==0 %}∞{% else %}{{v.limit}}{% endif %}</td><td>{{v.expiry_date}}</td><td>{% if v.expiry_date < today %}<span class="badge badge-expired">Expired</span>{% else %}<span class="badge badge-active">Active</span>{% endif %}</td>
<td class="flex"><form method="POST" action="/delete_key"><input type="hidden" name="key_name" value="{{k}}"><button type="submit" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></button></form><form method="POST" action="/reset_key"><input type="hidden" name="key_name" value="{{k}}"><button type="submit" class="btn btn-warning btn-sm"><i class="fas fa-undo"></i></button></form></td></tr>
{% endfor %}</tbody></table></div></div>
</div>
</body>
</html>
"""

CHANGE_PASSWORD_HTML = """
<!DOCTYPE html>
<html>
<head><title>Change Password</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Courier New',monospace;background:{{settings.bg_color}};color:{{settings.primary_color}};min-height:100vh;display:flex;align-items:center;justify-content:center}.container{max-width:400px;width:100%;padding:20px}.glass{background:rgba(10,10,10,0.95);border:1px solid rgba({{rgb_primary}},0.12);border-radius:16px;padding:30px}.form-group{margin-bottom:15px}.form-control{width:100%;padding:10px 14px;background:rgba({{rgb_primary}},0.03);border:1px solid rgba({{rgb_primary}},0.1);border-radius:8px;color:{{settings.primary_color}};font-family:'Courier New',monospace}.btn{padding:10px;border:1px solid {{settings.primary_color}};border-radius:8px;background:transparent;color:{{settings.primary_color}};cursor:pointer;font-family:'Courier New',monospace;width:100%}.btn:hover{background:{{settings.primary_color}};color:{{settings.bg_color}}}
</style>
</head>
<body>
<div class="container"><div class="glass"><h2 style="text-align:center;margin-bottom:20px">Change Password</h2>
<form method="POST">
<div class="form-group"><input type="password" name="current_password" class="form-control" placeholder="Current Password" required></div>
<div class="form-group"><input type="password" name="new_password" class="form-control" placeholder="New Password" required></div>
<div class="form-group"><input type="password" name="confirm_password" class="form-control" placeholder="Confirm Password" required></div>
<button type="submit" class="btn"><i class="fas fa-save"></i> Update</button>
</form>
<a href="/dashboard" style="display:block;text-align:center;margin-top:15px;color:{{settings.secondary_color}};text-decoration:none">← Back</a>
</div></div>
</body>
</html>
"""

# ===== ROUTES =====
@app.route('/')
def home():
    if session.get('admin'):
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    ui = get_ui_settings()
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    rgb_primary = hex_to_rgb(settings.get('primary_color', '#00ff41'))
    if request.method == 'POST':
        if request.form.get('password') == get_admin_password():
            session['admin'] = True
            return redirect('/dashboard')
        flash('Invalid password!', 'danger')
    return render_template_string(LOGIN_HTML, ui=ui, settings=settings, rgb_primary=rgb_primary, version=VERSION)

@app.route('/dashboard')
@admin_required
def dashboard():
    analytics = get_analytics()
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    custom_apis = get_custom_apis()
    ui = get_ui_settings()
    rgb_primary = hex_to_rgb(settings.get('primary_color', '#00ff41'))
    return render_template_string(DASHBOARD_HTML, keys=get_keys(), settings=settings, rgb_primary=rgb_primary,
                                   analytics=analytics, today=str(date.today()), custom_apis=custom_apis, ui=ui)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

@app.route('/change_password', methods=['GET', 'POST'])
@admin_required
def change_password():
    ui = get_ui_settings()
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    rgb_primary = hex_to_rgb(settings.get('primary_color', '#00ff41'))
    if request.method == 'POST':
        current = request.form.get('current_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        if current != get_admin_password():
            flash('Current password incorrect!', 'danger')
        elif not new or len(new) < 4:
            flash('Password must be at least 4 characters!', 'danger')
        elif new != confirm:
            flash('Passwords do not match!', 'danger')
        else:
            set_admin_password(new)
            flash('Password changed successfully!', 'success')
            return redirect('/dashboard')
    return render_template_string(CHANGE_PASSWORD_HTML, ui=ui, settings=settings, rgb_primary=rgb_primary)

@app.route('/generate', methods=['POST'])
@admin_required
def generate_web():
    keys = get_keys()
    key_name = request.form.get('key_name')
    if len(keys) >= MAX_KEYS_PER_USER:
        flash('Maximum keys limit reached!', 'danger')
        return redirect('/dashboard')
    keys[key_name] = {
        "limit": int(request.form.get('limit')),
        "used": 0,
        "expiry_date": request.form.get('expiry'),
        "api_type": request.form.get('type'),
        "last_used_date": str(date.today()),
        "created_at": datetime.now().isoformat()
    }
    save_data(KEYS_FILE, keys)
    flash(f'Key "{key_name}" created!', 'success')
    return redirect('/dashboard')

@app.route('/delete_key', methods=['POST'])
@admin_required
def delete_web():
    keys = get_keys()
    key_name = request.form.get('key_name')
    keys.pop(key_name, None)
    save_data(KEYS_FILE, keys)
    flash(f'Key "{key_name}" deleted!', 'warning')
    return redirect('/dashboard')

@app.route('/reset_key', methods=['POST'])
@admin_required
def reset_key():
    keys = get_keys()
    key_name = request.form.get('key_name')
    if key_name in keys:
        keys[key_name]['used'] = 0
        keys[key_name]['last_used_date'] = str(date.today())
        save_data(KEYS_FILE, keys)
        flash(f'Key "{key_name}" reset!', 'success')
    return redirect('/dashboard')

@app.route('/add_custom_api', methods=['POST'])
@admin_required
def add_custom_api():
    api_name = request.form.get('api_name', '').strip().lower()
    api_url = request.form.get('api_url', '').strip()
    if api_name and api_url:
        api_name = re.sub(r'[^a-zA-Z0-9_]', '', api_name)
        save_custom_api(api_name, api_url)
        flash(f'Custom API "{api_name}" added!', 'success')
    return redirect('/dashboard')

@app.route('/delete_custom_api', methods=['POST'])
@admin_required
def delete_custom_api_route():
    api_name = request.form.get('api_name')
    if api_name and delete_custom_api(api_name):
        flash(f'Custom API "{api_name}" deleted!', 'warning')
    return redirect('/dashboard')

# ===== API ENDPOINT =====
cache_store = {}

@app.route('/api/v1/info', methods=['GET', 'POST'])
def api_endpoint():
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    if settings.get('maintenance_mode', False):
        return jsonify({"error": "API under maintenance"}), 503
    
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if settings.get('blacklist_enabled', True):
        blacklist = get_blacklist()
        if client_ip in blacklist.get('ips', []):
            return jsonify({"error": "IP blocked"}), 403
    
    if not rate_limit_check(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    api_key = request.args.get('key')
    query = request.args.get('query')
    
    if not api_key or not query:
        return jsonify({"error": "Missing parameters! Use: ?key=KEY&query=DATA"}), 400
    
    keys = get_keys()
    custom_apis = get_custom_apis()
    
    if api_key not in keys:
        log_error("INVALID_KEY", f"Invalid key: {api_key}", api_key, query)
        return jsonify({"error": "Invalid API Key!"}), 401
    
    key_info = keys[api_key]
    
    if date.today() > datetime.strptime(key_info.get('expiry_date', '2099-12-31'), '%Y-%m-%d').date():
        return jsonify({"error": "API Key Expired!"}), 403
    
    if key_info['limit'] != 0 and key_info['used'] >= key_info['limit']:
        return jsonify({"error": "Daily Limit Reached!"}), 429
    
    api_type = key_info['api_type']
    if api_type not in custom_apis:
        return jsonify({"error": f"API '{api_type}' not configured"}), 500
    
    url = custom_apis[api_type] + query
    
    # Cache
    cache_key = f"{api_key}:{query}"
    if settings.get('cache_enabled', True) and cache_key in cache_store:
        data, cache_time = cache_store[cache_key]
        if time.time() - cache_time < settings.get('cache_duration', 300):
            keys[api_key]['used'] += 1
            save_data(KEYS_FILE, keys)
            return jsonify(data)
    
    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code == 200:
            try:
                data = resp.json()
                # Remove unwanted fields
                for f in ['credit', 'developer', 'owner', 'powered_by', 'BUY_API', 'SUPPORT']:
                    data.pop(f, None)
                if settings.get('enable_credit', True):
                    data['credit'] = settings.get('credit_text', '@Xenon33cyber')
                    data['developed_by'] = '@Xenon33cyber'
                data['api_version'] = VERSION
                data['server_time'] = datetime.now().isoformat()
                
                if settings.get('cache_enabled', True):
                    cache_store[cache_key] = (data.copy(), time.time())
                
                keys[api_key]['used'] += 1
                save_data(KEYS_FILE, keys)
                
                if settings.get('enable_logging', True):
                    update_analytics(api_key, key_info['api_type'], "success", client_ip, request.headers.get('User-Agent'))
                
                return jsonify(data)
            except:
                log_error("JSON_ERROR", "Invalid JSON from backend", api_key, query)
                return jsonify({"error": "Backend returned invalid JSON"}), 502
        else:
            return jsonify({"error": f"Backend error: {resp.status_code}"}), 502
    except Exception as e:
        log_error("CONNECTION_ERROR", str(e), api_key, query)
        return jsonify({"error": f"Connection error: {str(e)}"}), 504

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "version": VERSION, "timestamp": datetime.now().isoformat()})

# ===== VERCEL HANDLER =====
def handler(request, context):
    return app(request.environ, context.start_response)

# ===== LOCAL TESTING =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)