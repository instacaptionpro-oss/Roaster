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

# Import search module
try:
    from search import get_smart_context, get_india_trending, get_global_trending
    SEARCH_ENABLED = True
    print("✅ Real-time search enabled")
except:
    SEARCH_ENABLED = False
    print("⚠️ Search module not found - using basic mode")

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ===== DATABASE =====
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://roast_db_c13t_user:9PO09Y3SpZ6z5r0eYszLsYGHg0bcYtXx@dpg-d5ubdo24d50c73d1bmdg-a/roast_db_c13t")

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
                id SERIAL PRIMARY KEY,
                topic VARCHAR(255),
                identity_label VARCHAR(100),
                roast_text TEXT,
                language VARCHAR(20) DEFAULT 'hindi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS stats (
                id SERIAL PRIMARY KEY,
                total_roasts INTEGER DEFAULT 0
            )''')
            cur.execute('SELECT COUNT(*) as c FROM stats')
            if cur.fetchone()['c'] == 0:
                cur.execute('INSERT INTO stats (total_roasts) VALUES (47892)')
            conn.commit()
        except: pass
        finally: conn.close()

init_database()

# Supabase (optional)
supabase = None
try:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")
    if url and key:
        supabase = create_client(url, key)
except: pass

MEMES_FOLDER = "memes"
AI_MODELS = ["llama-3.3-70b-versatile", "qwen/qwen-2.5-72b-instruct", "meta-llama/llama-3.1-70b-versatile"]

def get_daily_topic(language='hindi'):
    try:
        with open('daily_topic.json', 'r', encoding='utf-8') as f:
            return json.load(f).get(language)
    except:
        return {"topic": "Gym People", "label": "Gym Tourist", "description": "Selfie > Workout"}

# ===== POWERFUL FRONTEND =====
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ROASTER - India's #1 Brutal Truth Machine</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a0a0a 50%, #0a0a0a 100%);
            color: #fff;
            overflow-x: hidden;
        }
        
        /* Animated background particles */
        .bg-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            background-image: 
                radial-gradient(circle at 20% 80%, rgba(255,69,0,0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255,0,0,0.1) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(255,100,0,0.05) 0%, transparent 70%);
        }
        
        .navbar {
            position: relative;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            background: rgba(0,0,0,0.8);
            border-bottom: 2px solid #FF4500;
        }
        
        .nav-brand {
            font-size: 1.8rem;
            font-weight: 900;
            background: linear-gradient(90deg, #FF4500, #FF6B35, #FF4500);
            background-size: 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: brandGlow 3s infinite;
        }
        
        @keyframes brandGlow {
            0%, 100% { background-position: 0% 50%; filter: drop-shadow(0 0 10px #FF4500); }
            50% { background-position: 100% 50%; filter: drop-shadow(0 0 20px #FF4500); }
        }
        
        .live-counter {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 16px;
            background: rgba(255,69,0,0.2);
            border: 1px solid #FF4500;
            border-radius: 50px;
        }
        
        .live-dot {
            width: 10px;
            height: 10px;
            background: #00ff00;
            border-radius: 50%;
            animation: livePulse 1s infinite;
        }
        
        @keyframes livePulse {
            0%, 100% { box-shadow: 0 0 5px #00ff00; }
            50% { box-shadow: 0 0 20px #00ff00, 0 0 30px #00ff00; }
        }
        
        .counter-number {
            font-weight: 900;
            font-size: 1.1rem;
            color: #FF4500;
        }
        
        .container {
            position: relative;
            z-index: 10;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 24px;
        }
        
        /* ===== HERO SECTION - POWERFUL WORDS ===== */
        .hero-section {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .hero-tagline {
            display: inline-block;
            padding: 8px 24px;
            background: linear-gradient(90deg, rgba(255,69,0,0.3), rgba(255,0,0,0.3));
            border: 1px solid rgba(255,69,0,0.5);
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 700;
            color: #FF6B35;
            margin-bottom: 20px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        
        .hero-title {
            font-size: clamp(2.5rem, 8vw, 4.5rem);
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: 16px;
            letter-spacing: -2px;
        }
        
        .hero-title .highlight {
            background: linear-gradient(90deg, #FF4500, #FF0000, #FF4500);
            background-size: 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: textShine 3s infinite;
        }
        
        @keyframes textShine {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .hero-subtitle {
            font-size: 1.2rem;
            color: rgba(255,255,255,0.7);
            max-width: 600px;
            margin: 0 auto 16px;
            line-height: 1.6;
        }
        
        /* POWERFUL FEATURE BADGES */
        .feature-badges {
            display: flex;
            justify-content: center;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 24px;
        }
        
        .feature-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 600;
            color: rgba(255,255,255,0.8);
        }
        
        .feature-badge .icon {
            font-size: 1rem;
        }
        
        /* ===== RGB HOT TOPIC ===== */
        .hot-topic-section {
            margin-bottom: 40px;
        }
        
        .hot-topic-banner {
            position: relative;
            background: #0a0a0a;
            border-radius: 20px;
            padding: 28px 32px;
            cursor: pointer;
            transition: transform 0.3s;
            overflow: hidden;
        }
        
        .hot-topic-banner::before {
            content: '';
            position: absolute;
            top: -4px; left: -4px; right: -4px; bottom: -4px;
            background: linear-gradient(45deg, 
                #ff0000, #ff7300, #fffb00, #48ff00, 
                #00ffd5, #002bff, #7a00ff, #ff00c8, #ff0000);
            background-size: 400%;
            border-radius: 24px;
            z-index: -1;
            animation: rgbRotate 4s linear infinite;
        }
        
        .hot-topic-banner::after {
            content: '';
            position: absolute;
            top: -4px; left: -4px; right: -4px; bottom: -4px;
            background: linear-gradient(45deg, 
                #ff0000, #ff7300, #fffb00, #48ff00, 
                #00ffd5, #002bff, #7a00ff, #ff00c8, #ff0000);
            background-size: 400%;
            border-radius: 24px;
            z-index: -2;
            filter: blur(30px);
            opacity: 0.6;
            animation: rgbRotate 4s linear infinite;
        }
        
        @keyframes rgbRotate {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .hot-topic-banner:hover {
            transform: scale(1.02);
        }
        
        .hot-label-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 14px;
        }
        
        .fire-emoji {
            font-size: 1.6rem;
            animation: fireShake 0.4s infinite alternate;
        }
        
        @keyframes fireShake {
            0% { transform: rotate(-8deg) scale(1); }
            100% { transform: rotate(8deg) scale(1.1); }
        }
        
        .hot-label {
            font-size: 0.75rem;
            font-weight: 900;
            letter-spacing: 4px;
            text-transform: uppercase;
            background: linear-gradient(90deg, #FF4500, #FFD700, #FF4500);
            background-size: 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: textShine 2s infinite;
        }
        
        .hot-topic-title {
            font-size: 1.8rem;
            font-weight: 900;
            color: #fff;
            margin-bottom: 8px;
            text-shadow: 0 0 30px rgba(255,255,255,0.3);
        }
        
        .hot-topic-desc {
            font-size: 1rem;
            color: rgba(255,255,255,0.7);
        }
        
        .tap-hint {
            margin-top: 16px;
            font-size: 0.8rem;
            font-weight: 700;
            color: #00ff88;
            animation: tapPulse 1.5s infinite;
        }
        
        @keyframes tapPulse {
            0%, 100% { opacity: 0.5; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.02); }
        }
        
        /* ===== WHAT WE DO SECTION ===== */
        .what-we-do {
            background: rgba(255,69,0,0.1);
            border: 1px solid rgba(255,69,0,0.3);
            border-radius: 20px;
            padding: 32px;
            margin-bottom: 40px;
            text-align: center;
        }
        
        .section-title {
            font-size: 1.4rem;
            font-weight: 800;
            margin-bottom: 20px;
            color: #FF4500;
        }
        
        .usp-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .usp-card {
            background: rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px 16px;
            text-align: center;
            transition: all 0.3s;
        }
        
        .usp-card:hover {
            border-color: #FF4500;
            transform: translateY(-4px);
        }
        
        .usp-icon {
            font-size: 2rem;
            margin-bottom: 12px;
        }
        
        .usp-title {
            font-size: 1rem;
            font-weight: 800;
            margin-bottom: 8px;
            color: #fff;
        }
        
        .usp-desc {
            font-size: 0.85rem;
            color: rgba(255,255,255,0.6);
            line-height: 1.4;
        }
        
        /* ===== INPUT SECTION ===== */
        .input-section {
            margin-bottom: 32px;
        }
        
        .language-toggle {
            display: flex;
            justify-content: center;
            gap: 0;
            margin-bottom: 20px;
            background: rgba(0,0,0,0.5);
            border-radius: 50px;
            padding: 4px;
            width: fit-content;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid rgba(255,69,0,0.3);
        }
        
        .lang-btn {
            padding: 10px 28px;
            font-size: 0.9rem;
            font-weight: 700;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s;
            background: transparent;
            color: rgba(255,255,255,0.5);
        }
        
        .lang-btn.active {
            background: #FF4500;
            color: #fff;
            box-shadow: 0 4px 20px rgba(255,69,0,0.5);
        }
        
        .input-box {
            max-width: 700px;
            margin: 0 auto;
        }
        
        .input-wrapper {
            display: flex;
            gap: 8px;
            background: rgba(0,0,0,0.6);
            border: 2px solid rgba(255,69,0,0.3);
            border-radius: 16px;
            padding: 6px;
            transition: all 0.3s;
        }
        
        .input-wrapper:focus-within {
            border-color: #FF4500;
            box-shadow: 0 0 30px rgba(255,69,0,0.3);
        }
        
        .topic-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            padding: 16px;
            font-size: 1.1rem;
            color: #fff;
            font-family: inherit;
        }
        
        .topic-input::placeholder {
            color: rgba(255,255,255,0.3);
        }
        
        .roast-btn {
            padding: 16px 32px;
            background: linear-gradient(135deg, #FF4500, #FF0000);
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 800;
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .roast-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 30px rgba(255,69,0,0.5);
        }
        
        .roast-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Quick picks */
        .quick-picks {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 8px;
            margin-top: 20px;
        }
        
        .quick-chip {
            padding: 8px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 600;
            color: rgba(255,255,255,0.7);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .quick-chip:hover {
            background: rgba(255,69,0,0.2);
            border-color: #FF4500;
            color: #fff;
        }
        
        /* ===== LOADING ===== */
        .loading-section {
            display: none;
            text-align: center;
            padding: 60px;
        }
        
        .loading-section.active {
            display: block;
        }
        
        .loader {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(255,69,0,0.2);
            border-top-color: #FF4500;
            border-radius: 50%;
            margin: 0 auto 20px;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            100% { transform: rotate(360deg); }
        }
        
        .loading-text {
            font-size: 1rem;
            color: #FF4500;
            font-weight: 600;
        }
        
        /* ===== RESULT ===== */
        .result-section {
            display: none;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .result-section.active {
            display: block;
            animation: slideUp 0.5s ease;
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(40px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .result-card {
            background: rgba(0,0,0,0.8);
            border: 3px solid #FF4500;
            border-radius: 24px;
            padding: 24px;
            box-shadow: 0 0 60px rgba(255,69,0,0.4);
        }
        
        .result-image {
            width: 100%;
            border-radius: 16px;
            margin-bottom: 20px;
        }
        
        .share-buttons {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        
        .share-btn {
            padding: 14px;
            border: none;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .share-btn:hover {
            transform: translateY(-3px);
        }
        
        .btn-whatsapp { background: #25D366; color: #fff; }
        .btn-insta { background: linear-gradient(45deg, #f09433, #dc2743, #bc1888); color: #fff; }
        .btn-download { background: #1e90ff; color: #fff; }
        .btn-again { background: transparent; border: 2px solid #FF4500; color: #FF4500; }
        
        .error-box {
            display: none;
            background: rgba(255,0,0,0.2);
            border: 1px solid #ff0000;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            margin: 20px auto;
            max-width: 500px;
        }
        
        .error-box.active { display: block; }
        
        /* TRUST SECTION */
        .trust-section {
            text-align: center;
            padding: 40px 20px;
            margin-top: 40px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .trust-title {
            font-size: 0.9rem;
            color: rgba(255,255,255,0.4);
            margin-bottom: 16px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        
        .trust-stats {
            display: flex;
            justify-content: center;
            gap: 40px;
            flex-wrap: wrap;
        }
        
        .trust-stat {
            text-align: center;
        }
        
        .trust-number {
            font-size: 2rem;
            font-weight: 900;
            color: #FF4500;
        }
        
        .trust-label {
            font-size: 0.8rem;
            color: rgba(255,255,255,0.5);
        }
        
        @media (max-width: 768px) {
            .navbar { padding: 16px 20px; }
            .nav-brand { font-size: 1.4rem; }
            .container { padding: 24px 16px; }
            .hero-title { font-size: 2rem; }
            .hot-topic-title { font-size: 1.4rem; }
            .usp-grid { grid-template-columns: 1fr 1fr; }
            .share-buttons { grid-template-columns: 1fr 1fr; }
            .trust-stats { gap: 24px; }
            .feature-badges { gap: 8px; }
        }
    </style>
</head>
<body>
    <div class="bg-particles"></div>
    
    <nav class="navbar">
        <div class="nav-brand">🔥 ROASTER</div>
        <div class="live-counter">
            <div class="live-dot"></div>
            <span class="counter-number" id="liveCounter">47,892</span>
            <span id="counterLabel">roasted</span>
        </div>
    </nav>
    
    <div class="container">
        
        <!-- HERO SECTION -->
        <section class="hero-section">
            <div class="hero-tagline" id="heroTagline">🇮🇳 INDIA'S #1 ROAST MACHINE</div>
            
            <h1 class="hero-title" id="heroTitle">
                <span id="titleLine1">Sach Sunne Ki</span><br>
                <span class="highlight" id="titleLine2">Himmat Hai?</span>
            </h1>
            
            <p class="hero-subtitle" id="heroSubtitle">
                Wo AI jo tere mooh pe sach bolega. Wo baat jo tera dost nahi bolega, hum bolenge. <strong>15-20 words mein teri poori reality.</strong>
            </p>
            
            <div class="feature-badges">
                <div class="feature-badge"><span class="icon">🔥</span><span id="badge1">100% Brutal</span></div>
                <div class="feature-badge"><span class="icon">🎯</span><span id="badge2">Real-Time Trends</span></div>
                <div class="feature-badge"><span class="icon">🤖</span><span id="badge3">AI-Powered</span></div>
                <div class="feature-badge"><span class="icon">😂</span><span id="badge4">Relatable AF</span></div>
            </div>
        </section>
        
        <!-- RGB HOT TOPIC -->
        <section class="hot-topic-section">
            <div class="hot-topic-banner" id="hotTopicBanner" onclick="useDailyTopic()">
                <div class="hot-label-row">
                    <span class="fire-emoji">🔥</span>
                    <span class="hot-label" id="hotLabel">TODAY'S VIRAL ROAST</span>
                    <span class="fire-emoji">🔥</span>
                </div>
                <div class="hot-topic-title" id="hotTopicTitle">Loading...</div>
                <div class="hot-topic-desc" id="hotTopicDesc">Tap to roast this trending topic</div>
                <div class="tap-hint">👆 TAP TO ROAST 👆</div>
            </div>
        </section>
        
        <!-- WHAT WE DO -->
        <section class="what-we-do">
            <h2 class="section-title" id="whatWeDoTitle">🎯 Hum Kya Karte Hain?</h2>
            <div class="usp-grid">
                <div class="usp-card">
                    <div class="usp-icon">🪞</div>
                    <div class="usp-title" id="usp1Title">Reality Mirror</div>
                    <div class="usp-desc" id="usp1Desc">Wo sach jo tu khud se chhupata hai, hum mooh pe bolte hain</div>
                </div>
                <div class="usp-card">
                    <div class="usp-icon">📈</div>
                    <div class="usp-title" id="usp2Title">Trend-Based</div>
                    <div class="usp-desc" id="usp2Desc">Latest news aur memes se connected roasts - always relevant</div>
                </div>
                <div class="usp-card">
                    <div class="usp-icon">🧠</div>
                    <div class="usp-title" id="usp3Title">Smart AI</div>
                    <div class="usp-desc" id="usp3Desc">15-20 words mein puri baat - na zyada, na kam</div>
                </div>
                <div class="usp-card">
                    <div class="usp-icon">💀</div>
                    <div class="usp-title" id="usp4Title">No Mercy</div>
                    <div class="usp-desc" id="usp4Desc">Emotional damage guaranteed - mummy kasam</div>
                </div>
            </div>
        </section>
        
        <!-- INPUT SECTION -->
        <section class="input-section">
            <div class="language-toggle">
                <button class="lang-btn active" id="hindiBtn" onclick="setLanguage('hindi')">🇮🇳 Hindi</button>
                <button class="lang-btn" id="englishBtn" onclick="setLanguage('english')">🇺🇸 English</button>
            </div>
            
            <div class="input-box">
                <div class="input-wrapper">
                    <input type="text" class="topic-input" id="topicInput" placeholder="Kiski leni hai aaj..." maxlength="100">
                    <button class="roast-btn" id="roastBtn" onclick="executeRoast()">
                        <span>🔥</span>
                        <span id="roastBtnText">ROAST</span>
                    </button>
                </div>
                
                <div class="quick-picks" id="quickPicks">
                    <button class="quick-chip" onclick="useExample('Gym wale')">💪 Gym</button>
                    <button class="quick-chip" onclick="useExample('Engineers')">💻 Engineers</button>
                    <button class="quick-chip" onclick="useExample('Startups')">🚀 Startups</button>
                    <button class="quick-chip" onclick="useExample('Influencers')">📱 Influencers</button>
                    <button class="quick-chip" onclick="useExample('Cricket fans')">🏏 Cricket</button>
                    <button class="quick-chip" onclick="useExample('Office wale')">👔 Office</button>
                </div>
            </div>
        </section>
        
        <!-- LOADING -->
        <section class="loading-section" id="loadingSection">
            <div class="loader"></div>
            <div class="loading-text" id="loadingText">Teri aukaat dhundh raha...</div>
        </section>
        
        <!-- RESULT -->
        <section class="result-section" id="resultSection">
            <div class="result-card">
                <img src="" alt="Roast" class="result-image" id="resultImage">
                <div class="share-buttons">
                    <button class="share-btn btn-whatsapp" onclick="shareWhatsApp()">📱 WhatsApp</button>
                    <button class="share-btn btn-insta" onclick="shareInsta()">📸 Instagram</button>
                    <button class="share-btn btn-download" onclick="downloadImage()">⬇️ Download</button>
                    <button class="share-btn btn-again" onclick="resetRoast()">🔄 Again</button>
                </div>
            </div>
        </section>
        
        <div class="error-box" id="errorBox"></div>
        
        <!-- TRUST SECTION -->
        <section class="trust-section">
            <div class="trust-title" id="trustTitle">Trusted by Thousands</div>
            <div class="trust-stats">
                <div class="trust-stat">
                    <div class="trust-number" id="statRoasts">47K+</div>
                    <div class="trust-label" id="statRoastsLabel">Roasts Generated</div>
                </div>
                <div class="trust-stat">
                    <div class="trust-number">4.8⭐</div>
                    <div class="trust-label" id="statRatingLabel">Savage Rating</div>
                </div>
                <div class="trust-stat">
                    <div class="trust-number">15s</div>
                    <div class="trust-label" id="statTimeLabel">Avg. Roast Time</div>
                </div>
            </div>
        </section>
    </div>

    <script>
        let currentLang = 'hindi';
        let currentImg = '';
        let dailyTopic = null;
        
        const loadingMsgsHindi = [
            "Teri aukaat dhundh raha...",
            "Real-time sach nikal raha...",
            "Trends check kar raha...",
            "Brutal roast pak raha...",
            "Sach kadwa hai, ready ho ja..."
        ];
        
        const loadingMsgsEnglish = [
            "Finding your level...",
            "Checking real-time trends...",
            "Cooking brutal truth...",
            "Preparing reality check...",
            "Truth hurts, get ready..."
        ];
        
        // Fetch stats
        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('liveCounter').textContent = data.total_roasts.toLocaleString();
                document.getElementById('statRoasts').textContent = Math.floor(data.total_roasts / 1000) + 'K+';
            } catch(e) {}
        }
        fetchStats();
        
        // Live counter animation
        setInterval(() => {
            const el = document.getElementById('liveCounter');
            let num = parseInt(el.textContent.replace(/,/g, '')) || 47892;
            el.textContent = (num + Math.floor(Math.random() * 3)).toLocaleString();
        }, 4000);
        
        // Fetch daily topic
        async function fetchDailyTopic() {
            try {
                const res = await fetch('/api/daily-topic?lang=' + currentLang);
                const data = await res.json();
                if (data.success) {
                    dailyTopic = data.data;
                    document.getElementById('hotTopicTitle').textContent = dailyTopic.topic;
                    document.getElementById('hotTopicDesc').textContent = dailyTopic.description;
                }
            } catch(e) {}
        }
        fetchDailyTopic();
        
        function useDailyTopic() {
            if (dailyTopic) {
                document.getElementById('topicInput').value = dailyTopic.topic;
                document.getElementById('hotTopicBanner').style.transform = 'scale(0.97)';
                setTimeout(() => {
                    document.getElementById('hotTopicBanner').style.transform = '';
                    executeRoast();
                }, 150);
            }
        }
        
        function setLanguage(lang) {
            currentLang = lang;
            document.getElementById('hindiBtn').classList.toggle('active', lang === 'hindi');
            document.getElementById('englishBtn').classList.toggle('active', lang === 'english');
            
            if (lang === 'hindi') {
                document.getElementById('heroTagline').textContent = "🇮🇳 INDIA'S #1 ROAST MACHINE";
                document.getElementById('titleLine1').textContent = "Sach Sunne Ki";
                document.getElementById('titleLine2').textContent = "Himmat Hai?";
                document.getElementById('heroSubtitle').innerHTML = "Wo AI jo tere mooh pe sach bolega. Wo baat jo tera dost nahi bolega, hum bolenge. <strong>15-20 words mein teri poori reality.</strong>";
                document.getElementById('topicInput').placeholder = "Kiski leni hai aaj...";
                document.getElementById('roastBtnText').textContent = "ROAST";
                document.getElementById('hotLabel').textContent = "AAJ KA VIRAL ROAST";
                document.getElementById('whatWeDoTitle').textContent = "🎯 Hum Kya Karte Hain?";
                document.getElementById('counterLabel').textContent = "bezati hui";
                document.getElementById('badge1').textContent = "100% Brutal";
                document.getElementById('badge2').textContent = "Real-Time";
                document.getElementById('badge3').textContent = "AI-Powered";
                document.getElementById('badge4').textContent = "Relatable";
                
                // USP Cards
                document.getElementById('usp1Title').textContent = "Reality Mirror";
                document.getElementById('usp1Desc').textContent = "Wo sach jo tu khud se chhupata hai, hum mooh pe bolte hain";
                document.getElementById('usp2Title').textContent = "Trend-Based";
                document.getElementById('usp2Desc').textContent = "Latest news aur memes se connected roasts";
                document.getElementById('usp3Title').textContent = "Smart AI";
                document.getElementById('usp3Desc').textContent = "15-20 words mein puri baat";
                document.getElementById('usp4Title').textContent = "No Mercy";
                document.getElementById('usp4Desc').textContent = "Emotional damage guaranteed";
                
                document.getElementById('trustTitle').textContent = "Logo Ka Bharosa";
                document.getElementById('statRoastsLabel').textContent = "Bezati Hui";
                document.getElementById('statRatingLabel').textContent = "Savage Rating";
                document.getElementById('statTimeLabel').textContent = "Roast Time";
            } else {
                document.getElementById('heroTagline').textContent = "🌍 #1 BRUTAL TRUTH MACHINE";
                document.getElementById('titleLine1').textContent = "Can You Handle";
                document.getElementById('titleLine2').textContent = "The Truth?";
                document.getElementById('heroSubtitle').innerHTML = "The AI that tells you what your friends won't. <strong>15-20 words of pure reality check.</strong>";
                document.getElementById('topicInput').placeholder = "Who needs a reality check...";
                document.getElementById('roastBtnText').textContent = "ROAST";
                document.getElementById('hotLabel').textContent = "TODAY'S VIRAL ROAST";
                document.getElementById('whatWeDoTitle').textContent = "🎯 What We Do?";
                document.getElementById('counterLabel').textContent = "roasted";
                document.getElementById('badge1').textContent = "100% Brutal";
                document.getElementById('badge2').textContent = "Real-Time";
                document.getElementById('badge3').textContent = "AI-Powered";
                document.getElementById('badge4').textContent = "Relatable";
                
                document.getElementById('usp1Title').textContent = "Reality Mirror";
                document.getElementById('usp1Desc').textContent = "The truth you hide from yourself, we say to your face";
                document.getElementById('usp2Title').textContent = "Trend-Based";
                document.getElementById('usp2Desc').textContent = "Connected to latest news and memes";
                document.getElementById('usp3Title').textContent = "Smart AI";
                document.getElementById('usp3Desc').textContent = "15-20 words, straight to the point";
                document.getElementById('usp4Title').textContent = "No Mercy";
                document.getElementById('usp4Desc').textContent = "Emotional damage guaranteed";
                
                document.getElementById('trustTitle').textContent = "Trusted Globally";
                document.getElementById('statRoastsLabel').textContent = "Roasts Generated";
                document.getElementById('statRatingLabel').textContent = "Savage Rating";
                document.getElementById('statTimeLabel').textContent = "Avg. Time";
            }
            
            fetchDailyTopic();
        }
        
        function useExample(topic) {
            document.getElementById('topicInput').value = topic;
        }
        
        document.getElementById('topicInput').addEventListener('keypress', e => {
            if (e.key === 'Enter') executeRoast();
        });
        
        async function executeRoast() {
            const topic = document.getElementById('topicInput').value.trim();
            if (!topic) {
                showError(currentLang === 'hindi' ? 'Abe kuch toh likh!' : 'Type something!');
                return;
            }
            
            // UI updates
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('errorBox').classList.remove('active');
            document.getElementById('loadingSection').classList.add('active');
            document.getElementById('roastBtn').disabled = true;
            
            // Loading messages
            const msgs = currentLang === 'hindi' ? loadingMsgsHindi : loadingMsgsEnglish;
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
                document.getElementById('loadingSection').classList.remove('active');
                document.getElementById('resultSection').classList.add('active');
                fetchStats();
            } catch(e) {
                clearInterval(interval);
                document.getElementById('loadingSection').classList.remove('active');
                showError(currentLang === 'hindi' ? 'Error! Dobara try kar' : 'Error! Try again');
            } finally {
                document.getElementById('roastBtn').disabled = false;
            }
        }
        
        function showError(msg) {
            const el = document.getElementById('errorBox');
            el.textContent = msg;
            el.classList.add('active');
        }
        
        function shareWhatsApp() {
            const text = currentLang === 'hindi' 
                ? 'Dekh meri bezati 🔥 ' + window.location.href 
                : 'Check my roast 🔥 ' + window.location.href;
            window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank');
        }
        
        function shareInsta() {
            downloadImage();
            alert(currentLang === 'hindi' ? 'Downloaded! Ab Insta pe daal' : 'Downloaded! Share on Insta');
        }
        
        function downloadImage() {
            if (currentImg) {
                const a = document.createElement('a');
                a.href = currentImg;
                a.download = 'roast_' + Date.now() + '.jpg';
                a.click();
            }
        }
        
        function resetRoast() {
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('topicInput').value = '';
            currentImg = '';
        }
    </script>
</body>
</html>"""


# ===== DATABASE FUNCTIONS =====
def save_roast_to_db(topic, label, roast, lang):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('INSERT INTO roasts (topic, identity_label, roast_text, language) VALUES (%s,%s,%s,%s)', (topic, label, roast, lang))
            cur.execute('UPDATE stats SET total_roasts = total_roasts + 1')
            conn.commit()
        except: pass
        finally: conn.close()

def get_total_roasts():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('SELECT total_roasts FROM stats WHERE id=1')
            r = cur.fetchone()
            return r['total_roasts'] if r else 47892
        except: return 47892
        finally: conn.close()
    return 47892


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
    
    # Border
    for i in range(6):
        c = "#FF4500" if i < 3 else "#8B0000"
        draw.rectangle([i, i, w-1-i, h-1-i], outline=c)
    
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
    lh = int(h * 0.05) + 10
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


# ===== AI ROAST WITH REAL-TIME SEARCH =====
def get_roast(topic, language='hindi'):
    # Get real-time context if available
    context = ""
    if SEARCH_ENABLED:
        try:
            data = get_smart_context(topic, language)
            context = data.get('topic_info', '')[:300]
        except:
            context = ""
    
    if language == 'hindi':
        prompt = f"""Tu India ka sabse savage roaster hai. 

REAL-TIME CONTEXT (use if relevant):
{context if context else 'No specific context'}

RULES:
- LABEL: 1-2 funny Hindi words
- ROAST: Exactly 15-20 words, relatable, spicy
- Use: bc, mc, chutiya, nalla, vela, bewkoof, gadha
- Make it TRENDING and CURRENT if context available
- 80% logo ko lage "ye toh main hoon"

FORMAT:
LABEL: [title]
ROAST: [15-20 word roast]

Topic: {topic}"""
    else:
        prompt = f"""You're the most savage roaster.

REAL-TIME CONTEXT (use if relevant):
{context if context else 'No specific context'}

RULES:
- LABEL: 1-2 funny words
- ROAST: Exactly 15-20 words, relatable, edgy
- Use current references if context available
- Make 80% people say "that's literally me"

FORMAT:
LABEL: [title]
ROAST: [15-20 word roast]

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
                if line.upper().startswith('LABEL:'): 
                    label = line.split(':',1)[1].strip().strip('"\'*')
                elif line.upper().startswith('ROAST:'): 
                    roast = line.split(':',1)[1].strip().strip('"\'*')
            
            if not label: label = "Certified Nalla" if language == 'hindi' else "Certified Clown"
            if not roast or len(roast) < 10: roast = text[:100].replace('*','')
            
            return label, roast
        except Exception as e:
            print(f"Model failed: {e}")
            continue
    
    return ("Certified Nalla", "AI bhi thak gaya bc") if language == 'hindi' else ("Certified Clown", "Even AI gave up on you")


# ===== ROUTES =====
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def stats():
    return jsonify({"total_roasts": get_total_roasts(), "success": True})

@app.route('/api/daily-topic')
def daily_topic_api():
    return jsonify({"success": True, "data": get_daily_topic(request.args.get('lang', 'hindi'))})

@app.route('/api/trending')
def trending_api():
    """Get trending topics"""
    if SEARCH_ENABLED:
        try:
            lang = request.args.get('lang', 'hindi')
            topics = get_india_trending() if lang == 'hindi' else get_global_trending()
            return jsonify({"success": True, "topics": topics})
        except:
            pass
    return jsonify({"success": False, "topics": []})

@app.route('/roast')
def roast():
    topic = request.args.get('topic', '').strip()
    lang = request.args.get('lang', 'hindi')
    
    if not topic: 
        return jsonify({"error": "No topic"}), 400
    
    if not os.path.exists(MEMES_FOLDER): 
        os.makedirs(MEMES_FOLDER)
        return jsonify({"error": "No memes folder"}), 500
    
    memes = [f for f in os.listdir(MEMES_FOLDER) if f.lower().endswith(('.jpg','.jpeg','.png'))]
    if not memes: 
        return jsonify({"error": "No memes"}), 500
    
    try:
        label, roast_text = get_roast(topic, lang)
        img = add_text_to_image(os.path.join(MEMES_FOLDER, random.choice(memes)), label, roast_text)
        
        buf = BytesIO()
        img.save(buf, 'JPEG', quality=95)
        buf.seek(0)
        
        save_roast_to_db(topic, label, roast_text, lang)
        
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
