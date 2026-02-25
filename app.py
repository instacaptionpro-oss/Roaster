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

# ===== CLEAN UI WITH YOUR COLORS =====
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
            --bg-main: #0A0A0A;
            --bg-input: #2C2C2E;
            --bg-card: #1C1C1E;
            --text-primary: #FFFFFF;
            --text-placeholder: #8E8E93;
            --accent-red: #FF3B30;
            --accent-orange: #FF9500;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-main);
            color: var(--text-primary);
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
            background: rgba(10,10,10,0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,59,48,0.2);
        }
        
        .logo {
            font-size: 1.3rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--accent-red), var(--accent-orange));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .live-count {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
            color: var(--text-placeholder);
        }
        
        .live-dot {
            width: 8px;
            height: 8px;
            background: #30D158;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(48,209,88,0.4); }
            50% { opacity: 0.8; box-shadow: 0 0 0 8px rgba(48,209,88,0); }
        }
        
        .count-num {
            color: var(--accent-orange);
            font-weight: 700;
        }
        
        /* ===== HERO ===== */
        .hero {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 100px 20px 140px;
        }
        
        /* Example Card */
        .example-card {
            width: 100%;
            max-width: 400px;
            background: var(--bg-card);
            border: 2px solid var(--accent-red);
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 40px;
            opacity: 0.7;
            transition: all 0.4s ease;
            box-shadow: 0 0 30px rgba(255,59,48,0.15);
        }
        
        .example-card:hover {
            opacity: 1;
            box-shadow: 0 0 40px rgba(255,59,48,0.3);
        }
        
        .example-label {
            display: inline-block;
            background: linear-gradient(135deg, var(--accent-red), var(--accent-orange));
            color: #000;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }
        
        .example-topic {
            font-size: 0.75rem;
            color: var(--text-placeholder);
            margin-bottom: 8px;
        }
        
        .example-roast {
            font-size: 1.05rem;
            font-weight: 600;
            line-height: 1.5;
            color: var(--text-primary);
        }
        
        .example-hint {
            text-align: center;
            font-size: 0.7rem;
            color: var(--text-placeholder);
            margin-top: 14px;
        }
        
        /* Input Section */
        .input-section {
            width: 100%;
            max-width: 480px;
        }
        
        .main-input {
            width: 100%;
            padding: 18px 22px;
            font-size: 1.1rem;
            font-family: inherit;
            background: var(--bg-input);
            border: 2px solid var(--accent-red);
            border-radius: 14px;
            color: var(--text-primary);
            outline: none;
            transition: all 0.3s;
            margin-bottom: 14px;
        }
        
        .main-input:focus {
            box-shadow: 0 0 25px rgba(255,59,48,0.3);
        }
        
        .main-input::placeholder {
            color: var(--text-placeholder);
        }
        
        /* Language Toggle */
        .lang-toggle {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-bottom: 14px;
        }
        
        .lang-btn {
            padding: 8px 18px;
            font-size: 0.8rem;
            font-weight: 600;
            font-family: inherit;
            background: transparent;
            border: 1.5px solid var(--bg-input);
            border-radius: 8px;
            color: var(--text-placeholder);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .lang-btn.active {
            background: linear-gradient(135deg, var(--accent-red), var(--accent-orange));
            border-color: transparent;
            color: #000;
        }
        
        .lang-btn:hover:not(.active) {
            border-color: var(--accent-red);
            color: var(--text-primary);
        }
        
        /* Main Button */
        .roast-btn {
            width: 100%;
            padding: 18px;
            font-size: 1.15rem;
            font-weight: 800;
            font-family: inherit;
            background: linear-gradient(135deg, var(--accent-red), var(--accent-orange));
            border: none;
            border-radius: 14px;
            color: #000;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .roast-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(255,59,48,0.4);
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
            font-family: inherit;
            background: var(--bg-input);
            border: none;
            border-radius: 8px;
            color: var(--text-placeholder);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .chip:hover {
            background: var(--accent-red);
            color: #000;
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
            width: 50px;
            height: 50px;
            border: 3px solid var(--bg-input);
            border-top-color: var(--accent-red);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-bottom: 20px;
        }
        
        @keyframes spin {
            100% { transform: rotate(360deg); }
        }
        
        .loading-text {
            font-size: 0.95rem;
            color: var(--text-placeholder);
        }
        
        /* ===== RESULT ===== */
        .result-section {
            display: none;
            min-height: 100vh;
            flex-direction: column;
            align-items: center;
            padding: 90px 20px 50px;
        }
        
        .result-section.active {
            display: flex;
        }
        
        .result-topic {
            font-size: 0.8rem;
            color: var(--text-placeholder);
            margin-bottom: 16px;
        }
        
        .result-card {
            width: 100%;
            max-width: 420px;
            background: var(--bg-card);
            border: 2px solid var(--accent-red);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 24px;
            box-shadow: 0 0 40px rgba(255,59,48,0.25);
        }
        
        .result-image {
            width: 100%;
            display: block;
        }
        
        .primary-actions {
            display: flex;
            gap: 12px;
            width: 100%;
            max-width: 420px;
            margin-bottom: 16px;
        }
        
        .action-btn {
            flex: 1;
            padding: 14px;
            font-size: 0.95rem;
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
            background: var(--accent-red);
            color: var(--text-primary);
        }
        
        .btn-new {
            background: var(--bg-input);
            color: var(--text-primary);
            border: 2px solid var(--accent-red);
        }
        
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255,59,48,0.3);
        }
        
        .share-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .share-btn {
            padding: 10px 18px;
            font-size: 0.8rem;
            font-weight: 600;
            font-family: inherit;
            background: var(--bg-input);
            border: none;
            border-radius: 8px;
            color: var(--text-placeholder);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .share-btn:hover {
            background: var(--accent-red);
            color: var(--text-primary);
        }
        
        /* ===== TRENDING BAR ===== */
        .trending-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 100;
            padding: 14px 16px;
            background: rgba(10,10,10,0.95);
            backdrop-filter: blur(10px);
            border-top: 1px solid rgba(255,59,48,0.2);
            display: flex;
            align-items: center;
            gap: 12px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        
        .trending-bar::-webkit-scrollbar { display: none; }
        
        .trending-label {
            font-size: 0.75rem;
            color: var(--accent-red);
            font-weight: 700;
            white-space: nowrap;
        }
        
        .trending-chip {
            padding: 6px 14px;
            font-size: 0.75rem;
            font-family: inherit;
            background: var(--bg-input);
            border: none;
            border-radius: 6px;
            color: var(--text-primary);
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.3s;
        }
        
        .trending-chip:hover {
            background: var(--accent-red);
            color: #000;
        }
        
        /* ===== MOBILE ===== */
        @media (max-width: 500px) {
            .header { padding: 14px 18px; }
            .logo { font-size: 1.1rem; }
            .hero { padding: 80px 16px 120px; }
            .example-card { padding: 18px 20px; margin-bottom: 32px; }
            .example-roast { font-size: 1rem; }
            .main-input { padding: 16px 18px; font-size: 1rem; }
            .roast-btn { padding: 16px; font-size: 1rem; }
            .result-section { padding: 80px 16px 80px; }
            .primary-actions { flex-direction: column; }
        }
        
        .hidden { display: none !important; }
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
    
    <!-- HERO -->
    <section class="hero" id="heroSection">
        <div class="example-card" id="exampleCard">
            <div class="example-label" id="exampleLabel">PROTEIN PAKODA</div>
            <div class="example-topic" id="exampleTopic">Gym Wale</div>
            <div class="example-roast" id="exampleRoast">"Creatine ka dabba 2000 ka, body abhi bhi 2002 wali hai"</div>
            <div class="example-hint">↑ Ye tujhe bhi mil sakta hai</div>
        </div>
        
        <div class="input-section">
            <input type="text" class="main-input" id="topicInput" placeholder="Kisko roast karein?" maxlength="100" autofocus>
            
            <div class="lang-toggle">
                <button class="lang-btn active" id="hindiBtn" onclick="setLang('hindi')">हिंदी</button>
                <button class="lang-btn" id="englishBtn" onclick="setLang('english')">English</button>
                <button class="lang-btn" id="mixBtn" onclick="setLang('mix')">Mix</button>
            </div>
            
            <button class="roast-btn" id="roastBtn" onclick="generateRoast()">
                <span>🔥</span>
                <span id="btnText">Roast Karo</span>
            </button>
            
            <div class="quick-chips">
                <button class="chip" onclick="useTopic('Monday')">Monday</button>
                <button class="chip" onclick="useTopic('My Ex')">My Ex</button>
                <button class="chip" onclick="useTopic('Engineers')">Engineers</button>
                <button class="chip" onclick="useTopic('Gym')">Gym</button>
                <button class="chip" onclick="useTopic('Office')">Office</button>
            </div>
        </div>
    </section>
    
    <!-- LOADING -->
    <section class="loading-section" id="loadingSection">
        <div class="loader"></div>
        <div class="loading-text" id="loadingText">Roast ban raha hai...</div>
    </section>
    
    <!-- RESULT -->
    <section class="result-section" id="resultSection">
        <div class="result-topic" id="resultTopic">Topic: Monday</div>
        <div class="result-card">
            <img src="" alt="Roast" class="result-image" id="resultImage">
        </div>
        <div class="primary-actions">
            <button class="action-btn btn-save" onclick="downloadImage()">📥 Save</button>
            <button class="action-btn btn-new" onclick="newRoast()">🔄 New Roast</button>
        </div>
        <div class="share-actions">
            <button class="share-btn" onclick="shareWhatsApp()">WhatsApp</button>
            <button class="share-btn" onclick="shareTwitter()">Twitter</button>
            <button class="share-btn" onclick="copyLink()">Copy</button>
        </div>
    </section>
    
    <!-- TRENDING -->
    <div class="trending-bar" id="trendingBar">
        <span class="trending-label">🔥 Trending:</span>
        <button class="trending-chip" onclick="useTopic('IPL')">IPL</button>
        <button class="trending-chip" onclick="useTopic('AI')">AI</button>
        <button class="trending-chip" onclick="useTopic('Startup')">Startup</button>
        <button class="trending-chip" onclick="useTopic('Influencers')">Influencers</button>
        <button class="trending-chip" onclick="useTopic('Cricket')">Cricket</button>
        <button class="trending-chip" onclick="useTopic('Dating')">Dating</button>
    </div>

    <script>
        let currentLang = 'hindi';
        let currentImg = '';
        let exampleIdx = 0;
        
        const examples = {
            hindi: [
                {label: "PROTEIN PAKODA", topic: "Gym Wale", roast: "Creatine ka dabba 2000 ka, body abhi bhi 2002 wali hai"},
                {label: "CTRL+C CODER", topic: "Engineers", roast: "Stack Overflow band ho jaye toh inki salary bhi band"},
                {label: "SOMVAR VICTIM", topic: "Monday", roast: "Alarm 6 ka, utha 9 baje, blame kiya traffic ko"}
            ],
            english: [
                {label: "PROTEIN CLOWN", topic: "Gym Bros", roast: "Spent more on supplements than actual workouts"},
                {label: "COPY PASTE DEV", topic: "Engineers", roast: "If Stack Overflow dies, half the tech industry dies"},
                {label: "MONDAY HATER", topic: "Monday", roast: "Sets 5 alarms, still blames traffic for being late"}
            ],
            mix: [
                {label: "GYM TOURIST", topic: "Gym Bros", roast: "Protein daily peeta hai, gym yearly jaata hai"},
                {label: "COPY PASTE DEV", topic: "Engineers", roast: "Resume pe 10 skills, actually sirf Googling aati hai"},
                {label: "MONDAY SYNDROME", topic: "Monday", roast: "Friday party, Monday 'headache' message"}
            ]
        };
        
        const loadingMsgs = {
            hindi: ["Roast pak raha hai...", "Sach nikal raha hai...", "Thoda ruk..."],
            english: ["Cooking roast...", "Finding truth...", "Wait for it..."],
            mix: ["Roast ban raha...", "Truth loading...", "Almost ready..."]
        };
        
        function rotateExample() {
            const ex = examples[currentLang];
            exampleIdx = (exampleIdx + 1) % ex.length;
            const c = ex[exampleIdx];
            
            const card = document.getElementById('exampleCard');
            card.style.opacity = '0.3';
            
            setTimeout(() => {
                document.getElementById('exampleLabel').textContent = c.label;
                document.getElementById('exampleTopic').textContent = c.topic;
                document.getElementById('exampleRoast').textContent = '"' + c.roast + '"';
                card.style.opacity = '0.7';
            }, 200);
        }
        setInterval(rotateExample, 4000);
        
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
        
        function setLang(lang) {
            currentLang = lang;
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(lang + 'Btn').classList.add('active');
            
            const ph = {hindi: "Kisko roast karein?", english: "Who to roast?", mix: "Kisko roast karna hai?"};
            document.getElementById('topicInput').placeholder = ph[lang];
            
            const btn = {hindi: "Roast Karo", english: "Roast Now", mix: "Roast Karo"};
            document.getElementById('btnText').textContent = btn[lang];
            
            exampleIdx = -1;
            rotateExample();
        }
        
        function useTopic(t) {
            document.getElementById('topicInput').value = t;
            document.getElementById('topicInput').focus();
        }
        
        document.getElementById('topicInput').addEventListener('keypress', e => {
            if (e.key === 'Enter') generateRoast();
        });
        
        async function generateRoast() {
            const topic = document.getElementById('topicInput').value.trim();
            if (!topic) {
                document.getElementById('topicInput').style.boxShadow = '0 0 20px rgba(255,59,48,0.6)';
                setTimeout(() => document.getElementById('topicInput').style.boxShadow = '', 500);
                return;
            }
            
            document.getElementById('heroSection').classList.add('hidden');
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('loadingSection').classList.add('active');
            document.getElementById('trendingBar').classList.add('hidden');
            
            const msgs = loadingMsgs[currentLang];
            let i = 0;
            const interval = setInterval(() => {
                document.getElementById('loadingText').textContent = msgs[++i % msgs.length];
            }, 1000);
            
            try {
                const res = await fetch('/roast?topic=' + encodeURIComponent(topic) + '&lang=' + currentLang);
                clearInterval(interval);
                
                if (!res.ok) throw new Error();
                
                const blob = await res.blob();
                currentImg = URL.createObjectURL(blob);
                
                document.getElementById('resultImage').src = currentImg;
                document.getElementById('resultTopic').textContent = 'Topic: ' + topic;
                document.getElementById('loadingSection').classList.remove('active');
                document.getElementById('resultSection').classList.add('active');
                
                updateCounter();
            } catch(e) {
                clearInterval(interval);
                alert('Error! Try again');
                newRoast();
            }
        }
        
        function newRoast() {
            document.getElementById('loadingSection').classList.remove('active');
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('heroSection').classList.remove('hidden');
            document.getElementById('trendingBar').classList.remove('hidden');
            document.getElementById('topicInput').value = '';
            document.getElementById('topicInput').focus();
            currentImg = '';
        }
        
        function downloadImage() {
            if (currentImg) {
                const a = document.createElement('a');
                a.href = currentImg;
                a.download = 'roast_' + Date.now() + '.jpg';
                a.click();
            }
        }
        
        function shareWhatsApp() {
            window.open('https://wa.me/?text=' + encodeURIComponent('Check this roast! 🔥 ' + location.href), '_blank');
        }
        
        function shareTwitter() {
            window.open('https://twitter.com/intent/tweet?text=' + encodeURIComponent('Got roasted! 🔥 ' + location.href), '_blank');
        }
        
        function copyLink() {
            navigator.clipboard.writeText(location.href);
            alert('Link copied!');
        }
    </script>
</body>
</html>"""


# ===== IMAGE FUNCTIONS =====
def get_font(size=40):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arial.ttf"]
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
    
    # Red border
    for i in range(4):
        draw.rectangle([i, i, w-1-i, h-1-i], outline="#FF3B30")
    
    # Label
    lf = get_font(int(h * 0.06))
    lt = label.upper()
    lb = lf.getbbox(lt)
    lx = (w - lb[2]) // 2
    
    draw.rectangle([lx-12, 12, lx+lb[2]+12, 18+lb[3]+8], fill="#FF3B30")
    draw.text((lx, 15), lt, font=lf, fill="#000000")
    
    # Roast
    rf = get_font(int(h * 0.045))
    lines = wrap_text(roast, rf, int(w * 0.9))
    lh = int(h * 0.048) + 6
    y = h - len(lines) * lh - 18
    
    for line in lines:
        lb = rf.getbbox(line)
        x = (w - lb[2]) // 2
        for dx in range(-2,3):
            for dy in range(-2,3):
                draw.text((x+dx, y+dy), line, font=rf, fill="#000000")
        draw.text((x, y), line, font=rf, fill="#FFFFFF")
        y += lh
    
    return img


# ===== AI ROAST =====
def get_roast(topic, language='hindi'):
    context = ""
    if SEARCH_ENABLED:
        try:
            from search import get_smart_context
            data = get_smart_context(topic, language)
            context = data.get('topic_info', '')[:400]
        except: pass
    
    prompts = {
        'hindi': f"""Tu India ka sabse brutal roaster hai. Natural bhai jaisa bol.

{f'Context: {context}' if context else ''}

Topic: {topic}

LABEL: 2 word funny title
ROAST: 10-18 words, brutal, natural Hindi""",
        
        'english': f"""You're a brutal roaster. Talk natural like a bro.

{f'Context: {context}' if context else ''}

Topic: {topic}

LABEL: 2 word funny title
ROAST: 10-18 words, brutal, natural English""",
        
        'mix': f"""Tu brutal roaster hai. Hinglish mein bol.

{f'Context: {context}' if context else ''}

Topic: {topic}

LABEL: 2 word funny title
ROAST: 10-18 words, brutal, Hinglish"""
    }
    
    for model in AI_MODELS:
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompts.get(language, prompts['hindi'])}],
                model=model, temperature=1.4, max_tokens=80
            )
            text = res.choices[0].message.content.strip()
            
            label, roast = "", ""
            for line in text.split('\n'):
                if 'LABEL:' in line.upper():
                    label = line.split(':', 1)[1].strip().strip('"*').upper()
                elif 'ROAST:' in line.upper():
                    roast = line.split(':', 1)[1].strip().strip('"*')
            
            if not label: label = "CERTIFIED ROAST"
            if not roast: roast = text[:80].replace('*','')
            
            return label, roast
        except: continue
    
    return ("BACKUP ROAST", "AI thak gaya tujhe roast karte karte")


# ===== ROUTES =====
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def stats():
    return jsonify({"total_roasts": get_total_roasts()})

@app.route('/roast')
def roast():
    topic = request.args.get('topic', '').strip()
    lang = request.args.get('lang', 'hindi')
    
    if not topic: return jsonify({"error": "No topic"}), 400
    
    memes = [f for f in os.listdir(MEMES_FOLDER) if f.endswith(('.jpg','.jpeg','.png'))] if os.path.exists(MEMES_FOLDER) else []
    if not memes: return jsonify({"error": "No memes"}), 500
    
    try:
        label, roast_text = get_roast(topic, lang)
        img = add_text_to_image(os.path.join(MEMES_FOLDER, random.choice(memes)), label, roast_text)
        
        buf = BytesIO()
        img.save(buf, 'JPEG', quality=95)
        buf.seek(0)
        
        save_roast(topic, label, roast_text, lang)
        return send_file(BytesIO(buf.getvalue()), mimetype='image/jpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    os.makedirs(MEMES_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
