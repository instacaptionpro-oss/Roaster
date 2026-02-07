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
            print("✅ PostgreSQL Database initialized successfully")
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
        finally:
            conn.close()

init_database()

# Supabase setup (optional)
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

supabase = None
if supabase_url and supabase_key:
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase connected successfully")
    except Exception as e:
        print(f"⚠️ Supabase connection failed: {e}")
        supabase = None

MEMES_FOLDER = "memes"

AI_MODELS = [
    "llama-3.3-70b-versatile",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.1-70b-versatile"
]

# ===== DAILY TOPIC FUNCTION =====
def get_daily_topic(language='hindi'):
    """Get today's hot roast topic from daily_topic.json"""
    try:
        with open('daily_topic.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(language, data.get('hindi'))
    except Exception as e:
        print(f"Error loading daily topic: {e}")
        if language == 'hindi':
            return {
                "topic": "Monday Morning Office Wale",
                "label": "Corporate Ghulam",
                "description": "Subah 9 baje se marzi ke against kaam karne wale bechare"
            }
        else:
            return {
                "topic": "Monday Morning Office People",
                "label": "Corporate Slave",
                "description": "Poor souls working against their will since 9am"
            }

# ===== FRONTEND HTML =====
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Roaster AI - Teri Bezati Free Mein</title>
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
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
            background-image: url('https://i.postimg.cc/R0g9tGYB/Mr.jpg');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
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
            padding: 24px 48px;
            backdrop-filter: blur(12px);
            background: rgba(0, 0, 0, 0.6);
            border-bottom: 1px solid rgba(255, 69, 0, 0.3);
        }

        .nav-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.5rem;
            font-weight: 900;
            letter-spacing: -1px;
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
            animation: pulse 2s ease-in-out infinite;
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

        /* ===== HOT TOPIC BANNER - ATTENTION SEEKING ===== */
        .hot-topic-banner {
            position: relative;
            background: linear-gradient(135deg, #FF0000 0%, #FF4500 30%, #FF6347 60%, #FF4500 100%);
            border: 3px solid #FFD700;
            border-radius: 20px;
            padding: 20px 28px;
            margin-bottom: 30px;
            cursor: pointer;
            transition: all 0.3s ease;
            animation: hotBannerPulse 2s ease-in-out infinite, hotBannerShake 5s ease-in-out infinite;
            box-shadow: 
                0 0 40px rgba(255, 69, 0, 0.7),
                0 0 80px rgba(255, 0, 0, 0.4),
                inset 0 0 30px rgba(255, 215, 0, 0.2);
            overflow: hidden;
        }

        .hot-topic-banner::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(
                45deg,
                transparent 30%,
                rgba(255, 255, 255, 0.1) 50%,
                transparent 70%
            );
            animation: shimmer 3s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%) rotate(45deg); }
            100% { transform: translateX(100%) rotate(45deg); }
        }

        @keyframes hotBannerPulse {
            0%, 100% { 
                box-shadow: 
                    0 0 40px rgba(255, 69, 0, 0.7),
                    0 0 80px rgba(255, 0, 0, 0.4);
            }
            50% { 
                box-shadow: 
                    0 0 60px rgba(255, 69, 0, 0.9),
                    0 0 120px rgba(255, 0, 0, 0.6);
            }
        }

        @keyframes hotBannerShake {
            0%, 90%, 100% { transform: translateX(0); }
            92%, 96% { transform: translateX(-3px) rotate(-0.5deg); }
            94%, 98% { transform: translateX(3px) rotate(0.5deg); }
        }

        .hot-topic-banner:hover {
            transform: scale(1.03);
            box-shadow: 
                0 0 80px rgba(255, 69, 0, 1),
                0 0 150px rgba(255, 0, 0, 0.7);
        }

        .hot-badge-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 10px;
        }

        .fire-icon {
            font-size: 1.5rem;
            animation: fireFlicker 0.5s ease-in-out infinite alternate;
        }

        @keyframes fireFlicker {
            0% { transform: scale(1) rotate(-5deg); }
            100% { transform: scale(1.1) rotate(5deg); }
        }

        .hot-badge {
            background: #000;
            color: #FFD700;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 900;
            letter-spacing: 2px;
            text-transform: uppercase;
            border: 2px solid #FFD700;
            animation: badgePulse 1s ease-in-out infinite;
        }

        @keyframes badgePulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        .hot-topic-text {
            position: relative;
            font-size: 1.5rem;
            font-weight: 900;
            color: #fff;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.8), 0 0 20px rgba(255,215,0,0.5);
            margin-bottom: 8px;
        }

        .hot-topic-desc {
            position: relative;
            font-size: 0.95rem;
            color: rgba(255,255,255,0.95);
            text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
            font-weight: 500;
        }

        .click-hint {
            position: relative;
            margin-top: 12px;
            font-size: 0.8rem;
            color: #FFD700;
            font-weight: 700;
            animation: clickPulse 1.5s ease-in-out infinite;
        }

        @keyframes clickPulse {
            0%, 100% { opacity: 0.7; }
            50% { opacity: 1; }
        }

        .live-ticker {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 20px;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 69, 0, 0.3);
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 600;
            color: #FF4500;
            margin-bottom: 28px;
        }

        .ticker-icon {
            animation: flicker 1.5s ease-in-out infinite;
        }

        @keyframes flicker {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .hero-headline {
            font-size: clamp(2.2rem, 8vw, 4rem);
            font-weight: 900;
            letter-spacing: -3px;
            line-height: 1.1;
            margin-bottom: 16px;
            color: #fff;
            text-shadow: 0 4px 20px rgba(0, 0, 0, 0.9);
        }

        .hero-headline .accent {
            color: #FF4500;
            text-shadow: 0 0 40px rgba(255, 69, 0, 0.8);
        }

        .hero-subtext {
            font-size: 1rem;
            color: #fff;
            font-weight: 400;
            margin-bottom: 32px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            text-shadow: 0 2px 15px rgba(0, 0, 0, 0.9);
        }

        .language-toggle {
            display: flex;
            justify-content: center;
            gap: 0;
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
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
            background: transparent;
            color: rgba(255, 255, 255, 0.6);
        }

        .lang-btn.active {
            background: #FF4500;
            color: white;
            box-shadow: 0 4px 15px rgba(255, 69, 0, 0.4);
        }

        .lang-btn:hover:not(.active) {
            color: #fff;
            background: rgba(255, 69, 0, 0.2);
        }

        .input-engine {
            position: relative;
            max-width: 700px;
            margin: 0 auto 28px;
        }

        .command-line {
            display: flex;
            align-items: center;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 69, 0, 0.3);
            border-radius: 16px;
            padding: 4px;
            transition: all 0.3s ease;
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
            padding: 18px 8px;
            font-size: 1rem;
            color: #fff;
            font-family: 'Inter', monospace;
        }

        .command-input::placeholder {
            color: #888;
        }

        .execute-btn {
            width: 52px;
            height: 52px;
            background: #FF4500;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            box-shadow: 0 4px 20px rgba(255, 69, 0, 0.4);
        }

        .execute-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(255, 69, 0, 0.6);
        }

        .execute-btn:active {
            transform: translateY(0);
        }

        .execute-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .arrow-icon {
            width: 22px;
            height: 22px;
            fill: white;
        }

        .examples-section {
            margin-bottom: 35px;
        }

        .examples-label {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 14px;
            font-weight: 500;
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
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
        }

        .example-chip:hover {
            background: rgba(255, 69, 0, 0.3);
            border-color: #FF4500;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(255, 69, 0, 0.3);
        }

        .example-chip:active {
            transform: translateY(0);
        }

        .example-chip .chip-emoji {
            margin-right: 5px;
        }

        .example-chip.hidden {
            display: none;
        }

        .more-options-btn {
            padding: 8px 20px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px dashed rgba(255, 255, 255, 0.4);
            border-radius: 50px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
            margin-top: 10px;
        }

        .more-options-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: #FF4500;
            color: #fff;
        }

        .more-options-btn.expanded {
            background: rgba(255, 69, 0, 0.2);
            border: 1px solid #FF4500;
            color: #FF4500;
        }

        .loading-container {
            display: none;
            padding: 60px 24px;
        }

        .loading-container.active {
            display: block;
        }

        .loading-ring {
            width: 70px;
            height: 70px;
            border: 4px solid rgba(255, 69, 0, 0.1);
            border-top: 4px solid #FF4500;
            border-radius: 50%;
            margin: 0 auto 28px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 1.1rem;
            color: #FF4500;
            font-weight: 600;
            animation: textPulse 2s ease-in-out infinite;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.9);
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
            backdrop-filter: blur(12px);
            border: 3px solid #FF4500;
            border-radius: 20px;
            box-shadow: 
                0 0 60px rgba(255, 69, 0, 0.5),
                inset 0 0 30px rgba(255, 69, 0, 0.1);
            animation: cardSlideIn 0.5s ease-out;
        }

        .result-card.active {
            display: block;
        }

        @keyframes cardSlideIn {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
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

        .whatsapp-btn, .retry-btn {
            flex: 1;
            padding: 14px 20px;
            font-size: 0.9rem;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
        }

        .whatsapp-btn {
            background: #25D366;
            color: white;
        }

        .whatsapp-btn:hover {
            background: #1ea952;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(37, 211, 102, 0.4);
        }

        .instagram-btn {
            background: linear-gradient(45deg,#f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%);
            color: white;
            flex: 1;
            padding: 14px 20px;
            font-size: 0.9rem;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
        }

        .instagram-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(204, 35, 136, 0.35);
        }

        .retry-btn {
            background: rgba(255, 69, 0, 0.2);
            color: #FF4500;
            border: 2px solid #FF4500;
        }

        .retry-btn:hover {
            background: #FF4500;
            color: white;
            transform: translateY(-2px);
        }

        .download-btn {
            background: #1e90ff;
            color: white;
            flex: 1;
            padding: 14px 20px;
            font-size: 0.9rem;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
        }

        .download-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(30, 144, 255, 0.25);
        }

        .error-message {
            display: none;
            max-width: 500px;
            margin: 20px auto;
            padding: 14px 20px;
            background: rgba(255, 69, 0, 0.2);
            backdrop-filter: blur(12px);
            border: 1px solid #FF4500;
            border-radius: 12px;
            color: #fff;
            font-weight: 600;
            animation: shake 0.5s;
        }

        .error-message.active {
            display: block;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }

        @media (max-width: 768px) {
            .navbar {
                padding: 16px 20px;
            }

            .nav-brand {
                font-size: 1.2rem;
            }

            .container {
                padding: 30px 16px;
            }

            .hot-topic-banner {
                padding: 16px 20px;
                border-radius: 16px;
            }

            .hot-topic-text {
                font-size: 1.2rem;
            }

            .hot-topic-desc {
                font-size: 0.85rem;
            }

            .hero-headline {
                font-size: 1.8rem;
                letter-spacing: -1px;
            }

            .hero-subtext {
                font-size: 0.9rem;
            }

            .language-toggle {
                width: 100%;
                max-width: 260px;
            }

            .lang-btn {
                padding: 8px 18px;
                font-size: 0.8rem;
            }

            .example-chips {
                gap: 6px;
            }

            .example-chip {
                padding: 6px 12px;
                font-size: 0.75rem;
            }

            .action-buttons {
                flex-direction: column;
            }

            .command-input {
                font-size: 0.9rem;
                padding: 14px 8px;
            }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="nav-brand">
            🔥 ROASTER
        </div>
        <div class="system-status">
            <div class="status-dot"></div>
            <span id="statusText">Bakchodi Mode: ON</span>
        </div>
    </nav>

    <div class="container">
        
        <!-- ===== HOT TOPIC BANNER - ATTENTION SEEKING ===== -->
        <div class="hot-topic-banner" id="hotTopicBanner" onclick="useDailyTopic()">
            <div class="hot-badge-container">
                <span class="fire-icon">🔥</span>
                <span class="hot-badge">AAJ KA SPECIAL ROAST</span>
                <span class="fire-icon">🔥</span>
            </div>
            <div class="hot-topic-text" id="hotTopicText">Loading...</div>
            <div class="hot-topic-desc" id="hotTopicDesc"></div>
            <div class="click-hint">👆 TAP TO ROAST THIS TOPIC 👆</div>
        </div>

        <div class="live-ticker">
            <span class="ticker-icon">🔥</span>
            <span id="egoCounter">Loading...</span> <span id="tickerText">Logo Ki Bezati Hui</span>
        </div>

        <h1 class="hero-headline">
            <span id="headlineText">Apni <span class="accent">Asli Aukaat</span> Dekh</span>
        </h1>
        <p class="hero-subtext" id="subtextText">
            2-3 line ka brutal roast jo tujhe khud mein dikhe. 100% relatable! 🪞
        </p>

        <!-- ===== LANGUAGE TOGGLE ===== -->
        <div class="language-toggle">
            <button class="lang-btn active" id="hindiBtn" onclick="setLanguage('hindi')">
                🇮🇳 Hindi
            </button>
            <button class="lang-btn" id="englishBtn" onclick="setLanguage('english')">
                🇺🇸 English
            </button>
        </div>

        <!-- ===== INPUT ENGINE ===== -->
        <div class="input-engine">
            <div class="command-line">
                <span class="command-prefix">></span>
                <input 
                    type="text" 
                    class="command-input" 
                    id="topicInput"
                    placeholder="Kiski leni hai? Bol na bc..."
                    maxlength="100"
                >
                <button class="execute-btn" id="executeBtn" onclick="executeRoast()">
                    <svg class="arrow-icon" viewBox="0 0 24 24">
                        <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
                    </svg>
                </button>
            </div>
        </div>

        <!-- ===== EXAMPLE CHIPS ===== -->
        <div class="examples-section">
            <p class="examples-label" id="examplesLabel">🎯 Sabse Jyada Bezati:</p>
            
            <!-- HINDI CHIPS -->
            <div class="example-chips" id="hindiChips">
                <button class="example-chip" onclick="useExample('Gym wale log')">
                    <span class="chip-emoji">💪</span>Gym Frauds
                </button>
                <button class="example-chip" onclick="useExample('Engineering students')">
                    <span class="chip-emoji">💻</span>Engineers
                </button>
                <button class="example-chip" onclick="useExample('Procrastination experts')">
                    <span class="chip-emoji">⏰</span>Kal Karte Hain
                </button>
                <button class="example-chip" onclick="useExample('Online shopping addiction')">
                    <span class="chip-emoji">🛒</span>Shopaholics
                </button>
                
                <button class="example-chip hidden hindi-extra" onclick="useExample('Social media attention seekers')">
                    <span class="chip-emoji">📱</span>Attention Seekers
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Broke people with rich dreams')">
                    <span class="chip-emoji">💸</span>Gareeb Sapne
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Gamers who blame lag')">
                    <span class="chip-emoji">🎮</span>Lag Bahana
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Corporate office slaves')">
                    <span class="chip-emoji">👔</span>Office Majdoor
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Diet wale log')">
                    <span class="chip-emoji">🥗</span>Diet Frauds
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Exam se ek raat pehle')">
                    <span class="chip-emoji">📚</span>Last Night Padhaku
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Situationship experts')">
                    <span class="chip-emoji">💔</span>Situationship
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Netflix binge watchers')">
                    <span class="chip-emoji">📺</span>Netflix Addicts
                </button>
            </div>
            
            <!-- ENGLISH CHIPS -->
            <div class="example-chips" id="englishChips" style="display: none;">
                <button class="example-chip" onclick="useExample('Gym people who never go')">
                    <span class="chip-emoji">💪</span>Gym Frauds
                </button>
                <button class="example-chip" onclick="useExample('Software engineers')">
                    <span class="chip-emoji">💻</span>Engineers
                </button>
                <button class="example-chip" onclick="useExample('Procrastinators')">
                    <span class="chip-emoji">⏰</span>Procrastinators
                </button>
                <button class="example-chip" onclick="useExample('Online shopping addicts')">
                    <span class="chip-emoji">🛒</span>Shopaholics
                </button>
                
                <button class="example-chip hidden english-extra" onclick="useExample('Social media attention seekers')">
                    <span class="chip-emoji">📱</span>Attention Seekers
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Broke people rich dreams')">
                    <span class="chip-emoji">💸</span>Broke Dreamers
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Gamers who blame lag')">
                    <span class="chip-emoji">🎮</span>Lag Blamers
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Corporate office workers')">
                    <span class="chip-emoji">👔</span>Office Slaves
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('People on diet')">
                    <span class="chip-emoji">🥗</span>Diet Frauds
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Last night study experts')">
                    <span class="chip-emoji">📚</span>Crammers
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Situationship people')">
                    <span class="chip-emoji">💔</span>Situationship
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Netflix binge watchers')">
                    <span class="chip-emoji">📺</span>Netflix Addicts
                </button>
            </div>
            
            <button class="more-options-btn" id="moreOptionsBtn" onclick="toggleMoreOptions()">
                + Aur Dikhao
            </button>
        </div>

        <div class="loading-container" id="loadingContainer">
            <div class="loading-ring"></div>
            <div class="loading-text" id="loadingText">Teri aukaat dhundh raha hoon...</div>
        </div>

        <div class="result-card" id="resultCard">
            <img src="" alt="Roasted" class="result-image" id="resultImage">
            <div class="action-buttons">
                <button class="whatsapp-btn" onclick="shareToWhatsApp()">
                    📱 WhatsApp
                </button>
                <button class="instagram-btn" onclick="shareToInstagram()">
                    📸 Instagram
                </button>
                <button class="download-btn" onclick="downloadResult()">
                    ⬇️ Download
                </button>
                <button class="retry-btn" onclick="reset()">
                    🔄 Aur
                </button>
            </div>
        </div>

        <div class="error-message" id="errorMessage"></div>
    </div>

    <script>
        let currentImageUrl = '';
        let currentTopic = '';
        let currentLanguage = 'hindi';
        let moreOptionsExpanded = false;
        let dailyTopicData = null;
        
        const loadingMessagesHindi = [
            "Teri aukaat dhundh raha hoon...",
            "2-3 line ka maal ban raha hai...",
            "Bakchodi load ho rahi hai...",
            "Tera nalla pan calculate ho raha...",
            "Tujhe chuna lagane ki taiyari...",
            "Fekarchand ki report ban rahi...",
            "Tera kalesh ready ho raha hai...",
            "Brutal roast cook ho raha hai..."
        ];
        
        const loadingMessagesEnglish = [
            "Finding your true self...",
            "Cooking a 2-3 line roast...",
            "Loading your reality check...",
            "Calculating your failure rate...",
            "Preparing brutal honesty...",
            "Your L is being prepared...",
            "Truth incoming, brace yourself...",
            "This one's gonna hurt..."
        ];

        // Fetch Daily Topic
        async function fetchDailyTopic() {
            try {
                const response = await fetch('/api/daily-topic?lang=' + currentLanguage);
                const data = await response.json();
                if (data.success) {
                    dailyTopicData = data.data;
                    document.getElementById('hotTopicText').textContent = dailyTopicData.topic;
                    document.getElementById('hotTopicDesc').textContent = dailyTopicData.description;
                    
                    // Update badge text based on language
                    const badge = document.querySelector('.hot-badge');
                    badge.textContent = currentLanguage === 'hindi' ? "AAJ KA SPECIAL ROAST" : "TODAY'S SPECIAL ROAST";
                    
                    const hint = document.querySelector('.click-hint');
                    hint.textContent = currentLanguage === 'hindi' ? "👆 TAP TO ROAST THIS 👆" : "👆 TAP TO ROAST THIS 👆";
                }
            } catch (error) {
                console.error('Failed to fetch daily topic:', error);
            }
        }

        function useDailyTopic() {
            if (dailyTopicData) {
                document.getElementById('topicInput').value = dailyTopicData.topic;
                
                // Flash effect
                const banner = document.getElementById('hotTopicBanner');
                banner.style.transform = 'scale(0.97)';
                banner.style.boxShadow = '0 0 100px rgba(255, 215, 0, 1)';
                setTimeout(() => {
                    banner.style.transform = 'scale(1)';
                    banner.style.boxShadow = '';
                    executeRoast();
                }, 200);
            }
        }

        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                document.getElementById('egoCounter').textContent = data.total_roasts.toLocaleString();
            } catch (error) {
                document.getElementById('egoCounter').textContent = '14,203';
            }
        }
        
        fetchStats();
        fetchDailyTopic();

        function animateCounter() {
            const counter = document.getElementById('egoCounter');
            setInterval(() => {
                let currentVal = parseInt(counter.textContent.replace(/,/g, '')) || 14203;
                currentVal += Math.floor(Math.random() * 3);
                counter.textContent = currentVal.toLocaleString();
            }, 3000);
        }
        setTimeout(animateCounter, 2000);

        function setLanguage(lang) {
            currentLanguage = lang;
            
            document.getElementById('hindiBtn').classList.toggle('active', lang === 'hindi');
            document.getElementById('englishBtn').classList.toggle('active', lang === 'english');
            
            document.getElementById('hindiChips').style.display = lang === 'hindi' ? 'flex' : 'none';
            document.getElementById('englishChips').style.display = lang === 'english' ? 'flex' : 'none';
            
            const input = document.getElementById('topicInput');
            if (lang === 'hindi') {
                input.placeholder = "Kiski leni hai? Bol na bc...";
                document.getElementById('examplesLabel').textContent = "🎯 Sabse Jyada Bezati:";
                document.getElementById('statusText').textContent = "Bakchodi Mode: ON";
                document.getElementById('tickerText').textContent = "Logo Ki Bezati Hui";
                document.getElementById('headlineText').innerHTML = 'Apni <span class="accent">Asli Aukaat</span> Dekh';
                document.getElementById('subtextText').textContent = "2-3 line ka brutal roast jo tujhe khud mein dikhe. 100% relatable! 🪞";
                document.getElementById('moreOptionsBtn').textContent = moreOptionsExpanded ? '− Kam Dikhao' : '+ Aur Dikhao';
            } else {
                input.placeholder = "Who needs a reality check?";
                document.getElementById('examplesLabel').textContent = "🎯 Most Roasted Topics:";
                document.getElementById('statusText').textContent = "Savage Mode: ON";
                document.getElementById('tickerText').textContent = "People Roasted Today";
                document.getElementById('headlineText').innerHTML = 'See Your <span class="accent">True Self</span>';
                document.getElementById('subtextText').textContent = "2-3 lines of brutal truth that hits home. 100% relatable! 🪞";
                document.getElementById('moreOptionsBtn').textContent = moreOptionsExpanded ? '− Show Less' : '+ Show More';
            }
            
            // Refetch daily topic for new language
            fetchDailyTopic();
            
            hideExtraChips();
            moreOptionsExpanded = false;
            document.getElementById('moreOptionsBtn').classList.remove('expanded');
        }

        function toggleMoreOptions() {
            moreOptionsExpanded = !moreOptionsExpanded;
            const btn = document.getElementById('moreOptionsBtn');
            
            if (moreOptionsExpanded) {
                btn.textContent = currentLanguage === 'hindi' ? '− Kam Dikhao' : '− Show Less';
                btn.classList.add('expanded');
                showExtraChips();
            } else {
                btn.textContent = currentLanguage === 'hindi' ? '+ Aur Dikhao' : '+ Show More';
                btn.classList.remove('expanded');
                hideExtraChips();
            }
        }

        function showExtraChips() {
            const extraClass = currentLanguage === 'hindi' ? 'hindi-extra' : 'english-extra';
            document.querySelectorAll('.' + extraClass).forEach(chip => {
                chip.classList.remove('hidden');
            });
        }

        function hideExtraChips() {
            document.querySelectorAll('.hindi-extra, .english-extra').forEach(chip => {
                chip.classList.add('hidden');
            });
        }

        function useExample(topic) {
            document.getElementById('topicInput').value = topic;
            document.getElementById('topicInput').focus();
            
            const input = document.getElementById('topicInput');
            input.style.background = 'rgba(255, 69, 0, 0.2)';
            setTimeout(() => {
                input.style.background = 'transparent';
            }, 300);
        }

        document.getElementById('topicInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                executeRoast();
            }
        });

        async function executeRoast() {
            const topic = document.getElementById('topicInput').value.trim();
            
            if (!topic) {
                const errorMsg = currentLanguage === 'hindi' 
                    ? 'Abe kuch toh likh nalle! 🤡' 
                    : 'Type something first clown! 🤡';
                showError(errorMsg);
                return;
            }

            currentTopic = topic;
            
            document.getElementById('resultCard').classList.remove('active');
            document.getElementById('errorMessage').classList.remove('active');
            document.getElementById('loadingContainer').classList.add('active');
            document.getElementById('executeBtn').disabled = true;

            const messages = currentLanguage === 'hindi' ? loadingMessagesHindi : loadingMessagesEnglish;
            let msgIndex = 0;
            const loadingInterval = setInterval(() => {
                msgIndex = (msgIndex + 1) % messages.length;
                document.getElementById('loadingText').textContent = messages[msgIndex];
            }, 1000);

            try {
                const response = await fetch('/roast?topic=' + encodeURIComponent(topic) + '&lang=' + currentLanguage);
                
                clearInterval(loadingInterval);
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Roast failed');
                }

                const blob = await response.blob();
                currentImageUrl = URL.createObjectURL(blob);
                
                document.getElementById('resultImage').src = currentImageUrl;
                document.getElementById('loadingContainer').classList.remove('active');
                document.getElementById('resultCard').classList.add('active');
                
                fetchStats();

            } catch (error) {
                clearInterval(loadingInterval);
                document.getElementById('loadingContainer').classList.remove('active');
                const errorMsg = currentLanguage === 'hindi' 
                    ? 'Kuch toh gadbad hai! Dobara try kar bc! 😤' 
                    : 'Something went wrong! Try again! 😤';
                showError(errorMsg);
            } finally {
                document.getElementById('executeBtn').disabled = false;
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.classList.add('active');
        }

        function shareToWhatsApp() {
            const text = currentLanguage === 'hindi'
                ? encodeURIComponent('Dekh meri kaise li gayi 🔥😂 - Tu bhi apni luwa: ' + window.location.href)
                : encodeURIComponent('Got roasted hard 🔥😂 - Get yours: ' + window.location.href);
            window.open('https://wa.me/?text=' + text, '_blank');
        }

        function shareToInstagram() {
            downloadResult();
            const msg = currentLanguage === 'hindi' 
                ? 'Image download ho gaya! 📸 Ab Instagram pe daal!' 
                : 'Image downloaded! 📸 Now share on Instagram!';
            alert(msg);
        }

        function downloadResult() {
            if (currentImageUrl) {
                const a = document.createElement('a');
                a.href = currentImageUrl;
                a.download = 'roast_' + Date.now() + '.jpg';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
        }

        function reset() {
            document.getElementById('resultCard').classList.remove('active');
            document.getElementById('topicInput').value = '';
            document.getElementById('topicInput').focus();
            currentImageUrl = '';
            currentTopic = '';
        }

        setLanguage('hindi');
    </script>
</body>
</html>"""


# ===== DATABASE FUNCTIONS =====
def save_roast_to_db(topic, identity_label, roast_text, language='hindi'):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO roasts (topic, identity_label, roast_text, language) VALUES (%s, %s, %s, %s)',
                (topic, identity_label, roast_text, language)
            )
            cursor.execute(
                'UPDATE stats SET total_roasts = total_roasts + 1, last_updated = CURRENT_TIMESTAMP WHERE id = 1'
            )
            conn.commit()
        except Exception as e:
            print(f"❌ Database save error: {e}")
        finally:
            conn.close()

def get_total_roasts():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT total_roasts FROM stats WHERE id = 1')
            result = cursor.fetchone()
            return result['total_roasts'] if result else 14203
        except Exception as e:
            return 14203
        finally:
            conn.close()
    return 14203


# ===== BACKEND FUNCTIONS =====
def get_font(size=40):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\Arial.ttf",
        "arial.ttf",
        "DejaVuSans-Bold.ttf"
    ]
    
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    
    return ImageFont.load_default()


def get_roast(topic, language='hindi'):
    """Generate 2-part roast: Identity Label + 2-3 Line Relatable Roast"""
    
    if language == 'hindi':
        system_prompt = """
Tu ek SAVAGE Hindi meme writer hai. Tujhe 2 cheezein deni hain:

### FORMAT (STRICTLY FOLLOW):
LABEL: [1-2 word funny Hindi title]
ROAST: [2-3 lines ka relatable roast jo sabko lage "ye toh main hoon bc"]

### RULES:
1. LABEL = Funny identity (1-2 words max)
2. ROAST = 2-3 LINES, not just one line! Multiple sentences.
3. RELATABLE - 80% log bole "haan ye toh main hoon"
4. SPICY WORDS - bc, mc, bsdk, chutiya, gadha, bewkoof, nalla, vela, fekarchand, sasta, bakchodi, kaleshi, chuna
5. Each line should hit different angle of same topic
6. Funny + Savage + True

### LABEL IDEAS:
Procrastination Ka Devta, Khatarnak Gareeb, Gym Ka Tourist, Wishlist Ka Raja, Corporate Majdoor, Bistar Ka Keeda, Chapri Aesthetic, Ghosting Expert, Maggi Scientist, Situationship Ka Maara, Vela Supreme, Fekarchand Premium, Nalla Professional

### EXAMPLE FORMAT:
LABEL: Gym Ka Tourist
ROAST: Gym membership lena hi workout tha, ab body bhi maang raha hai bc.
Selfie toh 50 leli, ek pushup nahi hua aaj bhi.
Trainer bhi ab tera naam bhool gaya hai chutiye.

LABEL: Corporate Ghulam  
ROAST: Monday se Friday tak toh jeena hi nahi hai tujhe.
Salary aate hi EMI, rent aur upar se gareeb bhi wohi ka wohi.
"Work-life balance" sirf LinkedIn pe likhne ke liye hai nalle.

LABEL: Situationship Expert
ROAST: Na girlfriend hai, na single hai, beech mein latka hua hai.
"Dekh lenge" sunते sunते 2 saal nikal gaye bewkoof.
Commitment se itna darr lagta hai jitna Monday se.

BE CREATIVE! 2-3 LINES ALWAYS! DIFFERENT EVERY TIME!

Topic: """

    else:
        system_prompt = """
You're a SAVAGE meme writer. Give 2 things:

### FORMAT (STRICTLY FOLLOW):
LABEL: [1-2 word funny title]
ROAST: [2-3 lines of relatable roast that makes everyone say "that's me lol"]

### RULES:
1. LABEL = Funny identity (1-2 words max)
2. ROAST = 2-3 LINES, not just one! Multiple sentences.
3. RELATABLE - 80% people say "that's literally me"
4. EDGY WORDS - damn, hell, crap, dumbass, idiot, loser, clown, pathetic
5. Each line hits different angle of same topic
6. Funny + Savage + True

### LABEL IDEAS:
Procrastination God, Professional Broke, Gym Tourist, Cart Champion, Corporate Slave, Bed Potato, Copy-Paste Engineer, Ghosting Pro, Microwave Chef, Almost Dating, Premium Loser, Certified Clown

### EXAMPLE FORMAT:
LABEL: Gym Tourist
ROAST: Buying the membership was the only workout you did this year.
Mirror selfies? 50. Actual exercises? Maybe 2.
Even your trainer pretends not to know you anymore.

LABEL: Corporate Slave
ROAST: Monday to Friday you're basically a zombie in formal clothes.
Salary comes, EMI goes, you're still broke somehow.
"Work-life balance" only exists in your LinkedIn bio.

LABEL: Situationship Pro
ROAST: Not single, not taken, just confused for 2 years straight.
"Let's see where this goes" has gone absolutely nowhere.
Commitment scares you more than Monday mornings.

BE CREATIVE! 2-3 LINES ALWAYS! DIFFERENT EVERY TIME!

Topic: """

    for model_index, model_name in enumerate(AI_MODELS):
        try:
            completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": topic}
                ],
                model=model_name,
                temperature=1.3,
                max_tokens=200,
                top_p=0.95,
            )
            
            response = completion.choices[0].message.content.strip()
            print(f"AI Response: {response}")
            
            label = ""
            roast_lines = []
            
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.upper().startswith('LABEL:'):
                    label = line.split(':', 1)[1].strip().strip('"\'')
                elif line.upper().startswith('ROAST:'):
                    roast_lines.append(line.split(':', 1)[1].strip().strip('"\''))
                elif line and not line.upper().startswith('LABEL') and len(roast_lines) > 0:
                    # Additional roast lines
                    roast_lines.append(line.strip().strip('"\''))
                elif line and len(roast_lines) == 0 and label:
                    # First roast line without ROAST: prefix
                    roast_lines.append(line.strip().strip('"\''))
            
            # Clean up
            label = label.replace('**', '').replace('*', '').strip()
            roast = ' '.join(roast_lines).replace('**', '').replace('*', '').strip()
            
            # Ensure we have 2-3 sentences
            if roast.count('.') < 2:
                # Try to split by common patterns
                if '।' in roast:  # Hindi full stop
                    roast = roast.replace('।', '.')
            
            if not label:
                if language == 'hindi':
                    label = random.choice(["Certified Nalla", "Vela Premium", "Bakchod Expert", "Chapri Supreme"])
                else:
                    label = random.choice(["Certified Clown", "Professional Idiot", "Expert Loser", "Premium Dumbass"])
            
            if not roast or len(roast) < 20:
                if language == 'hindi':
                    roast = "Tujhe roast karne layak content hi nahi hai bc. Itna boring hai tu ki AI bhi bore ho gaya. Ja pehle kuch interesting kar life mein."
                else:
                    roast = "You're too boring to even roast properly. The AI literally fell asleep. Go do something interesting first."
            
            print(f"✅ Label: {label}")
            print(f"✅ Roast: {roast}")
            
            return label, roast
        
        except Exception as e:
            print(f"❌ Model {model_name} failed: {e}")
            continue
    
    # Fallback roasts (2-3 lines)
    if language == 'hindi':
        fallbacks = [
            ("Certified Nalla", "AI bhi thak gaya tujhe samajhne mein, tu hopeless case hai bc. Teri life mein itna kuch ho raha hai ki kuch bhi nahi ho raha. Ja so ja, wohi tera best talent hai."),
            ("Vela Supreme", "Tere jaise nalle dhundhne mein bhi mehnat lagti hai. Din bhar phone pe aur raat bhar bhi phone pe. Productive toh tu apne sapno mein bhi nahi hai bewkoof."),
            ("Bakchod Expert", "Kuch karna nahi hai life mein, bas bakchodi karni hai. Friends bhi ab bore ho gaye hain tujhse. Real talent: kuch na karke bhi busy rehna."),
        ]
    else:
        fallbacks = [
            ("Certified Clown", "Even AI gave up on you, that's a new level of pathetic. Your life is so uneventful that nothing is happening. Go sleep, that's your only real talent."),
            ("Professional Idiot", "Your existence is already a roast, I don't need to add more. Phone 24/7 but still got nothing to show for it. Productivity left the chat years ago."),
            ("Expert Loser", "You're so boring even autocomplete doesn't want to finish your sentences. Friends pretend to be busy when you text. Peak skill: being busy doing absolutely nothing."),
        ]
    
    return random.choice(fallbacks)


def wrap_text(text, font, max_width):
    lines = []
    words = text.split()
    
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines


def add_text_to_image(image_path, label, roast):
    """Add Label (top) + 2-3 line Roast (bottom) with RED HOT style"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    img_width, img_height = img.size
    
    # ===== RED HOT BORDER =====
    border_width = 10
    draw.rectangle([0, 0, img_width-1, img_height-1], outline="#8B0000", width=border_width)
    draw.rectangle([border_width, border_width, img_width-border_width-1, img_height-border_width-1], outline="#FF4500", width=5)
    draw.rectangle([border_width+5, border_width+5, img_width-border_width-6, img_height-border_width-6], outline="#FF6347", width=2)
    
    # ===== TOP: IDENTITY LABEL =====
    label_font_size = int(img_height * 0.075)
    label_font = get_font(label_font_size)
    
    label_text = label.upper()
    label_bbox = label_font.getbbox(label_text)
    label_width = label_bbox[2] - label_bbox[0]
    label_x = (img_width - label_width) // 2
    label_y = 25
    
    # Black outline
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            draw.text((label_x + dx, label_y + dy), label_text, font=label_font, fill="black")
    
    # Orange label
    draw.text((label_x, label_y), label_text, font=label_font, fill="#FF4500")
    
    # ===== BOTTOM: 2-3 LINE ROAST =====
    roast_font_size = int(img_height * 0.042)  # Slightly smaller for more lines
    roast_font = get_font(roast_font_size)
    
    max_width = int(img_width * 0.88)
    lines = wrap_text(roast, roast_font, max_width)
    
    line_height = roast_font_size + 8
    total_text_height = len(lines) * line_height
    y_position = img_height - total_text_height - 30
    
    for line in lines:
        bbox = roast_font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x_position = (img_width - text_width) // 2
        
        # Black outline
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                draw.text((x_position + dx, y_position + dy), line, font=roast_font, fill="black")
        
        # Cream text
        draw.text((x_position, y_position), line, font=roast_font, fill="#FFFACD")
        y_position += line_height
    
    return img


def save_to_supabase(topic, roast_text, image_buffer, language='hindi'):
    if supabase is None:
        return None
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"roast_{timestamp}_{random.randint(1000, 9999)}.jpg"
        image_buffer.seek(0)
        supabase.storage.from_("memes").upload(filename, image_buffer.read(), file_options={"content-type": "image/jpeg"})
        return supabase.storage.from_("memes").get_public_url(filename)
    except Exception as e:
        print(f"Supabase Error: {e}")
        return None


# ===== ROUTES =====
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/stats')
def get_stats():
    total = get_total_roasts()
    return jsonify({"total_roasts": total, "success": True})


@app.route('/api/daily-topic')
def daily_topic():
    lang = request.args.get('lang', 'hindi')
    topic_data = get_daily_topic(lang)
    return jsonify({"success": True, "data": topic_data})


@app.route('/roast', methods=['GET'])
def roast():
    topic = request.args.get('topic', '').strip()
    language = request.args.get('lang', 'hindi').strip()
    
    if not topic:
        return jsonify({"error": "Topic required!"}), 400
    
    if not os.path.exists(MEMES_FOLDER):
        os.makedirs(MEMES_FOLDER)
        return jsonify({"error": "Memes folder is empty!"}), 500
    
    meme_files = [f for f in os.listdir(MEMES_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not meme_files:
        return jsonify({"error": "No meme images found!"}), 500
    
    try:
        label, roast_text = get_roast(topic, language)
        
        random_meme = random.choice(meme_files)
        meme_path = os.path.join(MEMES_FOLDER, random_meme)
        final_image = add_text_to_image(meme_path, label, roast_text)
        
        img_io = BytesIO()
        final_image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        
        save_roast_to_db(topic, label, roast_text, language)
        
        try:
            save_to_supabase(topic, roast_text, BytesIO(img_io.getvalue()), language)
        except:
            pass
        
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == '__main__':
    if not os.path.exists(MEMES_FOLDER):
        os.makedirs(MEMES_FOLDER)
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
