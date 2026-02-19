import os
import random
import json
from io import BytesIO
from datetime import datetime
from flask import Flask, request, send_file, jsonify, render_template_string
from groq import Groq
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Import search if available
try:
    from search import get_smart_context, get_india_trending
    SEARCH_ENABLED = True
except:
    SEARCH_ENABLED = False

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://roast_db_c13t_user:9PO09Y3SpZ6z5r0eYszLsYGHg0bcYtXx@dpg-d5ubdo24d50c73d1bmdg-a/roast_db_c13t")
MEMES_FOLDER = "memes"
AI_MODELS = ["llama-3.3-70b-versatile", "qwen/qwen-2.5-72b-instruct", "meta-llama/llama-3.1-70b-versatile"]

# Database functions
def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except:
        return None

def init_database():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS roasts (
                id SERIAL PRIMARY KEY, topic VARCHAR(255), label VARCHAR(100),
                roast TEXT, language VARCHAR(20), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS stats (
                id SERIAL PRIMARY KEY, total_roasts INTEGER DEFAULT 0
            )''')
            cur.execute('SELECT COUNT(*) as c FROM stats')
            if cur.fetchone()['c'] == 0:
                cur.execute('INSERT INTO stats (total_roasts) VALUES (52341)')
            conn.commit()
        except: pass
        finally: conn.close()

init_database()

def get_total_roasts():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('SELECT total_roasts FROM stats WHERE id=1')
            r = cur.fetchone()
            return r['total_roasts'] if r else 52341
        except: return 52341
        finally: conn.close()
    return 52341

def save_roast(topic, label, roast, lang):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('INSERT INTO roasts (topic, label, roast, language) VALUES (%s,%s,%s,%s)', (topic, label, roast, lang))
            cur.execute('UPDATE stats SET total_roasts = total_roasts + 1')
            conn.commit()
        except: pass
        finally: conn.close()

def get_daily_topic(lang='hindi'):
    try:
        with open('daily_topic.json', 'r', encoding='utf-8') as f:
            return json.load(f).get(lang)
    except:
        return {"topic": "Monday Morning", "label": "Somvar Syndrome"}

# Example roasts for rotating display
EXAMPLE_ROASTS = {
    "hindi": [
        {"topic": "Gym Wale", "label": "PROTEIN PAKODA", "roast": "Creatine ka dabba 2000 ka, body abhi bhi 2002 wali hai"},
        {"topic": "Engineers", "label": "CTRL+C DEVELOPER", "roast": "Stack Overflow band ho jaye toh inki salary bhi band"},
        {"topic": "Monday", "label": "SOMVAR VICTIM", "roast": "Alarm 6 baje laga ke 9 baje uthna talent nahi majboori hai"},
        {"topic": "Influencers", "label": "FOLLOW KA BHIKHARI", "roast": "500 followers pe bhi bio mein 'DM for collab' likha hai"},
        {"topic": "Startups", "label": "FUNDED FAILURE", "roast": "Idea nahi hai business ka, bas pitch deck ready hai"}
    ],
    "english": [
        {"topic": "Gym Bros", "label": "PROTEIN CLOWN", "roast": "Spent more on supplements than actual workouts this year"},
        {"topic": "Engineers", "label": "COPY PASTE DEV", "roast": "If Stack Overflow shuts down half the tech industry collapses"},
        {"topic": "Monday", "label": "MONDAY SURVIVOR", "roast": "Set 5 alarms to wake up and still blamed traffic for being late"},
        {"topic": "Influencers", "label": "CLOUT CHASER", "roast": "500 followers but bio says 'DM for collaborations'"},
        {"topic": "Startups", "label": "FUNDED MESS", "roast": "No product no users but pitch deck has 47 slides"}
    ]
}

# ===== CLEAN UI =====
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ROASTER - India's Brutal Roast Machine</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg: #0D0D0D;
            --primary: #FF6B35;
            --accent: #FFD23F;
            --text: #FFFFFF;
            --text-muted: #888888;
            --card-bg: #1A1A1A;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        /* ===== HEADER ===== */
        .header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(13,13,13,0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .logo {
            font-size: 1.2rem;
            font-weight: 900;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .live-count {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
            color: var(--text-muted);
        }
        
        .live-dot {
            width: 8px;
            height: 8px;
            background: #00FF00;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        .count-num {
            color: var(--accent);
            font-weight: 700;
        }
        
        /* ===== HERO SECTION ===== */
        .hero {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 80px 20px 120px;
            position: relative;
        }
        
        /* Rotating Example Card */
        .example-card {
            position: relative;
            width: 100%;
            max-width: 380px;
            background: var(--card-bg);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 40px;
            opacity: 0.6;
            transform: scale(0.95);
            transition: all 0.5s ease;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .example-card:hover {
            opacity: 0.9;
            transform: scale(1);
        }
        
        .example-label {
            display: inline-block;
            background: var(--primary);
            color: #000;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 800;
            margin-bottom: 12px;
            letter-spacing: 1px;
        }
        
        .example-topic {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 8px;
        }
        
        .example-roast {
            font-size: 1.1rem;
            font-weight: 600;
            line-height: 1.5;
            color: var(--text);
        }
        
        .example-hint {
            text-align: center;
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 12px;
        }
        
        /* Input Section */
        .input-section {
            width: 100%;
            max-width: 500px;
        }
        
        .input-wrapper {
            position: relative;
            margin-bottom: 16px;
        }
        
        .main-input {
            width: 100%;
            padding: 20px 24px;
            font-size: 1.1rem;
            font-family: inherit;
            background: var(--card-bg);
            border: 2px solid transparent;
            border-radius: 16px;
            color: var(--text);
            outline: none;
            transition: all 0.3s;
        }
        
        .main-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 30px rgba(255,107,53,0.2);
        }
        
        .main-input::placeholder {
            color: var(--text-muted);
        }
        
        /* Language Toggle */
        .lang-toggle {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-bottom: 16px;
        }
        
        .lang-btn {
            padding: 8px 16px;
            font-size: 0.8rem;
            font-weight: 600;
            background: transparent;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .lang-btn.active {
            background: var(--primary);
            border-color: var(--primary);
            color: #000;
        }
        
        /* Main Button */
        .roast-btn {
            width: 100%;
            padding: 20px;
            font-size: 1.2rem;
            font-weight: 800;
            font-family: inherit;
            background: linear-gradient(135deg, var(--primary), #FF8C42);
            border: none;
            border-radius: 16px;
            color: #000;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .roast-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(255,107,53,0.4);
        }
        
        .roast-btn:active {
            transform: translateY(0);
        }
        
        .roast-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Quick Chips */
        .quick-chips {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 8px;
            margin-top: 20px;
        }
        
        .chip {
            padding: 8px 14px;
            font-size: 0.8rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .chip:hover {
            background: rgba(255,107,53,0.2);
            border-color: var(--primary);
            color: var(--text);
        }
        
        /* ===== RESULT SECTION ===== */
        .result-section {
            display: none;
            min-height: 100vh;
            padding: 80px 20px 40px;
            flex-direction: column;
            align-items: center;
        }
        
        .result-section.active {
            display: flex;
        }
        
        .result-topic {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 16px;
        }
        
        .result-card {
            width: 100%;
            max-width: 450px;
            border-radius: 20px;
            overflow: hidden;
            margin-bottom: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        
        .result-image {
            width: 100%;
            display: block;
        }
        
        .primary-actions {
            display: flex;
            gap: 12px;
            width: 100%;
            max-width: 450px;
            margin-bottom: 16px;
        }
        
        .action-btn {
            flex: 1;
            padding: 16px;
            font-size: 1rem;
            font-weight: 700;
            font-family: inherit;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .btn-save {
            background: var(--primary);
            color: #000;
        }
        
        .btn-new {
            background: var(--card-bg);
            border: 2px solid var(--primary);
            color: var(--primary);
        }
        
        .action-btn:hover {
            transform: translateY(-2px);
        }
        
        .share-actions {
            display: flex;
            gap: 12px;
        }
        
        .share-btn {
            padding: 12px 20px;
            font-size: 0.85rem;
            font-weight: 600;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .share-btn:hover {
            background: rgba(255,255,255,0.2);
            color: var(--text);
        }
        
        /* ===== LOADING ===== */
        .loading-section {
            display: none;
            min-height: 100vh;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .loading-section.active {
            display: flex;
        }
        
        .loader {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(255,107,53,0.2);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-bottom: 24px;
        }
        
        @keyframes spin {
            100% { transform: rotate(360deg); }
        }
        
        .loading-text {
            font-size: 1rem;
            color: var(--text-muted);
        }
        
        /* ===== TRENDING BAR (Bottom) ===== */
        .trending-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 100;
            padding: 12px 16px;
            background: rgba(13,13,13,0.95);
            backdrop-filter: blur(10px);
            border-top: 1px solid rgba(255,255,255,0.05);
            display: flex;
            align-items: center;
            gap: 12px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        
        .trending-bar::-webkit-scrollbar {
            display: none;
        }
        
        .trending-label {
            font-size: 0.75rem;
            color: var(--primary);
            font-weight: 700;
            white-space: nowrap;
        }
        
        .trending-chip {
            padding: 6px 14px;
            font-size: 0.8rem;
            background: rgba(255,107,53,0.15);
            border: 1px solid rgba(255,107,53,0.3);
            border-radius: 20px;
            color: var(--text);
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.3s;
        }
        
        .trending-chip:hover {
            background: var(--primary);
            color: #000;
        }
        
        /* ===== MOBILE ===== */
        @media (max-width: 600px) {
            .header {
                padding: 12px 16px;
            }
            
            .logo {
                font-size: 1rem;
            }
            
            .hero {
                padding: 70px 16px 100px;
            }
            
            .example-card {
                padding: 20px;
                margin-bottom: 30px;
            }
            
            .main-input {
                padding: 18px 20px;
                font-size: 1rem;
            }
            
            .roast-btn {
                padding: 18px;
                font-size: 1.1rem;
            }
            
            .result-section {
                padding: 70px 16px 80px;
            }
            
            .primary-actions {
                flex-direction: column;
            }
            
            .share-actions {
                flex-wrap: wrap;
                justify-content: center;
            }
        }
        
        /* Hide sections */
        .hidden {
            display: none !important;
        }
    </style>
</head>
<body>
    <!-- HEADER -->
    <header class="header">
        <div class="logo">🔥 ROASTER</div>
        <div class="live-count">
            <div class="live-dot"></div>
            <span class="count-num" id="liveCount">52,341</span>
            <span>roasted</span>
        </div>
    </header>
    
    <!-- HERO SECTION -->
    <section class="hero" id="heroSection">
        <!-- Rotating Example Card -->
        <div class="example-card" id="exampleCard">
            <div class="example-label" id="exampleLabel">PROTEIN PAKODA</div>
            <div class="example-topic" id="exampleTopic">Gym Wale</div>
            <div class="example-roast" id="exampleRoast">"Creatine ka dabba 2000 ka, body abhi bhi 2002 wali hai"</div>
            <div class="example-hint">↑ Ye mil sakta hai tujhe bhi</div>
        </div>
        
        <!-- Input Section -->
        <div class="input-section">
            <div class="input-wrapper">
                <input 
                    type="text" 
                    class="main-input" 
                    id="topicInput"
                    placeholder="Kisko roast karein?"
                    maxlength="100"
                    autofocus
                >
            </div>
            
            <div class="lang-toggle">
                <button class="lang-btn active" id="hindiBtn" onclick="setLang('hindi')">हिंदी</button>
                <button class="lang-btn" id="englishBtn" onclick="setLang('english')">English</button>
                <button class="lang-btn" id="mixBtn" onclick="setLang('mix')">Mix</button>
            </div>
            
            <button class="roast-btn" id="roastBtn" onclick="generateRoast()">
                <span>🔥</span>
                <span id="btnText">ROAST KARO</span>
            </button>
            
            <div class="quick-chips" id="quickChips">
                <button class="chip" onclick="useTopic('Monday')">Monday</button>
                <button class="chip" onclick="useTopic('My Ex')">My Ex</button>
                <button class="chip" onclick="useTopic('Engineers')">Engineers</button>
                <button class="chip" onclick="useTopic('Gym')">Gym</button>
                <button class="chip" onclick="useTopic('Office')">Office</button>
            </div>
        </div>
    </section>
    
    <!-- LOADING SECTION -->
    <section class="loading-section" id="loadingSection">
        <div class="loader"></div>
        <div class="loading-text" id="loadingText">Roast ban raha hai...</div>
    </section>
    
    <!-- RESULT SECTION -->
    <section class="result-section" id="resultSection">
        <div class="result-topic" id="resultTopic">Topic: Monday</div>
        
        <div class="result-card">
            <img src="" alt="Roast" class="result-image" id="resultImage">
        </div>
        
        <div class="primary-actions">
            <button class="action-btn btn-save" onclick="downloadImage()">
                <span>📥</span> Save
            </button>
            <button class="action-btn btn-new" onclick="newRoast()">
                <span>🔄</span> New Roast
            </button>
        </div>
        
        <div class="share-actions">
            <button class="share-btn" onclick="shareWhatsApp()">WhatsApp</button>
            <button class="share-btn" onclick="shareTwitter()">Twitter</button>
            <button class="share-btn" onclick="copyLink()">Copy Link</button>
        </div>
    </section>
    
    <!-- TRENDING BAR -->
    <div class="trending-bar" id="trendingBar">
        <span class="trending-label">🔥 Trending:</span>
        <button class="trending-chip" onclick="useTopic('IPL')">IPL</button>
        <button class="trending-chip" onclick="useTopic('AI Jobs')">AI Jobs</button>
        <button class="trending-chip" onclick="useTopic('Traffic')">Traffic</button>
        <button class="trending-chip" onclick="useTopic('Startup')">Startup</button>
        <button class="trending-chip" onclick="useTopic('Influencers')">Influencers</button>
        <button class="trending-chip" onclick="useTopic('Cricket')">Cricket</button>
    </div>

    <script>
        let currentLang = 'hindi';
        let currentImg = '';
        let currentTopic = '';
        let exampleIndex = 0;
        
        const examples = {
            hindi: [
                {label: "PROTEIN PAKODA", topic: "Gym Wale", roast: "Creatine ka dabba 2000 ka, body abhi bhi 2002 wali hai"},
                {label: "CTRL+C WARRIOR", topic: "Engineers", roast: "Stack Overflow band ho jaye toh inki salary bhi band"},
                {label: "SOMVAR VICTIM", topic: "Monday", roast: "Alarm 6 ka lagaya, utha 9 baje, blame kiya traffic ko"},
                {label: "CLOUT BHIKHARI", topic: "Influencers", roast: "500 followers pe bio mein 'DM for collab' likha hai"},
                {label: "PITCH DECK PRO", topic: "Startups", roast: "Product nahi hai, users nahi hai, bas funding ki baat hai"}
            ],
            english: [
                {label: "PROTEIN CLOWN", topic: "Gym Bros", roast: "Spent more on supplements than actual gym visits this year"},
                {label: "STACKOVERFLOW DEV", topic: "Engineers", roast: "If Google goes down half the developers become unemployed"},
                {label: "MONDAY HATER", topic: "Monday", roast: "Sets 10 alarms, still blames traffic for being late"},
                {label: "CLOUT CHASER", topic: "Influencers", roast: "500 followers but 'Open for collaborations' in bio"},
                {label: "PITCH MASTER", topic: "Startups", roast: "No product no users just vibes and a 50 slide deck"}
            ],
            mix: [
                {label: "GYM KA TOURIST", topic: "Gym Bros", roast: "Protein shake peeta hai daily, gym jaata hai yearly"},
                {label: "COPY PASTE DEV", topic: "Engineers", roast: "Resume pe 10 skills, actually sirf Googling aati hai"},
                {label: "MONDAY SYNDROME", topic: "Monday", roast: "Friday ko party, Monday ko 'I have a headache' message"},
                {label: "INSTA FAMOUS", topic: "Influencers", roast: "Followers fake hai, engagement fake hai, bas ego real hai"},
                {label: "STARTUP BRO", topic: "Startups", roast: "Idea copied, team nahi hai, but Shark Tank ka sapna hai"}
            ]
        };
        
        const loadingMsgs = {
            hindi: ["Roast pak raha hai...", "Sach nikal raha hai...", "Brutal mode on...", "Thoda ruk, mast aayega..."],
            english: ["Cooking your roast...", "Finding the truth...", "Brutal mode on...", "Wait, it'll be fire..."],
            mix: ["Roast ban raha hai...", "Sach with spice...", "Loading brutal truth...", "Aane wala hai mast..."]
        };
        
        // Rotate examples
        function rotateExample() {
            const ex = examples[currentLang];
            exampleIndex = (exampleIndex + 1) % ex.length;
            const current = ex[exampleIndex];
            
            const card = document.getElementById('exampleCard');
            card.style.opacity = '0';
            card.style.transform = 'scale(0.9)';
            
            setTimeout(() => {
                document.getElementById('exampleLabel').textContent = current.label;
                document.getElementById('exampleTopic').textContent = current.topic;
                document.getElementById('exampleRoast').textContent = '"' + current.roast + '"';
                card.style.opacity = '0.6';
                card.style.transform = 'scale(0.95)';
            }, 300);
        }
        setInterval(rotateExample, 4000);
        
        // Update counter
        async function updateCounter() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('liveCount').textContent = data.total_roasts.toLocaleString();
            } catch(e) {}
        }
        updateCounter();
        setInterval(() => {
            const el = document.getElementById('liveCount');
            let n = parseInt(el.textContent.replace(/,/g, '')) || 52341;
            el.textContent = (n + Math.floor(Math.random() * 2)).toLocaleString();
        }, 5000);
        
        // Language
        function setLang(lang) {
            currentLang = lang;
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(lang + 'Btn').classList.add('active');
            
            const placeholders = {
                hindi: "Kisko roast karein?",
                english: "Who to roast?",
                mix: "Kisko roast karna hai?"
            };
            document.getElementById('topicInput').placeholder = placeholders[lang];
            
            const btnTexts = {
                hindi: "ROAST KARO",
                english: "ROAST NOW",
                mix: "ROAST KARO"
            };
            document.getElementById('btnText').textContent = btnTexts[lang];
            
            exampleIndex = -1;
            rotateExample();
        }
        
        // Use topic
        function useTopic(topic) {
            document.getElementById('topicInput').value = topic;
            document.getElementById('topicInput').focus();
        }
        
        // Enter key
        document.getElementById('topicInput').addEventListener('keypress', e => {
            if (e.key === 'Enter') generateRoast();
        });
        
        // Generate roast
        async function generateRoast() {
            const topic = document.getElementById('topicInput').value.trim();
            if (!topic) {
                document.getElementById('topicInput').style.borderColor = '#ff0000';
                setTimeout(() => {
                    document.getElementById('topicInput').style.borderColor = 'transparent';
                }, 1000);
                return;
            }
            
            currentTopic = topic;
            
            // Show loading
            document.getElementById('heroSection').classList.add('hidden');
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('loadingSection').classList.add('active');
            document.getElementById('trendingBar').classList.add('hidden');
            
            // Rotate loading messages
            const msgs = loadingMsgs[currentLang];
            let i = 0;
            const interval = setInterval(() => {
                document.getElementById('loadingText').textContent = msgs[++i % msgs.length];
            }, 1200);
            
            try {
                const res = await fetch('/roast?topic=' + encodeURIComponent(topic) + '&lang=' + currentLang);
                clearInterval(interval);
                
                if (!res.ok) throw new Error('Failed');
                
                const blob = await res.blob();
                currentImg = URL.createObjectURL(blob);
                
                document.getElementById('resultImage').src = currentImg;
                document.getElementById('resultTopic').textContent = 'Topic: ' + topic;
                
                document.getElementById('loadingSection').classList.remove('active');
                document.getElementById('resultSection').classList.add('active');
                
                updateCounter();
            } catch(e) {
                clearInterval(interval);
                alert('Error! Try again.');
                newRoast();
            }
        }
        
        // New roast
        function newRoast() {
            document.getElementById('loadingSection').classList.remove('active');
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('heroSection').classList.remove('hidden');
            document.getElementById('trendingBar').classList.remove('hidden');
            document.getElementById('topicInput').value = '';
            document.getElementById('topicInput').focus();
            currentImg = '';
        }
        
        // Download
        function downloadImage() {
            if (currentImg) {
                const a = document.createElement('a');
                a.href = currentImg;
                a.download = 'roast_' + Date.now() + '.jpg';
                a.click();
            }
        }
        
        // Share
        function shareWhatsApp() {
            const text = 'Check out this roast! 🔥 ' + window.location.href;
            window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank');
        }
        
        function shareTwitter() {
            const text = 'Just got roasted! 🔥 ' + window.location.href;
            window.open('https://twitter.com/intent/tweet?text=' + encodeURIComponent(text), '_blank');
        }
        
        function copyLink() {
            navigator.clipboard.writeText(window.location.href);
            alert('Link copied!');
        }
    </script>
</body>
</html>"""


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
        if font.getbbox(test)[2] <= max_w: line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def add_text_to_image(img_path, label, roast):
    img = Image.open(img_path)
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    # Simple clean border
    for i in range(5):
        draw.rectangle([i, i, w-1-i, h-1-i], outline="#FF6B35")
    
    # Label at top
    lf = get_font(int(h * 0.065))
    lt = label.upper()
    lb = lf.getbbox(lt)
    lx = (w - lb[2]) // 2
    
    # Label background
    padding = 10
    draw.rectangle([lx - padding, 15, lx + lb[2] + padding, 20 + lb[3] + padding], fill="#FF6B35")
    draw.text((lx, 18), lt, font=lf, fill="#000000")
    
    # Roast at bottom
    rf = get_font(int(h * 0.048))
    lines = wrap_text(roast, rf, int(w * 0.9))
    lh = int(h * 0.05) + 8
    y = h - len(lines) * lh - 20
    
    for line in lines:
        lb = rf.getbbox(line)
        x = (w - lb[2]) // 2
        # Shadow
        for dx in range(-2,3):
            for dy in range(-2,3):
                draw.text((x+dx, y+dy), line, font=rf, fill="#000000")
        draw.text((x, y), line, font=rf, fill="#FFFFFF")
        y += lh
    
    return img


# ===== NATURAL ROAST AI =====
def get_roast(topic, language='hindi'):
    # Get real-time context if available
    context = ""
    if SEARCH_ENABLED:
        try:
            data = get_smart_context(topic, language)
            context = data.get('topic_info', '')[:400]
        except:
            context = ""
    
    # Simple natural prompt - like a bro talking to bro
    if language == 'hindi':
        prompt = f"""Tu India ka sabse brutal roaster hai. Tera kaam hai sirf roast karna - no filter, no mercy.

Tu ek bhai ki tarah naturally baat karta hai. Forced funny nahi, natural savage.

{f'CURRENT INFO: {context}' if context else ''}

Topic: {topic}

Rules:
- LABEL: 2 words max, funny Hindi/Hinglish title (like "PROTEIN PAKODA", "CTRL+C CODER")
- ROAST: 10-18 words, natural language, brutal but relatable
- Use current references if available
- Be creative, different every time
- Talk like a friend roasting friend
- No emojis, no hashtags

Format:
LABEL: [2 word title]
ROAST: [brutal one-liner]"""

    elif language == 'english':
        prompt = f"""You're India's most brutal roaster. Your job is to roast - no filter, no mercy.

You talk naturally like a bro. Not forced funny, just natural savage.

{f'CURRENT INFO: {context}' if context else ''}

Topic: {topic}

Rules:
- LABEL: 2 words max, funny title (like "PROTEIN CLOWN", "COPY PASTE DEV")  
- ROAST: 10-18 words, natural, brutal but relatable
- Use current references if available
- Be creative, different every time
- Talk like a friend roasting friend
- No emojis, no hashtags

Format:
LABEL: [2 word title]
ROAST: [brutal one-liner]"""

    else:  # mix
        prompt = f"""Tu India ka sabse brutal roaster hai. Hinglish mein baat kar - Hindi + English mix.

Natural bhai jaisa bol. Forced nahi, natural savage.

{f'CURRENT INFO: {context}' if context else ''}

Topic: {topic}

Rules:
- LABEL: 2 words max, funny Hinglish title
- ROAST: 10-18 words, Hinglish, brutal but relatable
- Use current references if available
- Be creative har baar different
- Bhai jaisa roast kar
- No emojis, no hashtags

Format:
LABEL: [2 word title]
ROAST: [brutal one-liner]"""

    # Try AI models
    for model in AI_MODELS:
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                temperature=1.4,  # High creativity
                max_tokens=100
            )
            text = res.choices[0].message.content.strip()
            
            label, roast = "", ""
            for line in text.split('\n'):
                line = line.strip()
                if line.upper().startswith('LABEL:'):
                    label = line.split(':', 1)[1].strip().strip('"\'*').upper()
                elif line.upper().startswith('ROAST:'):
                    roast = line.split(':', 1)[1].strip().strip('"\'*')
            
            # Fallbacks
            if not label:
                labels = {
                    'hindi': ["CERTIFIED NALLA", "VELA SUPREME", "BAKCHOD PRO"],
                    'english': ["CERTIFIED CLOWN", "PRO FAILURE", "EXPERT LOSER"],
                    'mix': ["CERTIFIED CHUTIYA", "PRO VELA", "BAKCHOD KING"]
                }
                label = random.choice(labels.get(language, labels['hindi']))
            
            if not roast or len(roast) < 10:
                roast = text.replace('*', '').strip()[:100] if text else "Tujhe roast karne layak content hi nahi hai"
            
            return label, roast
            
        except Exception as e:
            print(f"Model failed: {e}")
            continue
    
    # Ultimate fallback
    fallbacks = {
        'hindi': ("BACKUP ROAST", "AI bhi thak gaya tujhe roast karte karte"),
        'english': ("BACKUP ROAST", "Even AI got tired roasting you"),
        'mix': ("BACKUP ROAST", "AI bhi give up kar diya tere pe")
    }
    return fallbacks.get(language, fallbacks['hindi'])


# ===== ROUTES =====
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def stats():
    return jsonify({"total_roasts": get_total_roasts(), "success": True})

@app.route('/api/examples')
def get_examples():
    lang = request.args.get('lang', 'hindi')
    return jsonify({"success": True, "examples": EXAMPLE_ROASTS.get(lang, EXAMPLE_ROASTS['hindi'])})

@app.route('/roast')
def roast():
    topic = request.args.get('topic', '').strip()
    lang = request.args.get('lang', 'hindi')
    
    if not topic:
        return jsonify({"error": "No topic"}), 400
    
    if not os.path.exists(MEMES_FOLDER):
        os.makedirs(MEMES_FOLDER)
        return jsonify({"error": "No memes"}), 500
    
    memes = [f for f in os.listdir(MEMES_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not memes:
        return jsonify({"error": "No meme images"}), 500
    
    try:
        label, roast_text = get_roast(topic, lang)
        img = add_text_to_image(os.path.join(MEMES_FOLDER, random.choice(memes)), label, roast_text)
        
        buf = BytesIO()
        img.save(buf, 'JPEG', quality=95)
        buf.seek(0)
        
        save_roast(topic, label, roast_text, lang)
        
        return send_file(BytesIO(buf.getvalue()), mimetype='image/jpeg')
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "search": SEARCH_ENABLED})

if __name__ == '__main__':
    os.makedirs(MEMES_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
