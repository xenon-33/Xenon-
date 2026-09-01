# -*- coding: utf-8 -*-
"""
Xenon API Management System v3.0.0
Owner: @Xenon33cyber
Developer: @Xenon33cyber
Deploy: Localhost / Render / Vercel
"""

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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ===== FILE PATHS - AUTO DETECT =====
# अगर /tmp है (Render/Vercel) तो वहाँ use करें, नहीं तो local
if os.path.exists("/tmp"):
    BASE_DIR = "/tmp"
else:
    BASE_DIR = os.getcwd()

ADMIN_PASSWORD_FILE = os.path.join(BASE_DIR, "admin_password.json")
KEYS_FILE = os.path.join(BASE_DIR, "api_keys.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "api_settings.json")
ANALYTICS_FILE = os.path.join(BASE_DIR, "analytics.json")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.json")
RATE_LIMIT_FILE = os.path.join(BASE_DIR, "rate_limits.json")
CUSTOM_APIS_FILE = os.path.join(BASE_DIR, "custom_apis.json")
UI_SETTINGS_FILE = os.path.join(BASE_DIR, "ui_settings.json")

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
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return default_data
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    save_data(filepath, default_data)
    return default_data

def save_data(filepath, data):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def get_admin_password():
    data = load_data(ADMIN_PASSWORD_FILE, {"password": "admin", "last_changed": datetime.now().isoformat()})
    return data.get("password", "admin")

def set_admin_password(new_password):
    save_data(ADMIN_PASSWORD_FILE, {
        "password": new_password,
        "last_changed": datetime.now().isoformat()
    })

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
    if len(analytics["top_ips"]) > 1000:
        analytics["top_ips"] = dict(sorted(analytics["top_ips"].items(), key=lambda x: x[1], reverse=True)[:1000])
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

def update_blacklist(entry_type, entry, action="add"):
    blacklist = get_blacklist()
    if action == "add":
        if entry not in blacklist[entry_type]:
            blacklist[entry_type].append(entry)
    elif action == "remove":
        if entry in blacklist[entry_type]:
            blacklist[entry_type].remove(entry)
    save_data(BLACKLIST_FILE, blacklist)

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
    """Convert hex color #RRGGBB to 'R,G,B' string"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r},{g},{b}"
    return "0,255,65"

def get_rgb(settings, key):
    return hex_to_rgb(settings.get(key, '#00ff41'))

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

# ===== LOGIN HTML =====
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XENON • Login</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: {{ settings.bg_color }};
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: {{ settings.primary_color }};
            overflow: hidden;
            position: relative;
        }
        ::selection { background: {{ settings.primary_color }}; color: {{ settings.bg_color }}; }
        #matrix-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            opacity: 0.15;
            pointer-events: none;
        }
        .scanline {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
            background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba({{ rgb_primary }},0.02) 2px, rgba({{ rgb_primary }},0.02) 4px);
        }
        .login-container {
            position: relative;
            z-index: 2;
            max-width: 420px;
            width: 100%;
            padding: 20px;
        }
        .glass {
            background: rgba(10,10,10,0.92);
            backdrop-filter: blur(20px);
            border: 1px solid rgba({{ rgb_primary }},0.2);
            border-radius: 20px;
            padding: 40px 30px;
            box-shadow: 0 0 60px rgba({{ rgb_primary }},0.05);
            position: relative;
            overflow: hidden;
        }
        .glass::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 50% 50%, rgba({{ rgb_primary }},0.03) 0%, transparent 70%);
            animation: rotateGlow 20s linear infinite;
            pointer-events: none;
        }
        @keyframes rotateGlow { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .logo-icon { text-align: center; font-size: 56px; color: {{ settings.primary_color }}; margin-bottom: 10px; text-shadow: 0 0 60px rgba({{ rgb_primary }},0.2); }
        .login-title { text-align: center; font-size: 24px; font-weight: 800; color: {{ settings.primary_color }}; text-shadow: 0 0 40px rgba({{ rgb_primary }},0.15); letter-spacing: 2px; margin-bottom: 6px; }
        .login-title .glitch { {% if ui.glitch_effect %}animation: glitch 3s infinite;{% endif %} }
        @keyframes glitch { 0%,95%,100% { transform: skew(0deg); opacity:1; } 96% { transform: skew(-2deg); opacity:0.8; } 97% { transform: skew(2deg); opacity:0.9; } 98% { transform: skew(-1deg); opacity:0.7; } }
        .login-subtitle { text-align: center; color: {{ settings.secondary_color }}; font-size: 13px; letter-spacing: 4px; text-transform: uppercase; margin-bottom: 30px; font-weight: 300; }
        .form-group { margin-bottom: 18px; position: relative; }
        .form-group label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 2px; color: {{ settings.secondary_color }}; }
        .form-control { width: 100%; padding: 12px 16px; background: rgba({{ rgb_primary }},0.03); border: 1px solid rgba({{ rgb_primary }},0.12); border-radius: 10px; color: {{ settings.primary_color }}; font-size: 14px; transition: all 0.3s ease; font-family: 'Courier New', monospace; letter-spacing: 1px; }
        .form-control:focus { outline: none; border-color: {{ settings.primary_color }}; box-shadow: 0 0 40px rgba({{ rgb_primary }},0.08); background: rgba({{ rgb_primary }},0.05); }
        .form-control::placeholder { color: {{ settings.secondary_color }}; opacity: 0.3; letter-spacing: 2px; }
        .btn { width: 100%; padding: 14px; border: 1px solid {{ settings.primary_color }}; border-radius: 10px; background: rgba({{ rgb_primary }},0.05); color: {{ settings.primary_color }}; font-weight: 700; cursor: pointer; transition: all 0.3s ease; font-family: 'Courier New', monospace; font-size: 14px; letter-spacing: 3px; text-transform: uppercase; position: relative; overflow: hidden; }
        .btn:hover { background: {{ settings.primary_color }}; color: {{ settings.bg_color }}; box-shadow: 0 0 50px rgba({{ rgb_primary }},0.15); transform: translateY(-2px); }
        .btn::after { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 60%); opacity: 0; transition: opacity 0.5s; }
        .btn:hover::after { opacity: 1; }
        .login-footer { margin-top: 20px; text-align: center; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .login-footer a { color: {{ settings.secondary_color }}; text-decoration: none; font-size: 11px; letter-spacing: 1px; transition: color 0.3s; }
        .login-footer a:hover { color: {{ settings.primary_color }}; }
        .login-footer .credit { color: {{ settings.secondary_color }}; font-size: 10px; opacity: 0.5; letter-spacing: 1px; }
        .alert { padding: 10px 14px; border-radius: 8px; margin-bottom: 15px; font-size: 12px; border: 1px solid transparent; letter-spacing: 0.5px; }
        .alert-danger { background: rgba(255,0,0,0.08); color: #ff4444; border-color: rgba(255,0,0,0.15); }
        .alert-success { background: rgba({{ rgb_primary }},0.08); color: {{ settings.primary_color }}; border-color: rgba({{ rgb_primary }},0.15); }
        .forgot-form .btn { background: rgba(255,165,0,0.05); border-color: #ffa500; color: #ffa500; }
        .forgot-form .btn:hover { background: #ffa500; color: {{ settings.bg_color }}; }
        .typing-cursor { display: inline-block; width: 2px; height: 16px; background: {{ settings.primary_color }}; animation: blink 0.8s step-end infinite; vertical-align: text-bottom; margin-left: 2px; }
        @keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0; } }
        @media (max-width:480px) { .glass { padding:25px 20px; } .login-title { font-size:18px; } .logo-icon { font-size:40px; } }
    </style>
</head>
<body>
    {% if ui.matrix_rain %}
    <canvas id="matrix-canvas"></canvas>
    {% endif %}
    <div class="scanline"></div>
    <div class="login-container">
        <div class="glass">
            <div class="logo-icon"><i class="fas {{ ui.logo_icon }}"></i></div>
            <div class="login-title"><span class="glitch">{{ ui.login_title }}</span></div>
            <div class="login-subtitle">{{ ui.login_subtitle }}</div>
            {% if forgot %}
            <form method="POST" action="/reset_password">
                <div class="form-group">
                    <label>New Access Key</label>
                    <input type="password" name="new_password" class="form-control" placeholder="> Enter New Secret_" required>
                </div>
                <div class="form-group">
                    <label>Confirm Access Key</label>
                    <input type="password" name="confirm_password" class="form-control" placeholder="> Confirm New Secret_" required>
                </div>
                <button type="submit" class="btn" style="border-color:#ffa500;color:#ffa500;"><i class="fas fa-key"></i> Reset Access</button>
            </form>
            <div class="login-footer">
                <a href="/login"><i class="fas fa-arrow-left"></i> Return to Login</a>
                <span class="credit">{{ ui.login_credit_text }}</span>
            </div>
            {% else %}
            <form method="POST" action="/login">
                <div class="form-group">
                    <input type="password" name="password" class="form-control" placeholder="{{ ui.login_placeholder }}" id="password-input" required autofocus>
                </div>
                <button type="submit" class="btn"><i class="fas fa-unlock-alt"></i> {{ ui.login_button_text }}</button>
            </form>
            <div class="login-footer">
                <a href="/forgot"><i class="fas fa-question-circle"></i> {{ ui.login_forgot_text }}</a>
                <span class="credit">{{ ui.login_credit_text }}</span>
            </div>
            {% endif %}
        </div>
    </div>
    <script>
        {% if ui.matrix_rain %}
        (function() {
            var canvas = document.getElementById('matrix-canvas');
            if (!canvas) return;
            var ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$#@%&*+=-<>?';
            var columns = Math.floor(canvas.width / 14);
            var drops = [];
            for (var i = 0; i < columns; i++) { drops.push(Math.floor(Math.random() * -100)); }
            function drawMatrix() {
                ctx.fillStyle = 'rgba(10,10,10,0.05)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '{{ settings.primary_color }}';
                ctx.font = '14px monospace';
                for (var i = 0; i < drops.length; i++) {
                    var text = chars[Math.floor(Math.random() * chars.length)];
                    ctx.fillText(text, i * 14, drops[i] * 14);
                    if (drops[i] * 14 > canvas.height && Math.random() > 0.975) { drops[i] = 0; }
                    drops[i]++;
                }
            }
            setInterval(drawMatrix, 50);
            window.addEventListener('resize', function() {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            });
        })();
        {% endif %}
        
        {% if ui.typing_animation %}
        (function() {
            var input = document.getElementById('password-input');
            if (!input) return;
            var original = input.getAttribute('placeholder') || '{{ ui.login_placeholder }}';
            var index = 0;
            var isDeleting = false;
            function typeEffect() {
                if (!isDeleting) {
                    input.setAttribute('placeholder', original.substring(0, index + 1) + '█');
                    index++;
                    if (index >= original.length) {
                        isDeleting = true;
                        setTimeout(typeEffect, 1500);
                        return;
                    }
                    setTimeout(typeEffect, 60);
                } else {
                    input.setAttribute('placeholder', original.substring(0, index) + '█');
                    index--;
                    if (index < 0) {
                        isDeleting = false;
                        index = 0;
                        setTimeout(typeEffect, 500);
                        return;
                    }
                    setTimeout(typeEffect, 30);
                }
            }
            setTimeout(typeEffect, 500);
        })();
        {% endif %}
    </script>
</body>
</html>
"""

# ===== DASHBOARD HTML =====
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XENON • Dashboard</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family:'Courier New',monospace;
            background:{{ settings.bg_color }};
            min-height:100vh;
            color:{{ settings.primary_color }};
            background-image:radial-gradient(circle at 20% 50%, rgba({{ rgb_primary }},0.03) 0%, transparent 50%), radial-gradient(circle at 80% 50%, rgba({{ rgb_primary }},0.03) 0%, transparent 50%);
        }
        ::selection { background:{{ settings.primary_color }}; color:{{ settings.bg_color }}; }
        .container { max-width:1400px; margin:0 auto; padding:15px; }
        .glass { background:rgba(10,10,10,0.95); backdrop-filter:blur(10px); border:1px solid rgba({{ rgb_primary }},0.12); border-radius:16px; padding:20px; box-shadow:0 0 30px rgba({{ rgb_primary }},0.03); }
        .glass:hover { border-color:rgba({{ rgb_primary }},0.2); }
        .header { display:flex; justify-content:space-between; align-items:center; padding:15px 20px; margin-bottom:20px; background:rgba(10,10,10,0.95); border-radius:16px; border:1px solid rgba({{ rgb_primary }},0.12); flex-wrap:wrap; gap:10px; }
        .logo { display:flex; align-items:center; gap:12px; }
        .logo i { font-size:30px; color:{{ settings.primary_color }}; animation:pulse 2s infinite; text-shadow:0 0 20px rgba({{ rgb_primary }},0.15); }
        @keyframes pulse { 0%,100% { transform:scale(1); opacity:1; } 50% { transform:scale(1.05); opacity:0.7; } }
        .logo h1 { font-size:22px; color:{{ settings.primary_color }}; font-weight:800; text-shadow:0 0 30px rgba({{ rgb_primary }},0.1); }
        .logo span { font-size:12px; color:{{ settings.secondary_color }}; }
        .header-actions { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
        .status-badge { padding:6px 12px; border-radius:20px; font-size:11px; font-weight:600; text-transform:uppercase; border:1px solid rgba({{ rgb_primary }},0.2); }
        .status-online { background:rgba({{ rgb_primary }},0.08); color:{{ settings.primary_color }}; }
        .btn { padding:8px 16px; border:1px solid {{ settings.primary_color }}; border-radius:8px; font-weight:600; cursor:pointer; transition:all 0.3s ease; display:inline-flex; align-items:center; gap:6px; font-size:13px; text-decoration:none; white-space:nowrap; font-family:'Courier New',monospace; background:transparent; color:{{ settings.primary_color }}; }
        .btn:hover { background:{{ settings.primary_color }}; color:{{ settings.bg_color }}; box-shadow:0 0 30px rgba({{ rgb_primary }},0.12); transform:translateY(-2px); }
        .btn-danger { border-color:#ff4444; color:#ff4444; }
        .btn-danger:hover { background:#ff4444; color:{{ settings.bg_color }}; box-shadow:0 0 30px rgba(255,0,0,0.15); }
        .btn-warning { border-color:#ffa500; color:#ffa500; }
        .btn-warning:hover { background:#ffa500; color:{{ settings.bg_color }}; }
        .btn-info { border-color:#00ccff; color:#00ccff; }
        .btn-info:hover { background:#00ccff; color:{{ settings.bg_color }}; }
        .btn-success { border-color:{{ settings.primary_color }}; color:{{ settings.primary_color }}; }
        .btn-success:hover { background:{{ settings.primary_color }}; color:{{ settings.bg_color }}; }
        .btn-outline { border-color:{{ settings.secondary_color }}; color:{{ settings.secondary_color }}; }
        .btn-outline:hover { background:{{ settings.secondary_color }}; color:{{ settings.bg_color }}; }
        .btn-sm { padding:4px 10px; font-size:11px; }
        .btn-block { width:100%; justify-content:center; }
        .stats-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:15px; margin-bottom:20px; }
        .stat-card { background:rgba(10,10,10,0.95); padding:15px; border-radius:12px; border:1px solid rgba({{ rgb_primary }},0.08); text-align:center; transition:all 0.3s ease; }
        .stat-card:hover { transform:translateY(-4px); border-color:rgba({{ rgb_primary }},0.2); box-shadow:0 0 30px rgba({{ rgb_primary }},0.05); }
        .stat-card .stat-icon { font-size:20px; margin-bottom:8px; color:{{ settings.primary_color }}; }
        .stat-card .stat-number { font-size:24px; font-weight:700; color:{{ settings.primary_color }}; text-shadow:0 0 30px rgba({{ rgb_primary }},0.1); }
        .stat-card .stat-label { font-size:11px; color:{{ settings.secondary_color }}; margin-top:4px; text-transform:uppercase; letter-spacing:1px; }
        .form-group { margin-bottom:15px; }
        .form-group label { display:block; margin-bottom:6px; font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:1px; color:{{ settings.secondary_color }}; }
        .form-control { width:100%; padding:10px 14px; background:rgba({{ rgb_primary }},0.03); border:1px solid rgba({{ rgb_primary }},0.12); border-radius:8px; color:{{ settings.primary_color }}; font-size:14px; transition:all 0.3s ease; font-family:'Courier New',monospace; }
        .form-control:focus { outline:none; border-color:{{ settings.primary_color }}; box-shadow:0 0 30px rgba({{ rgb_primary }},0.06); }
        .form-control::placeholder { color:{{ settings.secondary_color }}; opacity:0.3; }
        select.form-control option { background:{{ settings.bg_color }}; color:{{ settings.primary_color }}; }
        .table-container { overflow-x:auto; margin-top:15px; }
        table { width:100%; border-collapse:collapse; min-width:600px; }
        th { background:rgba({{ rgb_primary }},0.04); padding:10px 12px; text-align:left; font-size:10px; text-transform:uppercase; letter-spacing:1px; color:{{ settings.secondary_color }}; border-bottom:1px solid rgba({{ rgb_primary }},0.1); }
        td { padding:10px 12px; border-bottom:1px solid rgba({{ rgb_primary }},0.04); font-size:12px; }
        tr:hover { background:rgba({{ rgb_primary }},0.015); }
        .badge { display:inline-block; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:600; border:1px solid transparent; }
        .badge-active { background:rgba({{ rgb_primary }},0.12); color:{{ settings.primary_color }}; border-color:rgba({{ rgb_primary }},0.2); }
        .badge-expired { background:rgba(255,0,0,0.08); color:#ff4444; border-color:rgba(255,0,0,0.15); }
        .badge-custom { background:rgba({{ rgb_primary }},0.06); color:{{ settings.primary_color }}; border-color:rgba({{ rgb_primary }},0.1); }
        .copy-btn { background:rgba({{ rgb_primary }},0.04); color:{{ settings.primary_color }}; border:1px solid rgba({{ rgb_primary }},0.1); padding:4px 12px; border-radius:4px; cursor:pointer; font-size:11px; transition:all 0.3s ease; font-family:'Courier New',monospace; }
        .copy-btn:hover { background:{{ settings.primary_color }}; color:{{ settings.bg_color }}; box-shadow:0 0 20px rgba({{ rgb_primary }},0.1); }
        .copy-btn.copied { background:{{ settings.primary_color }}; color:{{ settings.bg_color }}; }
        .url-display { background:rgba({{ rgb_primary }},0.02); padding:6px 10px; border-radius:4px; font-size:10px; word-break:break-all; font-family:'Courier New',monospace; border-left:2px solid {{ settings.primary_color }}; max-width:250px; margin-bottom:4px; color:{{ settings.secondary_color }}; }
        .settings-grid { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
        .flex-between { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; }
        .text-muted { color:{{ settings.secondary_color }}; font-size:12px; }
        .mt-20 { margin-top:20px; }
        .mb-20 { margin-bottom:20px; }
        .flex { display:flex; align-items:center; flex-wrap:wrap; gap:10px; }
        .section-title { color:{{ settings.primary_color }}; margin-bottom:15px; font-size:18px; text-shadow:0 0 30px rgba({{ rgb_primary }},0.05); letter-spacing:1px; }
        .section-title i { margin-right:8px; }
        .credit-section { background:rgba({{ rgb_primary }},0.02); border:1px solid rgba({{ rgb_primary }},0.06); border-radius:8px; padding:12px; margin-top:10px; text-align:center; }
        .credit-section .credit-text { color:{{ settings.primary_color }}; font-weight:600; }
        .custom-api-item { display:flex; justify-content:space-between; align-items:center; padding:8px 12px; background:rgba({{ rgb_primary }},0.015); border-radius:6px; margin-bottom:6px; border-left:2px solid {{ settings.primary_color }}; flex-wrap:wrap; gap:8px; }
        .custom-api-item .api-name { color:{{ settings.primary_color }}; font-weight:600; font-size:13px; }
        .custom-api-item .api-url { color:{{ settings.secondary_color }}; font-size:11px; word-break:break-all; max-width:60%; }
        .custom-api-item .api-actions { display:flex; gap:6px; }
        .delete-api-btn { background:rgba(255,0,0,0.04); color:#ff4444; border:1px solid rgba(255,0,0,0.1); padding:2px 10px; border-radius:4px; cursor:pointer; font-size:11px; font-family:'Courier New',monospace; }
        .delete-api-btn:hover { background:#ff4444; color:{{ settings.bg_color }}; }
        .toggle { position:relative; display:inline-block; width:44px; height:24px; }
        .toggle input { opacity:0; width:0; height:0; }
        .toggle .slider { position:absolute; cursor:pointer; top:0; left:0; right:0; bottom:0; background:rgba({{ rgb_primary }},0.08); transition:.3s; border-radius:24px; border:1px solid rgba({{ rgb_primary }},0.1); }
        .toggle .slider:before { position:absolute; content:""; height:16px; width:16px; left:3px; bottom:3px; background:{{ settings.secondary_color }}; transition:.3s; border-radius:50%; }
        .toggle input:checked + .slider { background:rgba({{ rgb_primary }},0.15); border-color:{{ settings.primary_color }}; }
        .toggle input:checked + .slider:before { transform:translateX(20px); background:{{ settings.primary_color }}; }
        .toast { position:fixed; bottom:20px; right:20px; background:rgba({{ rgb_primary }},0.1); color:{{ settings.primary_color }}; padding:14px 20px; border-radius:12px; border:1px solid rgba({{ rgb_primary }},0.12); box-shadow:0 4px 30px rgba(0,0,0,0.5); display:none; animation:slideUp 0.3s ease; z-index:1000; font-size:14px; font-family:'Courier New',monospace; }
        @keyframes slideUp { from { transform:translateY(100px); opacity:0; } to { transform:translateY(0); opacity:1; } }
        .key-gen-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
        .key-gen-grid .full-width { grid-column:1 / -1; }
        .alert { padding:12px 16px; border-radius:8px; margin-bottom:15px; font-size:13px; border:1px solid transparent; }
        .alert-success { background:rgba({{ rgb_primary }},0.08); color:{{ settings.primary_color }}; border-color:rgba({{ rgb_primary }},0.12); }
        .alert-danger { background:rgba(255,0,0,0.06); color:#ff4444; border-color:rgba(255,0,0,0.1); }
        .alert-warning { background:rgba(255,165,0,0.06); color:#ffa500; border-color:rgba(255,165,0,0.1); }
        .alert-info { background:rgba(0,200,255,0.06); color:#00ccff; border-color:rgba(0,200,255,0.1); }
        .footer-text { text-align:center; margin-top:25px; padding:15px; color:{{ settings.secondary_color }}; font-size:12px; border-top:1px solid rgba({{ rgb_primary }},0.05); font-family:'Courier New',monospace; letter-spacing:1px; }
        .footer-text .highlight { color:{{ settings.primary_color }}; }
        .scanline { position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; background:repeating-linear-gradient(0deg, transparent, transparent 2px, rgba({{ rgb_primary }},0.01) 2px, rgba({{ rgb_primary }},0.01) 4px); z-index:9999; }
        .ui-editor-grid { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
        @media (max-width:768px) {
            .key-gen-grid { grid-template-columns:1fr; }
            .key-gen-grid .full-width { grid-column:1; }
            .settings-grid { grid-template-columns:1fr; }
            .ui-editor-grid { grid-template-columns:1fr; }
            .stats-grid { grid-template-columns:repeat(2,1fr); }
            .header { flex-direction:column; align-items:stretch; text-align:center; }
            .header-actions { justify-content:center; }
            .logo { justify-content:center; }
        }
    </style>
</head>
<body>
<div class="scanline"></div>
<div class="container">
    <div class="header glass">
        <div class="logo">
            <i class="fas {{ ui.logo_icon }}"></i>
            <div>
                <h1>{{ ui.header_title }}</h1>
                <span>{{ ui.header_subtitle }}</span>
            </div>
        </div>
        <div class="header-actions">
            <span class="status-badge status-online"><i class="fas fa-circle" style="font-size:8px;"></i> Online</span>
            <button class="btn btn-outline btn-sm" onclick="location.reload()"><i class="fas fa-sync-alt"></i> Refresh</button>
            <a href="/change_password" class="btn btn-warning btn-sm"><i class="fas fa-key"></i> Change Password</a>
            <a href="/logout" class="btn btn-danger btn-sm"><i class="fas fa-sign-out-alt"></i> Logout</a>
        </div>
    </div>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message|safe }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-icon"><i class="fas fa-keys"></i></div>
            <div class="stat-number">{{ keys|length }}</div>
            <div class="stat-label">{{ ui.stats_labels.keys }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i class="fas fa-chart-line"></i></div>
            <div class="stat-number">{{ analytics.total_requests|default(0) }}</div>
            <div class="stat-label">{{ ui.stats_labels.requests }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i class="fas fa-calendar-day"></i></div>
            <div class="stat-number">{{ analytics.daily_requests.get(today, 0)|default(0) }}</div>
            <div class="stat-label">{{ ui.stats_labels.daily }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i class="fas fa-plug"></i></div>
            <div class="stat-number">{{ custom_apis|length }}</div>
            <div class="stat-label">{{ ui.stats_labels.custom }}</div>
        </div>
    </div>
    <div class="glass mb-20">
        <h3 class="section-title"><i class="fas fa-palette"></i> UI Customization</h3>
        <form method="POST" action="/update_ui">
            <div class="ui-editor-grid">
                <div class="form-group">
                    <label>Primary Color</label>
                    <input type="color" name="primary_color" class="form-control" value="{{ settings.primary_color }}" style="height:50px;padding:4px;background:transparent;border:1px solid rgba({{ rgb_primary }},0.1);">
                </div>
                <div class="form-group">
                    <label>Secondary Color</label>
                    <input type="color" name="secondary_color" class="form-control" value="{{ settings.secondary_color }}" style="height:50px;padding:4px;background:transparent;border:1px solid rgba({{ rgb_primary }},0.1);">
                </div>
                <div class="form-group">
                    <label>Background Color</label>
                    <input type="color" name="bg_color" class="form-control" value="{{ settings.bg_color }}" style="height:50px;padding:4px;background:transparent;border:1px solid rgba({{ rgb_primary }},0.1);">
                </div>
                <div class="form-group">
                    <label>System Name</label>
                    <input type="text" name="system_name" class="form-control" value="{{ settings.system_name }}" placeholder="Xenon API Management System">
                </div>
                <div class="form-group">
                    <label>Logo Icon</label>
                    <input type="text" name="logo_icon" class="form-control" value="{{ ui.logo_icon }}" placeholder="fa-skull">
                </div>
                <div class="form-group">
                    <label>Header Title</label>
                    <input type="text" name="header_title" class="form-control" value="{{ ui.header_title }}" placeholder="Xenon API Management System">
                </div>
                <div class="form-group">
                    <label>Login Title</label>
                    <input type="text" name="login_title" class="form-control" value="{{ ui.login_title }}" placeholder="⚡ XENON API MANAGEMENT">
                </div>
                <div class="form-group">
                    <label>Login Subtitle</label>
                    <input type="text" name="login_subtitle" class="form-control" value="{{ ui.login_subtitle }}" placeholder="Secure & Encrypted Access">
                </div>
                <div class="form-group">
                    <label>Login Button Text</label>
                    <input type="text" name="login_button_text" class="form-control" value="{{ ui.login_button_text }}" placeholder="Access Core">
                </div>
                <div class="form-group">
                    <label>Login Placeholder</label>
                    <input type="text" name="login_placeholder" class="form-control" value="{{ ui.login_placeholder }}" placeholder="> Enter Master Password_">
                </div>
                <div class="form-group">
                    <label>Footer Credit Text</label>
                    <input type="text" name="footer_text" class="form-control" value="{{ settings.footer_text }}" placeholder="Developed by @Xenon33cyber">
                </div>
                <div class="form-group">
                    <label>Login Credit Text</label>
                    <input type="text" name="login_credit_text" class="form-control" value="{{ ui.login_credit_text }}" placeholder="🔐 Secured by @Xenon33cyber">
                </div>
                <div class="form-group" style="display:flex;align-items:center;gap:15px;flex-wrap:wrap;">
                    <label style="margin:0;display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" name="glitch_effect" {% if ui.glitch_effect %}checked{% endif %}> Glitch Effect
                    </label>
                    <label style="margin:0;display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" name="matrix_rain" {% if ui.matrix_rain %}checked{% endif %}> Matrix Rain
                    </label>
                    <label style="margin:0;display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" name="typing_animation" {% if ui.typing_animation %}checked{% endif %}> Typing Animation
                    </label>
                    <label style="margin:0;display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" name="hacker_style" {% if ui.hacker_style %}checked{% endif %}> Hacker Style
                    </label>
                </div>
            </div>
            <button type="submit" class="btn btn-success btn-block mt-20"><i class="fas fa-save"></i> Apply UI Customizations</button>
        </form>
    </div>
    <div class="glass mb-20">
        <h3 class="section-title"><i class="fas fa-plus-circle"></i> {{ ui.key_gen_title }}</h3>
        <form method="POST" action="/generate">
            <div class="key-gen-grid">
                <div class="form-group">
                    <label>Key Name</label>
                    <input type="text" name="key_name" class="form-control" placeholder="{{ ui.key_gen_name_placeholder }}" required>
                </div>
                <div class="form-group">
                    <label>Daily Limit</label>
                    <input type="number" name="limit" class="form-control" placeholder="{{ ui.key_gen_limit_placeholder }}" required>
                </div>
                <div class="form-group">
                    <label>Expiry Date</label>
                    <input type="date" name="expiry" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>{{ ui.key_gen_type_label }}</label>
                    <select name="type" class="form-control">
                        {% if custom_apis %}
                            {% for api_name in custom_apis.keys() %}
                                <option value="{{ api_name }}">🔧 {{ api_name|upper }} API</option>
                            {% endfor %}
                        {% else %}
                            <option value="custom">🔧 No APIs Added Yet</option>
                        {% endif %}
                    </select>
                </div>
                <div class="form-group full-width">
                    <button type="submit" class="btn btn-success btn-block" style="height:48px;">
                        <i class="fas fa-key"></i> {{ ui.key_gen_submit_text }}
                    </button>
                </div>
            </div>
        </form>
        <div class="credit-section">
            <i class="fas fa-code"></i>
            <span class="credit-text">{{ settings.credit_text }}</span>
        </div>
    </div>
    <div class="glass mb-20">
        <h3 class="section-title"><i class="fas fa-plug"></i> {{ ui.custom_api_title }}</h3>
        <form method="POST" action="/add_custom_api">
            <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:10px;align-items:end;">
                <div class="form-group">
                    <label>API Name</label>
                    <input type="text" name="api_name" class="form-control" placeholder="{{ ui.custom_api_name_placeholder }}" required>
                </div>
                <div class="form-group">
                    <label>API URL (with query placeholder)</label>
                    <input type="url" name="api_url" class="form-control" placeholder="{{ ui.custom_api_url_placeholder }}" required>
                </div>
                <button type="submit" class="btn btn-info" style="height:44px;">
                    <i class="fas fa-plus"></i> {{ ui.custom_api_add_text }}
                </button>
            </div>
        </form>
        {% if custom_apis %}
            <div style="margin-top:15px;">
                <h4 style="color:{{ settings.secondary_color }};font-size:13px;margin-bottom:10px;"><i class="fas fa-list"></i> Your Custom APIs</h4>
                {% for api_name, api_url in custom_apis.items() %}
                    <div class="custom-api-item">
                        <span class="api-name">{{ api_name|upper }}</span>
                        <span class="api-url">{{ api_url }}</span>
                        <div class="api-actions">
                            <form method="POST" action="/delete_custom_api" style="display:inline;">
                                <input type="hidden" name="api_name" value="{{ api_name }}">
                                <button type="submit" class="delete-api-btn" onclick="return confirm('Delete this custom API?')">
                                    <i class="fas fa-trash"></i> Delete
                                </button>
                            </form>
                        </div>
                    </div>
                {% endfor %}
            </div>
        {% else %}
            <div style="margin-top:15px;text-align:center;color:{{ settings.secondary_color }};font-size:13px;padding:20px 0;">
                <i class="fas fa-info-circle"></i> No custom APIs added yet.
            </div>
        {% endif %}
    </div>
    <div class="glass">
        <div class="flex-between mb-20">
            <h3 style="color:{{ settings.primary_color }};font-size:18px;text-shadow:0 0 30px rgba({{ rgb_primary }},0.05);">
                <i class="fas fa-database"></i> {{ ui.keys_table_title }}
            </h3>
            <span class="text-muted">{{ keys|length }} keys total</span>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        {% for header in ui.keys_table_headers %}
                        <th>{{ header }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for k, v in keys.items() %}
                    <tr>
                        <td><strong style="color:{{ settings.primary_color }};font-size:12px;">{{ k }}</strong></td>
                        <td><span class="badge badge-custom">{{ v.api_type|upper }}</span></td>
                        <td>{{ v.used }} / {% if v.limit == 0 %}∞{% else %}{{ v.limit }}{% endif %}</td>
                        <td style="font-size:11px;">{{ v.expiry_date }}</td>
                        <td>
                            {% if v.expiry_date < today %}
                                <span class="badge badge-expired"><i class="fas fa-times-circle"></i> Expired</span>
                            {% else %}
                                <span class="badge badge-active"><i class="fas fa-check-circle"></i> Active</span>
                            {% endif %}
                        </td>
                        <td>
                            <div class="url-display" id="url_{{ loop.index }}">
                                {{ host_url }}api/v1/info?key={{ k }}&query=YOUR_QUERY
                            </div>
                            <button class="copy-btn" onclick="copyToClipboard('url_{{ loop.index }}', this)">
                                <i class="fas fa-copy"></i> Copy URL
                            </button>
                        </td>
                        <td>
                            <form method="POST" action="/delete_key" style="display:inline;">
                                <input type="hidden" name="key_name" value="{{ k }}">
                                <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Delete this key?')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </form>
                            <form method="POST" action="/reset_key" style="display:inline;">
                                <input type="hidden" name="key_name" value="{{ k }}">
                                <button type="submit" class="btn btn-warning btn-sm" onclick="return confirm('Reset usage for this key?')">
                                    <i class="fas fa-undo"></i>
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    <div class="glass mt-20">
        <h3 class="section-title"><i class="fas fa-cog"></i> {{ ui.settings_title }}</h3>
        <div class="settings-grid">
            <div>
                <h4 style="color:{{ settings.secondary_color }};margin-bottom:12px;font-size:13px;">
                    <i class="fas fa-sliders-h"></i> {{ ui.settings_system_title }}
                </h4>
                <form method="POST" action="/update_config">
                    <div class="form-group">
                        <div class="flex flex-between">
                            <label>Maintenance Mode</label>
                            <label class="toggle">
                                <input type="checkbox" name="maintenance_mode" {% if settings.maintenance_mode %}checked{% endif %}>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                    <div class="form-group">
                        <div class="flex flex-between">
                            <label>Enable Logging</label>
                            <label class="toggle">
                                <input type="checkbox" name="enable_logging" {% if settings.enable_logging %}checked{% endif %}>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                    <div class="form-group">
                        <div class="flex flex-between">
                            <label>Enable Cache</label>
                            <label class="toggle">
                                <input type="checkbox" name="cache_enabled" {% if settings.cache_enabled %}checked{% endif %}>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                    <div class="form-group">
                        <div class="flex flex-between">
                            <label>Enable Credits</label>
                            <label class="toggle">
                                <input type="checkbox" name="enable_credit" {% if settings.enable_credit %}checked{% endif %}>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Rate Limit (requests/minute)</label>
                        <input type="number" name="rate_limit_per_minute" class="form-control" value="{{ settings.rate_limit_per_minute }}">
                    </div>
                    <button type="submit" class="btn btn-warning btn-block"><i class="fas fa-save"></i> Update Configuration</button>
                </form>
            </div>
            <div>
                <h4 style="color:{{ settings.secondary_color }};margin-bottom:12px;font-size:13px;">
                    <i class="fas fa-chart-bar"></i> {{ ui.settings_analytics_title }}
                </h4>
                <div style="background:rgba({{ rgb_primary }},0.015);padding:12px;border-radius:8px;max-height:250px;overflow-y:auto;border:1px solid rgba({{ rgb_primary }},0.04);">
                    <div style="margin-bottom:8px;">
                        <strong style="color:{{ settings.primary_color }};font-size:12px;">API Usage:</strong>
                        {% for api, count in analytics.api_usage.items() %}
                            <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba({{ rgb_primary }},0.04);font-size:12px;">
                                <span>{{ api|upper }}</span>
                                <span style="color:{{ settings.primary_color }};">{{ count }}</span>
                            </div>
                        {% endfor %}
                    </div>
                    <div>
                        <strong style="color:#ff4444;font-size:12px;">Recent Errors:</strong>
                        {% for error in analytics.error_logs[-3:]|reverse %}
                            <div style="padding:6px 0;border-bottom:1px solid rgba({{ rgb_primary }},0.04);font-size:11px;">
                                <span style="color:#ff4444;">[{{ error.type }}]</span>
                                <span style="color:{{ settings.secondary_color }};">{{ error.message[:35] }}...</span>
                            </div>
                        {% endfor %}
                    </div>
                </div>
                <div style="margin-top:12px;text-align:center;font-size:11px;color:{{ settings.secondary_color }};">
                    <i class="fas fa-code"></i> {{ ui.footer_credit }}
                </div>
            </div>
        </div>
    </div>
    <div class="footer-text">
        <i class="fas fa-skull"></i> {{ ui.logo_text }} v{{ version }} • 
        <span class="highlight">{{ settings.footer_text }}</span> • 
        <i class="fas fa-lock"></i> Secure & Encrypted
    </div>
</div>
<div id="toast" class="toast"><i class="fas fa-check-circle"></i> <span id="toastMessage">{{ ui.toast_copied }}</span></div>
<script>
    function copyToClipboard(elementId, buttonElement) {
        var element = document.getElementById(elementId);
        var text = element.innerText;
        var isSecure = window.isSecureContext || location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
        if (isSecure && navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(function() {
                showToast('{{ ui.toast_copied }}');
                if (buttonElement) {
                    buttonElement.classList.add('copied');
                    buttonElement.innerHTML = '<i class="fas fa-check"></i> Copied!';
                    setTimeout(function() {
                        buttonElement.classList.remove('copied');
                        buttonElement.innerHTML = '<i class="fas fa-copy"></i> Copy URL';
                    }, 2000);
                }
            }).catch(function() { fallbackCopy(text, buttonElement); });
        } else { fallbackCopy(text, buttonElement); }
    }
    function fallbackCopy(text, buttonElement) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        textarea.style.left = '-9999px';
        textarea.style.top = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            var successful = document.execCommand('copy');
            if (successful) {
                showToast('{{ ui.toast_copied }}');
                if (buttonElement) {
                    buttonElement.classList.add('copied');
                    buttonElement.innerHTML = '<i class="fas fa-check"></i> Copied!';
                    setTimeout(function() {
                        buttonElement.classList.remove('copied');
                        buttonElement.innerHTML = '<i class="fas fa-copy"></i> Copy URL';
                    }, 2000);
                }
            } else { showToast('{{ ui.toast_error }}'); }
        } catch (err) { showToast('{{ ui.toast_error }}'); }
        document.body.removeChild(textarea);
    }
    function showToast(message) {
        var toast = document.getElementById('toast');
        var toastMessage = document.getElementById('toastMessage');
        toastMessage.textContent = message;
        toast.style.display = 'block';
        clearTimeout(toast._timeout);
        toast._timeout = setTimeout(function() { toast.style.display = 'none'; }, 3000);
    }
    document.getElementById('toast').addEventListener('click', function() {
        this.style.display = 'none';
        clearTimeout(this._timeout);
    });
</script>
</body>
</html>
"""

# ===== CHANGE PASSWORD HTML =====
CHANGE_PASSWORD_HTML = """
<!DOCTYPE html>
<html>
<head><title>Change Password</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Courier New',monospace; background:{{ settings.bg_color }}; color:{{ settings.primary_color }}; min-height:100vh; display:flex; align-items:center; justify-content:center; }
    .container { max-width:400px; width:100%; padding:20px; }
    .glass { background:rgba(10,10,10,0.95); border:1px solid rgba({{ rgb_primary }},0.12); border-radius:16px; padding:30px; }
    .form-group { margin-bottom:15px; }
    .form-group label { display:block; margin-bottom:6px; font-size:12px; text-transform:uppercase; color:{{ settings.secondary_color }}; }
    .form-control { width:100%; padding:10px 14px; background:rgba({{ rgb_primary }},0.03); border:1px solid rgba({{ rgb_primary }},0.1); border-radius:8px; color:{{ settings.primary_color }}; font-size:14px; font-family:'Courier New',monospace; }
    .form-control:focus { outline:none; border-color:{{ settings.primary_color }}; box-shadow:0 0 30px rgba({{ rgb_primary }},0.06); }
    .btn { padding:10px 20px; border:1px solid {{ settings.primary_color }}; border-radius:8px; background:transparent; color:{{ settings.primary_color }}; cursor:pointer; font-family:'Courier New',monospace; font-weight:600; transition:all 0.3s ease; display:inline-flex; align-items:center; gap:8px; text-decoration:none; width:100%; justify-content:center; }
    .btn:hover { background:{{ settings.primary_color }}; color:{{ settings.bg_color }}; box-shadow:0 0 30px rgba({{ rgb_primary }},0.1); }
    .btn-danger { border-color:#ff4444; color:#ff4444; }
    .btn-danger:hover { background:#ff4444; color:{{ settings.bg_color }}; }
    .btn-success { border-color:{{ settings.primary_color }}; color:{{ settings.primary_color }}; }
    .btn-success:hover { background:{{ settings.primary_color }}; color:{{ settings.bg_color }}; }
    .mt-20 { margin-top:20px; }
    .text-center { text-align:center; }
    .alert { padding:10px 14px; border-radius:8px; margin-bottom:15px; font-size:13px; border:1px solid transparent; }
    .alert-success { background:rgba({{ rgb_primary }},0.08); color:{{ settings.primary_color }}; border-color:rgba({{ rgb_primary }},0.1); }
    .alert-danger { background:rgba(255,0,0,0.06); color:#ff4444; border-color:rgba(255,0,0,0.1); }
    .logo-icon { font-size:40px; color:{{ settings.primary_color }}; text-align:center; margin-bottom:20px; }
    h2 { text-align:center; color:{{ settings.primary_color }}; text-shadow:0 0 30px rgba({{ rgb_primary }},0.05); margin-bottom:20px; }
</style>
</head>
<body>
<div class="container">
    <div class="glass">
        <div class="logo-icon"><i class="fas fa-key"></i></div>
        <h2>Change Password</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message|safe }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label>Current Password</label>
                <input type="password" name="current_password" class="form-control" placeholder="> Enter current password_" required>
            </div>
            <div class="form-group">
                <label>New Password</label>
                <input type="password" name="new_password" class="form-control" placeholder="> Enter new password_" required>
            </div>
            <div class="form-group">
                <label>Confirm Password</label>
                <input type="password" name="confirm_password" class="form-control" placeholder="> Confirm new password_" required>
            </div>
            <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Change Password</button>
        </form>
        <div class="mt-20 text-center">
            <a href="/dashboard" class="btn" style="border-color:{{ settings.secondary_color }};color:{{ settings.secondary_color }};"><i class="fas fa-arrow-left"></i> Back to Dashboard</a>
        </div>
    </div>
</div>
</body>
</html>
"""

# ==========================================
# ROUTES
# ==========================================

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
        password = request.form.get('password')
        if password == get_admin_password():
            session['admin'] = True
            session['login_time'] = datetime.now().isoformat()
            return redirect('/dashboard')
        else:
            flash('Invalid password! Please try again.', 'danger')
    return render_template_string(LOGIN_HTML, ui=ui, settings=settings, rgb_primary=rgb_primary, forgot=False, version=VERSION)

@app.route('/forgot', methods=['GET'])
def forgot():
    ui = get_ui_settings()
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    rgb_primary = hex_to_rgb(settings.get('primary_color', '#00ff41'))
    return render_template_string(LOGIN_HTML, ui=ui, settings=settings, rgb_primary=rgb_primary, forgot=True, version=VERSION)

@app.route('/reset_password', methods=['POST'])
def reset_password():
    ui = get_ui_settings()
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    rgb_primary = hex_to_rgb(settings.get('primary_color', '#00ff41'))
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    if not new_password or len(new_password) < 4:
        flash('Password must be at least 4 characters long!', 'danger')
        return render_template_string(LOGIN_HTML, ui=ui, settings=settings, rgb_primary=rgb_primary, forgot=True, version=VERSION)
    if new_password != confirm_password:
        flash('Passwords do not match!', 'danger')
        return render_template_string(LOGIN_HTML, ui=ui, settings=settings, rgb_primary=rgb_primary, forgot=True, version=VERSION)
    set_admin_password(new_password)
    flash('Password reset successful! Please login with new password.', 'success')
    return render_template_string(LOGIN_HTML, ui=ui, settings=settings, rgb_primary=rgb_primary, forgot=False, version=VERSION)

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
            flash('Current password is incorrect!', 'danger')
            return redirect('/change_password')
        if not new or len(new) < 4:
            flash('New password must be at least 4 characters!', 'danger')
            return redirect('/change_password')
        if new != confirm:
            flash('Passwords do not match!', 'danger')
            return redirect('/change_password')
        set_admin_password(new)
        flash('Password changed successfully!', 'success')
        return redirect('/dashboard')
    return render_template_string(CHANGE_PASSWORD_HTML, ui=ui, settings=settings, rgb_primary=rgb_primary)

@app.route('/dashboard')
@admin_required
def dashboard():
    analytics = get_analytics()
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    custom_apis = get_custom_apis()
    ui = get_ui_settings()
    rgb_primary = hex_to_rgb(settings.get('primary_color', '#00ff41'))
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value
    return render_template_string(
        DASHBOARD_HTML,
        logged_in=True,
        keys=get_keys(),
        settings=settings,
        rgb_primary=rgb_primary,
        host_url=request.url_root,
        analytics=analytics,
        today=str(date.today()),
        version=VERSION,
        custom_apis=custom_apis,
        ui=ui
    )

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('login_time', None)
    return redirect('/login')

@app.route('/generate', methods=['POST'])
@admin_required
def generate_web():
    keys = get_keys()
    key_name = request.form.get('key_name')
    if len(keys) >= MAX_KEYS_PER_USER:
        flash('Maximum keys limit reached!', 'danger')
        return redirect('/dashboard')
    custom_apis = get_custom_apis()
    api_type = request.form.get('type')
    if not custom_apis and api_type == 'custom':
        flash('No custom APIs added yet! Please add an API first.', 'danger')
        return redirect('/dashboard')
    keys[key_name] = {
        "limit": int(request.form.get('limit')),
        "used": 0,
        "expiry_date": request.form.get('expiry'),
        "api_type": request.form.get('type'),
        "last_used_date": str(date.today()),
        "created_at": datetime.now().isoformat(),
        "created_by": request.remote_addr
    }
    save_data(KEYS_FILE, keys)
    flash(f'API Key "{key_name}" created successfully!', 'success')
    return redirect('/dashboard')

@app.route('/delete_key', methods=['POST'])
@admin_required
def delete_web():
    keys = get_keys()
    key_name = request.form.get('key_name')
    keys.pop(key_name, None)
    save_data(KEYS_FILE, keys)
    flash(f'API Key "{key_name}" deleted!', 'warning')
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
        flash(f'API Key "{key_name}" usage reset!', 'success')
    return redirect('/dashboard')

@app.route('/update_config', methods=['POST'])
@admin_required
def update_config():
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    settings.update({
        "maintenance_mode": 'maintenance_mode' in request.form,
        "enable_logging": 'enable_logging' in request.form,
        "cache_enabled": 'cache_enabled' in request.form,
        "enable_credit": 'enable_credit' in request.form,
        "rate_limit_per_minute": int(request.form.get('rate_limit_per_minute', 60))
    })
    save_data(SETTINGS_FILE, settings)
    flash('Configuration updated successfully!', 'success')
    return redirect('/dashboard')

@app.route('/update_ui', methods=['POST'])
@admin_required
def update_ui():
    ui = get_ui_settings()
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    
    settings['primary_color'] = request.form.get('primary_color', '#00ff41')
    settings['secondary_color'] = request.form.get('secondary_color', '#00aa33')
    settings['bg_color'] = request.form.get('bg_color', '#0a0a0a')
    settings['system_name'] = request.form.get('system_name', 'Xenon API Management System')
    settings['footer_text'] = request.form.get('footer_text', 'Developed by @Xenon33cyber')
    
    ui['logo_icon'] = request.form.get('logo_icon', 'fa-skull')
    ui['header_title'] = request.form.get('header_title', 'Xenon API Management System')
    ui['header_subtitle'] = request.form.get('header_subtitle', 'Premium API Management Platform')
    ui['login_title'] = request.form.get('login_title', '⚡ XENON API MANAGEMENT')
    ui['login_subtitle'] = request.form.get('login_subtitle', 'Secure & Encrypted Access')
    ui['login_button_text'] = request.form.get('login_button_text', 'Access Core')
    ui['login_placeholder'] = request.form.get('login_placeholder', '> Enter Master Password_')
    ui['login_credit_text'] = request.form.get('login_credit_text', '🔐 Secured by @Xenon33cyber')
    ui['glitch_effect'] = 'glitch_effect' in request.form
    ui['matrix_rain'] = 'matrix_rain' in request.form
    ui['typing_animation'] = 'typing_animation' in request.form
    ui['hacker_style'] = 'hacker_style' in request.form
    
    save_data(SETTINGS_FILE, settings)
    save_ui_settings(ui)
    flash('UI settings updated successfully!', 'success')
    return redirect('/dashboard')

@app.route('/add_custom_api', methods=['POST'])
@admin_required
def add_custom_api():
    api_name = request.form.get('api_name', '').strip().lower()
    api_url = request.form.get('api_url', '').strip()
    if not api_name or not api_url:
        flash('Please provide both API name and URL!', 'danger')
        return redirect('/dashboard')
    api_name = re.sub(r'[^a-zA-Z0-9_]', '', api_name)
    save_custom_api(api_name, api_url)
    flash(f'Custom API "{api_name}" added successfully!', 'success')
    return redirect('/dashboard')

@app.route('/delete_custom_api', methods=['POST'])
@admin_required
def delete_custom_api_route():
    api_name = request.form.get('api_name')
    if api_name and delete_custom_api(api_name):
        flash(f'Custom API "{api_name}" deleted!', 'warning')
    return redirect('/dashboard')

# ==========================================
# API ENDPOINT
# ==========================================

cache_store = {}

@app.route('/api/v1/info', methods=['GET', 'POST'])
def api_endpoint():
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    if settings.get('maintenance_mode', False):
        return jsonify({"error": "API is under maintenance. Please try again later."}), 503
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if settings.get('blacklist_enabled', True):
        blacklist = get_blacklist()
        if client_ip in blacklist.get('ips', []):
            return jsonify({"error": "Your IP has been blocked due to suspicious activity."}), 403
    if not rate_limit_check(client_ip):
        return jsonify({"error": "Rate limit exceeded. Please wait a moment."}), 429
    api_key = request.args.get('key')
    query = request.args.get('query')
    if not api_key or not query:
        return jsonify({"error": "Missing parameters! Usage: /api/v1/info?key=YOUR_KEY&query=TARGET_DATA"}), 400
    keys = get_keys()
    custom_apis = get_custom_apis()
    if api_key not in keys:
        log_error("INVALID_KEY", f"Invalid key used: {api_key}", api_key, query)
        return jsonify({"error": "Invalid API Key!"}), 401
    if settings.get('blacklist_enabled', True):
        blacklist = get_blacklist()
        if api_key in blacklist.get('keys', []):
            return jsonify({"error": "API Key has been revoked."}), 403
    key_info = keys[api_key]
    if date.today() > datetime.strptime(key_info.get('expiry_date', '2099-12-31'), '%Y-%m-%d').date():
        log_error("EXPIRED_KEY", f"Expired key used: {api_key}", api_key, query)
        return jsonify({"error": "API Key Expired! Contact Admin."}), 403
    if key_info['limit'] != 0 and key_info['used'] >= key_info['limit']:
        return jsonify({"error": "Daily Limit Reached!"}), 429
    api_type = key_info['api_type']
    if api_type in custom_apis:
        base_url = custom_apis[api_type]
    else:
        return jsonify({"error": f"API endpoint '{api_type}' is not configured."}), 500
    if request.host in base_url:
        log_error("CONFIG_ERROR", "Self-referencing API configuration", api_key, query)
        return jsonify({"error": "CRITICAL CONFIG ERROR: You pasted your OWN API link in the settings!"}), 500
    url = base_url + query
    cache_key = f"{api_key}:{query}"
    if settings.get('cache_enabled', True) and cache_key in cache_store:
        cache_data, cache_time = cache_store[cache_key]
        if time.time() - cache_time < settings.get('cache_duration', 300):
            keys[api_key]['used'] += 1
            save_data(KEYS_FILE, keys)
            return jsonify(cache_data)
    try:
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if 'text/html' in resp.headers.get('Content-Type', ''):
            log_error("HTML_RESPONSE", "Backend returned HTML", api_key, query)
            return jsonify({"error": "Backend Source API is returning HTML instead of JSON."}), 502
        if resp.status_code == 200:
            try:
                data = resp.json()
                for f in ['credit', 'developer', 'owner', 'powered_by', 'api_by', 'BUY_API', 'SUPPORT', 'author', 'created_by']:
                    data.pop(f, None)
                if settings.get('enable_credit', True):
                    data['credit'] = settings.get('credit_text', '@Xenon33cyber')
                    data['BUY_API'] = settings.get('credit_text', '@Xenon33cyber')
                    data['developed_by'] = settings.get('credit_text', '@Xenon33cyber')
                data['api_version'] = VERSION
                data['server_time'] = datetime.now().isoformat()
                data['api_name'] = settings.get('system_name', API_NAME)
                if settings.get('cache_enabled', True):
                    cache_store[cache_key] = (data.copy(), time.time())
                keys[api_key]['used'] += 1
                save_data(KEYS_FILE, keys)
                if settings.get('enable_logging', True):
                    update_analytics(api_key, key_info['api_type'], "success", client_ip, request.headers.get('User-Agent'))
                return jsonify(data)
            except json.JSONDecodeError:
                log_error("JSON_ERROR", "Invalid JSON from backend", api_key, query)
                return jsonify({"error": "Backend API Data is Corrupted (Not valid JSON)."}), 502
        log_error("HTTP_ERROR", f"Backend returned {resp.status_code}", api_key, query)
        return jsonify({"error": f"Original API Down (HTTP Code: {resp.status_code})"}), 502
    except requests.exceptions.RequestException as e:
        log_error("CONNECTION_ERROR", str(e), api_key, query)
        return jsonify({"error": f"Failed to connect to Source API: {str(e)}"}), 504

@app.route('/api/analytics')
@admin_required
def get_analytics_endpoint():
    return jsonify(get_analytics())

@app.route('/api/keys/stats')
@admin_required
def get_key_stats():
    keys = get_keys()
    stats = {"total": len(keys), "active": 0, "expired": 0, "by_type": {}}
    for k, v in keys.items():
        if date.today() <= datetime.strptime(v['expiry_date'], '%Y-%m-%d').date():
            stats["active"] += 1
        else:
            stats["expired"] += 1
        api_type = v['api_type']
        if api_type not in stats["by_type"]:
            stats["by_type"][api_type] = 0
        stats["by_type"][api_type] += 1
    return jsonify(stats)

@app.route('/api/health', methods=['GET'])
def health_check():
    settings = load_data(SETTINGS_FILE, DEFAULT_SETTINGS)
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "api_name": settings.get('system_name', API_NAME),
        "owner": settings.get('credit_text', '@Xenon33cyber')
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found. Use /api/v1/info"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

# ===== VERCEL HANDLER =====
def handler(request, context):
    return app(request.environ, context.start_response)

# ===== MAIN =====
if __name__ == "__main__":
    # Localhost के लिए 5099, Render/Vercel के लिए PORT env
    port = int(os.environ.get("PORT", 5099))
    print("=" * 70)
    print(f"💀 {API_NAME} v{VERSION}")
    print("=" * 70)
    print(f"🌍 Localhost: http://localhost:{port}")
    print(f"🌍 Network: http://0.0.0.0:{port}")
    print("🔑 Admin Password: admin")
    print("📊 Analytics: Enabled")
    print("🛡️ Rate Limiting: Active")
    print("⚡ Cache: Enabled")
    print("🔧 Custom APIs: Admin Can Add")
    print("🎨 UI Customization: Fully Configurable")
    print(f"💀 Owner: @Xenon33cyber")
    print("=" * 70)
    print("\n📌 Endpoints:")
    print(f"  🌐 Dashboard: http://localhost:{port}/dashboard")
    print(f"  🔑 Login: http://localhost:{port}/login")
    print(f"  📡 API: http://localhost:{port}/api/v1/info?key=admin&query=test")
    print(f"  ❤️ Health: http://localhost:{port}/api/health")
    print("=" * 70)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)