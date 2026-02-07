import os
import random
import json
from io import BytesIO
from datetime import datetime
from flask import Flask, request, send_file, jsonify, render_template_string
from groq import Groq
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from supabase import create_client, Client
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ===== POSTGRESQL DATABASE SETUP =====
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://roast_db_c13t_user:9PO09Y3SpZ6z5r0eYszLsYGHg0bcYtXx@dpg-d5ubdo24d50c73d1bmdg-a/roast_db_c13t")

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_database():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS roasts (
                    id SERIAL PRIMARY KEY,
                    topic VARCHAR(255) NOT NULL,
                    identity_label VARCHAR(100),
                    roast_text TEXT NOT NULL,
                    language VARCHAR(20) DEFAULT 'hindi',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    id SERIAL PRIMARY KEY,
                    total_roasts INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('SELECT COUNT(*) as count FROM stats')
            if cursor.fetchone()['count'] == 0:
                cursor.execute('INSERT INTO stats (total_roasts) VALUES (14203)')
            conn.commit()
            print("✅ PostgreSQL Database initialized")
        except Exception as e:
            print(f"❌ Database error: {e}")
        finally:
            conn.close()

init_database()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = None
if supabase_url and supabase_key:
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase connected")
    except Exception as e:
        print(f"⚠️ Supabase failed: {e}")

MEMES_FOLDER = "memes"

AI_MODELS = [
    "llama-3.3-70b-versatile",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.1-70b-versatile"
]

def get_daily_topic(language='hindi'):
    try:
        with open('daily_topic.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(language, data.get('hindi'))
    except:
        if language == 'hindi':
            return {"topic": "Monday Morning Office", "label": "Corporate Ghulam", "description": "Subah 9 baje se rona shuru"}
        return {"topic": "Monday Morning Office", "label": "Corporate Slave", "description": "Crying since 9am"}

# ===== FRONTEND HTML =====
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Roaster AI - Teri Bezati Free</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            background-image: url('https://i.postimg.cc/R0g9tGYB/Mr.jpg');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 0;
        }

        .navbar {
            position: relative;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            backdrop-filter: blur(12px);
            background: rgba(0, 0, 0, 0.6);
            border-bottom: 1px solid rgba(255, 69, 0, 0.3);
        }

        .nav-brand {
            font-size: 1.5rem;
            font-weight: 900;
            color: #FF4500;
            text-shadow: 0 0 20px rgba(255, 69, 0, 0.5);
        }

        .system-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
            color: #fff;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: #00ff88;
            border-radius: 50%;
            animation: pulse 2s infinite;
            box-shadow: 0 0 10px #00ff88;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(1.2); }
        }

        .container {
            position: relative;
            z-index: 10;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 24px;
            text-align: center;
        }

        /* ===== RGB ANIMATED HOT TOPIC BANNER ===== */
        .hot-topic-banner {
            position: relative;
            background: rgba(0, 0, 0, 0.9);
            border-radius: 20px;
            padding: 24px 28px;
            margin-bottom: 30px;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
            overflow: hidden;
        }

        .hot-topic-banner::before {
            content: '';
            position: absolute;
            top: -3px;
            left: -3px;
            right: -3px;
            bottom: -3px;
            background: linear-gradient(45deg, 
                #ff0000, #ff7300, #fffb00, #48ff00, 
                #00ffd5, #002bff, #7a00ff, #ff00c8, #ff0000);
            background-size: 400%;
            border-radius: 22px;
            z-index: -1;
            animation: rgbBorder 3s linear infinite;
        }

        .hot-topic-banner::after {
            content: '';
            position: absolute;
            top: -3px;
            left: -3px;
            right: -3px;
            bottom: -3px;
            background: linear-gradient(45deg, 
                #ff0000, #ff7300, #fffb00, #48ff00, 
                #00ffd5, #002bff, #7a00ff, #ff00c8, #ff0000);
            background-size: 400%;
            border-radius: 22px;
            z-index: -1;
            animation: rgbBorder 3s linear infinite;
            filter: blur(20px);
            opacity: 0.7;
        }

        @keyframes rgbBorder {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .hot-topic-banner:hover {
            transform: scale(1.02);
        }

        .hot-badge-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 12px;
        }

        .fire-icon {
            font-size: 1.5rem;
            animation: fireFlicker 0.5s infinite alternate;
        }

        @keyframes fireFlicker {
            0% { transform: scale(1) rotate(-5deg); }
            100% { transform: scale(1.15) rotate(5deg); }
        }

        .hot-badge {
            background: linear-gradient(90deg, #ff0000, #ff7300, #fffb00, #48ff00, #00ffd5, #002bff, #7a00ff, #ff00c8);
            background-size: 300%;
            animation: rgbText 3s linear infinite;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            padding: 6px 20px;
            font-size: 0.85rem;
            font-weight: 900;
            letter-spacing: 3px;
            text-transform: uppercase;
        }

        @keyframes rgbText {
            0% { background-position: 0% 50%; }
            100% { background-position: 300% 50%; }
        }

        .hot-topic-text {
            font-size: 1.6rem;
            font-weight: 900;
            color: #fff;
            text-shadow: 0 0 30px rgba(255,255,255,0.5);
            margin-bottom: 8px;
        }

        .hot-topic-desc {
            font-size: 0.95rem;
            color: rgba(255,255,255,0.8);
        }

        .click-hint {
            margin-top: 14px;
            font-size: 0.8rem;
            color: #00ff88;
            font-weight: 700;
            animation: clickPulse 1.5s infinite;
        }

        @keyframes clickPulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }

        .live-ticker {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 20px;
            background: rgba(0, 0, 0, 0.7);
            border: 1px solid rgba(255, 69, 0, 0.3);
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 600;
            color: #FF4500;
            margin-bottom: 24px;
        }

        .hero-headline {
            font-size: clamp(2rem, 7vw, 3.5rem);
            font-weight: 900;
            letter-spacing: -2px;
            margin-bottom: 12px;
            color: #fff;
            text-shadow: 0 4px 20px rgba(0, 0, 0, 0.9);
        }

        .hero-headline .accent {
            color: #FF4500;
            text-shadow: 0 0 40px rgba(255, 69, 0, 0.8);
        }

        .hero-subtext {
            font-size: 1rem;
            color: rgba(255,255,255,0.8);
            margin-bottom: 28px;
        }

        .language-toggle {
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 50px;
            padding: 4px;
            width: fit-content;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid rgba(255, 69, 0, 0.3);
        }

        .lang-btn {
            padding: 10px 24px;
            font-size: 0.9rem;
            font-weight: 700;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s;
            background: transparent;
            color: rgba(255, 255, 255, 0.6);
        }

        .lang-btn.active {
            background: #FF4500;
            color: white;
            box-shadow: 0 4px 15px rgba(255, 69, 0, 0.4);
        }

        .input-engine {
            max-width: 700px;
            margin: 0 auto 24px;
        }

        .command-line {
            display: flex;
            align-items: center;
            background: rgba(0, 0, 0, 0.7);
            border: 1px solid rgba(255, 69, 0, 0.3);
            border-radius: 16px;
            padding: 4px;
            transition: all 0.3s;
        }

        .command-line:focus-within {
            border-color: #FF4500;
            box-shadow: 0 0 0 4px rgba(255, 69, 0, 0.2);
        }

        .command-prefix {
            padding: 0 16px;
            color: #FF4500;
            font-weight: 700;
            font-size: 1.1rem;
        }

        .command-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            padding: 16px 8px;
            font-size: 1rem;
            color: #fff;
        }

        .command-input::placeholder {
            color: #666;
        }

        .execute-btn {
            width: 50px;
            height: 50px;
            background: #FF4500;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
            box-shadow: 0 4px 20px rgba(255, 69, 0, 0.4);
        }

        .execute-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(255, 69, 0, 0.6);
        }

        .execute-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .arrow-icon {
            width: 22px;
            height: 22px;
        }

        .examples-section {
            margin-bottom: 30px;
        }

        .examples-label {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.5);
            margin-bottom: 12px;
        }

        .example-chips {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 8px;
            max-width: 700px;
            margin: 0 auto;
        }

        .example-chip {
            padding: 8px 16px;
            background: rgba(255, 69, 0, 0.15);
            border: 1px solid rgba(255, 69, 0, 0.4);
            border-radius: 50px;
            color: #fff;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .example-chip:hover {
            background: rgba(255, 69, 0, 0.3);
            transform: translateY(-2px);
        }

        .example-chip.hidden {
            display: none;
        }

        .more-options-btn {
            padding: 8px 20px;
            background: transparent;
            border: 1px dashed rgba(255, 255, 255, 0.3);
            border-radius: 50px;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.8rem;
            cursor: pointer;
            margin-top: 10px;
            transition: all 0.3s;
        }

        .more-options-btn:hover {
            border-color: #FF4500;
            color: #FF4500;
        }

        .loading-container {
            display: none;
            padding: 60px;
        }

        .loading-container.active {
            display: block;
        }

        .loading-ring {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(255, 69, 0, 0.1);
            border-top: 4px solid #FF4500;
            border-radius: 50%;
            margin: 0 auto 24px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 1rem;
            color: #FF4500;
            animation: textPulse 2s infinite;
        }

        @keyframes textPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .result-card {
            display: none;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            background: rgba(0, 0, 0, 0.85);
            border: 3px solid #FF4500;
            border-radius: 20px;
            box-shadow: 0 0 60px rgba(255, 69, 0, 0.4);
        }

        .result-card.active {
            display: block;
            animation: cardSlideIn 0.5s ease;
        }

        @keyframes cardSlideIn {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .result-image {
            width: 100%;
            border-radius: 14px;
            margin-bottom: 20px;
            border: 2px solid rgba(255, 69, 0, 0.5);
        }

        .action-buttons {
            display: flex;
            gap: 10px;
        }

        .action-buttons button {
            flex: 1;
            padding: 14px;
            font-size: 0.85rem;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .whatsapp-btn {
            background: #25D366;
            color: white;
        }

        .instagram-btn {
            background: linear-gradient(45deg, #f09433, #dc2743, #bc1888);
            color: white;
        }

        .download-btn {
            background: #1e90ff;
            color: white;
        }

        .retry-btn {
            background: rgba(255, 69, 0, 0.2);
            color: #FF4500;
            border: 2px solid #FF4500 !important;
        }

        .action-buttons button:hover {
            transform: translateY(-2px);
        }

        .error-message {
            display: none;
            max-width: 500px;
            margin: 20px auto;
            padding: 14px;
            background: rgba(255, 69, 0, 0.2);
            border: 1px solid #FF4500;
            border-radius: 12px;
            color: #fff;
            font-weight: 600;
        }

        .error-message.active {
            display: block;
            animation: shake 0.5s;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }

        @media (max-width: 768px) {
            .navbar { padding: 16px 20px; }
            .nav-brand { font-size: 1.2rem; }
            .container { padding: 30px 16px; }
            .hot-topic-banner { padding: 18px 20px; }
            .hot-topic-text { font-size: 1.3rem; }
            .hero-headline { font-size: 1.8rem; }
            .action-buttons { flex-wrap: wrap; }
            .action-buttons button { flex: 1 1 45%; }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="nav-brand">🔥 ROASTER</div>
        <div class="system-status">
            <div class="status-dot"></div>
            <span id="statusText">Savage Mode: ON</span>
        </div>
    </nav>

    <div class="container">
        
        <!-- RGB HOT TOPIC BANNER -->
        <div class="hot-topic-banner" id="hotTopicBanner" onclick="useDailyTopic()">
            <div class="hot-badge-container">
                <span class="fire-icon">🔥</span>
                <span class="hot-badge" id="hotBadge">TODAY'S HOT ROAST</span>
                <span class="fire-icon">🔥</span>
            </div>
            <div class="hot-topic-text" id="hotTopicText">Loading...</div>
            <div class="hot-topic-desc" id="hotTopicDesc"></div>
            <div class="click-hint">👆 TAP TO ROAST THIS 👆</div>
        </div>

        <div class="live-ticker">
            <span>🔥</span>
            <span id="egoCounter">...</span>
            <span id="tickerText">Roasted Today</span>
        </div>

        <h1 class="hero-headline">
            <span id="headlineText">Apni <span class="accent">Aukaat</span> Dekh</span>
        </h1>
        <p class="hero-subtext" id="subtextText">15-20 words mein teri reality check 🪞</p>

        <div class="language-toggle">
            <button class="lang-btn active" id="hindiBtn" onclick="setLanguage('hindi')">🇮🇳 Hindi</button>
            <button class="lang-btn" id="englishBtn" onclick="setLanguage('english')">🇺🇸 English</button>
        </div>

        <div class="input-engine">
            <div class="command-line">
                <span class="command-prefix">></span>
                <input type="text" class="command-input" id="topicInput" placeholder="Kiski leni hai..." maxlength="100">
                <button class="execute-btn" id="executeBtn" onclick="executeRoast()">
                    <svg class="arrow-icon" viewBox="0 0 24 24">
                        <path d="M5 12h14M12 5l7 7-7 7" stroke="white" stroke-width="2" fill="none" stroke-linecap="round"/>
                    </svg>
                </button>
            </div>
        </div>

        <div class="examples-section">
            <p class="examples-label" id="examplesLabel">🎯 Popular:</p>
            <div class="example-chips" id="hindiChips">
                <button class="example-chip" onclick="useExample('Gym wale')">💪 Gym</button>
                <button class="example-chip" onclick="useExample('Engineers')">💻 Engineers</button>
                <button class="example-chip" onclick="useExample('Procrastinators')">⏰ Aalsi</button>
                <button class="example-chip" onclick="useExample('Shopaholics')">🛒 Shopping</button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Social media addicts')">📱 Social Media</button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Broke people')">💸 Gareeb</button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Gamers')">🎮 Gamers</button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Office workers')">👔 Office</button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Diet wale')">🥗 Diet</button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Students')">📚 Students</button>
            </div>
            <div class="example-chips" id="englishChips" style="display:none;">
                <button class="example-chip" onclick="useExample('Gym people')">💪 Gym</button>
                <button class="example-chip" onclick="useExample('Engineers')">💻 Engineers</button>
                <button class="example-chip" onclick="useExample('Procrastinators')">⏰ Lazy</button>
                <button class="example-chip" onclick="useExample('Shopaholics')">🛒 Shopping</button>
                <button class="example-chip hidden english-extra" onclick="useExample('Social media addicts')">📱 Social Media</button>
                <button class="example-chip hidden english-extra" onclick="useExample('Broke dreamers')">💸 Broke</button>
                <button class="example-chip hidden english-extra" onclick="useExample('Gamers')">🎮 Gamers</button>
                <button class="example-chip hidden english-extra" onclick="useExample('Office slaves')">👔 Office</button>
                <button class="example-chip hidden english-extra" onclick="useExample('Diet failures')">🥗 Diet</button>
                <button class="example-chip hidden english-extra" onclick="useExample('Students')">📚 Students</button>
            </div>
            <button class="more-options-btn" id="moreOptionsBtn" onclick="toggleMoreOptions()">+ More</button>
        </div>

        <div class="loading-container" id="loadingContainer">
            <div class="loading-ring"></div>
            <div class="loading-text" id="loadingText">Cooking roast...</div>
        </div>

        <div class="result-card" id="resultCard">
            <img src="" alt="Roast" class="result-image" id="resultImage">
            <div class="action-buttons">
                <button class="whatsapp-btn" onclick="shareToWhatsApp()">📱 WhatsApp</button>
                <button class="instagram-btn" onclick="shareToInstagram()">📸 Insta</button>
                <button class="download-btn" onclick="downloadResult()">⬇️ Save</button>
                <button class="retry-btn" onclick="reset()">🔄 Again</button>
            </div>
        </div>

        <div class="error-message" id="errorMessage"></div>
    </div>

    <script>
        let currentImageUrl = '';
        let currentTopic = '';
        let currentLanguage = 'hindi';
        let moreExpanded = false;
        let dailyTopicData = null;
        
        const loadingHindi = ["Teri aukaat dhundh raha...", "Roast pak raha hai...", "Sach kadwa hoga...", "Reality check loading..."];
        const loadingEnglish = ["Finding your level...", "Cooking your roast...", "Truth incoming...", "Reality check loading..."];

        async function fetchDailyTopic() {
            try {
                const res = await fetch('/api/daily-topic?lang=' + currentLanguage);
                const data = await res.json();
                if (data.success) {
                    dailyTopicData = data.data;
                    document.getElementById('hotTopicText').textContent = dailyTopicData.topic;
                    document.getElementById('hotTopicDesc').textContent = dailyTopicData.description;
                    document.getElementById('hotBadge').textContent = currentLanguage === 'hindi' ? "AAJ KA SPECIAL" : "TODAY'S SPECIAL";
                }
            } catch(e) { console.error(e); }
        }

        function useDailyTopic() {
            if (dailyTopicData) {
                document.getElementById('topicInput').value = dailyTopicData.topic;
                const banner = document.getElementById('hotTopicBanner');
                banner.style.transform = 'scale(0.97)';
                setTimeout(() => { banner.style.transform = ''; executeRoast(); }, 150);
            }
        }

        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('egoCounter').textContent = data.total_roasts.toLocaleString();
            } catch(e) { document.getElementById('egoCounter').textContent = '14,203'; }
        }
        
        fetchStats();
        fetchDailyTopic();
        
        setInterval(() => {
            let c = parseInt(document.getElementById('egoCounter').textContent.replace(/,/g,'')) || 14203;
            document.getElementById('egoCounter').textContent = (c + Math.floor(Math.random()*3)).toLocaleString();
        }, 3000);

        function setLanguage(lang) {
            currentLanguage = lang;
            document.getElementById('hindiBtn').classList.toggle('active', lang === 'hindi');
            document.getElementById('englishBtn').classList.toggle('active', lang === 'english');
            document.getElementById('hindiChips').style.display = lang === 'hindi' ? 'flex' : 'none';
            document.getElementById('englishChips').style.display = lang === 'english' ? 'flex' : 'none';
            
            if (lang === 'hindi') {
                document.getElementById('topicInput').placeholder = "Kiski leni hai...";
                document.getElementById('headlineText').innerHTML = 'Apni <span class="accent">Aukaat</span> Dekh';
                document.getElementById('subtextText').textContent = "15-20 words mein teri reality check 🪞";
                document.getElementById('tickerText').textContent = "Bezati Hui";
                document.getElementById('statusText').textContent = "Gali Mode: ON";
            } else {
                document.getElementById('topicInput').placeholder = "Who to roast...";
                document.getElementById('headlineText').innerHTML = 'See Your <span class="accent">True Self</span>';
                document.getElementById('subtextText').textContent = "15-20 words of brutal truth 🪞";
                document.getElementById('tickerText').textContent = "Roasted Today";
                document.getElementById('statusText').textContent = "Savage Mode: ON";
            }
            fetchDailyTopic();
            hideExtra();
        }

        function toggleMoreOptions() {
            moreExpanded = !moreExpanded;
            document.getElementById('moreOptionsBtn').textContent = moreExpanded ? '− Less' : '+ More';
            moreExpanded ? showExtra() : hideExtra();
        }

        function showExtra() {
            const cls = currentLanguage === 'hindi' ? 'hindi-extra' : 'english-extra';
            document.querySelectorAll('.' + cls).forEach(c => c.classList.remove('hidden'));
        }

        function hideExtra() {
            document.querySelectorAll('.hindi-extra, .english-extra').forEach(c => c.classList.add('hidden'));
            moreExpanded = false;
            document.getElementById('moreOptionsBtn').textContent = '+ More';
        }

        function useExample(topic) {
            document.getElementById('topicInput').value = topic;
        }

        document.getElementById('topicInput').addEventListener('keypress', e => { if(e.key === 'Enter') executeRoast(); });

        async function executeRoast() {
            const topic = document.getElementById('topicInput').value.trim();
            if (!topic) { showError(currentLanguage === 'hindi' ? 'Kuch toh likh!' : 'Type something!'); return; }
            
            currentTopic = topic;
            document.getElementById('resultCard').classList.remove('active');
            document.getElementById('errorMessage').classList.remove('active');
            document.getElementById('loadingContainer').classList.add('active');
            document.getElementById('executeBtn').disabled = true;

            const msgs = currentLanguage === 'hindi' ? loadingHindi : loadingEnglish;
            let i = 0;
            const interval = setInterval(() => {
                document.getElementById('loadingText').textContent = msgs[++i % msgs.length];
            }, 1000);

            try {
                const res = await fetch('/roast?topic=' + encodeURIComponent(topic) + '&lang=' + currentLanguage);
                clearInterval(interval);
                if (!res.ok) throw new Error('Failed');
                
                const blob = await res.blob();
                currentImageUrl = URL.createObjectURL(blob);
                document.getElementById('resultImage').src = currentImageUrl;
                document.getElementById('loadingContainer').classList.remove('active');
                document.getElementById('resultCard').classList.add('active');
                fetchStats();
            } catch(e) {
                clearInterval(interval);
                document.getElementById('loadingContainer').classList.remove('active');
                showError(currentLanguage === 'hindi' ? 'Error! Dobara try kar' : 'Error! Try again');
            } finally {
                document.getElementById('executeBtn').disabled = false;
            }
        }

        function showError(msg) {
            const el = document.getElementById('errorMessage');
            el.textContent = msg;
            el.classList.add('active');
        }

        function shareToWhatsApp() {
            const text = currentLanguage === 'hindi' 
                ? 'Dekh meri bezati 🔥 ' + window.location.href
                : 'Check my roast 🔥 ' + window.location.href;
            window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank');
        }

        function shareToInstagram() {
            downloadResult();
            alert(currentLanguage === 'hindi' ? 'Downloaded! Ab Insta pe daal' : 'Downloaded! Share on Insta');
        }

        function downloadResult() {
            if (currentImageUrl) {
                const a = document.createElement('a');
                a.href = currentImageUrl;
                a.download = 'roast_' + Date.now() + '.jpg';
                a.click();
            }
        }

        function reset() {
            document.getElementById('resultCard').classList.remove('active');
            document.getElementById('topicInput').value = '';
            currentImageUrl = '';
        }

        setLanguage('hindi');
    </script>
</body>
</html>"""


# ===== DATABASE =====
def save_roast_to_db(topic, label, roast, language):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('INSERT INTO roasts (topic, identity_label, roast_text, language) VALUES (%s, %s, %s, %s)', (topic, label, roast, language))
            cur.execute('UPDATE stats SET total_roasts = total_roasts + 1')
            conn.commit()
        except: pass
        finally: conn.close()

def get_total_roasts():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('SELECT total_roasts FROM stats WHERE id = 1')
            r = cur.fetchone()
            return r['total_roasts'] if r else 14203
        except: return 14203
        finally: conn.close()
    return 14203


# ===== IMAGE FUNCTIONS =====
def get_font(size=40):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: continue
    return ImageFont.load_default()

def wrap_text(text, font, max_w):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if font.getbbox(test)[2] <= max_w:
            line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def add_text_to_image(img_path, label, roast):
    img = Image.open(img_path)
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    # Border
    for i in range(8):
        draw.rectangle([i, i, w-1-i, h-1-i], outline="#FF4500" if i < 4 else "#8B0000")
    
    # Label
    lf = get_font(int(h * 0.07))
    lt = label.upper()
    lb = lf.getbbox(lt)
    lx = (w - lb[2]) // 2
    for dx in range(-3,4):
        for dy in range(-3,4):
            draw.text((lx+dx, 20+dy), lt, font=lf, fill="black")
    draw.text((lx, 20), lt, font=lf, fill="#FF4500")
    
    # Roast
    rf = get_font(int(h * 0.05))
    lines = wrap_text(roast, rf, int(w * 0.9))
    lh = int(h * 0.05) + 8
    y = h - len(lines) * lh - 25
    for line in lines:
        lb = rf.getbbox(line)
        x = (w - lb[2]) // 2
        for dx in range(-3,4):
            for dy in range(-3,4):
                draw.text((x+dx, y+dy), line, font=rf, fill="black")
        draw.text((x, y), line, font=rf, fill="#FFFACD")
        y += lh
    
    return img


# ===== AI ROAST =====
def get_roast(topic, language='hindi'):
    if language == 'hindi':
        prompt = f"""Tu savage Hindi roaster hai. Format:
LABEL: [1-2 word funny title]
ROAST: [15-20 words max, relatable, use bc/mc/chutiya/nalla/vela/bewkoof]

Example:
LABEL: Gym Tourist
ROAST: Membership lena hi workout tha, ab body bhi maang raha hai bc

Topic: {topic}"""
    else:
        prompt = f"""You're a savage roaster. Format:
LABEL: [1-2 word funny title]  
ROAST: [15-20 words max, relatable, edgy humor]

Example:
LABEL: Gym Tourist
ROAST: Buying the membership was your only workout this year, clown

Topic: {topic}"""

    for model in AI_MODELS:
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model, temperature=1.2, max_tokens=80
            )
            text = res.choices[0].message.content.strip()
            
            label, roast = "", ""
            for line in text.split('\n'):
                if line.upper().startswith('LABEL:'): label = line.split(':',1)[1].strip().strip('"\'')
                elif line.upper().startswith('ROAST:'): roast = line.split(':',1)[1].strip().strip('"\'')
            
            if not label: label = "Certified Nalla" if language == 'hindi' else "Certified Clown"
            if not roast: roast = text[:100]
            
            return label.replace('*',''), roast.replace('*','')
        except Exception as e:
            print(f"Model {model} failed: {e}")
            continue
    
    if language == 'hindi':
        return ("Certified Nalla", "AI bhi thak gaya tujhe roast karte karte bc")
    return ("Certified Clown", "Even AI got tired roasting you")


# ===== ROUTES =====
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def stats():
    return jsonify({"total_roasts": get_total_roasts(), "success": True})

@app.route('/api/daily-topic')
def daily_topic():
    return jsonify({"success": True, "data": get_daily_topic(request.args.get('lang', 'hindi'))})

@app.route('/roast')
def roast():
    topic = request.args.get('topic', '').strip()
    lang = request.args.get('lang', 'hindi')
    
    if not topic: return jsonify({"error": "No topic"}), 400
    if not os.path.exists(MEMES_FOLDER): return jsonify({"error": "No memes"}), 500
    
    memes = [f for f in os.listdir(MEMES_FOLDER) if f.lower().endswith(('.jpg','.jpeg','.png'))]
    if not memes: return jsonify({"error": "No memes"}), 500
    
    try:
        label, roast_text = get_roast(topic, lang)
        img = add_text_to_image(os.path.join(MEMES_FOLDER, random.choice(memes)), label, roast_text)
        
        buf = BytesIO()
        img.save(buf, 'JPEG', quality=95)
        buf.seek(0)
        
        save_roast_to_db(topic, label, roast_text, lang)
        
        return send_file(BytesIO(buf.getvalue()), mimetype='image/jpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    os.makedirs(MEMES_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
