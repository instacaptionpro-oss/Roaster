import os
import random
import textwrap
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

# Enable static file serving
app = Flask(__name__, static_folder='static', static_url_path='/static')

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ===== POSTGRESQL DATABASE SETUP =====
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://roast_db_c13t_user:9PO09Y3SpZ6z5r0eYszLsYGHg0bcYtXx@dpg-d5ubdo24d50c73d1bmdg-a/roast_db_c13t")

def get_db_connection():
    """Create a database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables"""
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
            # Initialize stats if empty
            cursor.execute('SELECT COUNT(*) as count FROM stats')
            if cursor.fetchone()['count'] == 0:
                cursor.execute('INSERT INTO stats (total_roasts) VALUES (14203)')
            
            conn.commit()
            print("✅ PostgreSQL Database initialized successfully")
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
        finally:
            conn.close()

# Initialize database on startup
init_database()

# Supabase setup (optional - for image storage)
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
else:
    print("⚠️ Supabase credentials not found (optional)")

MEMES_FOLDER = "memes"

# AI Model Configuration (Primary + Backups)
AI_MODELS = [
    "llama-3.3-70b-versatile",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.1-70b-versatile"
]

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
            padding: 60px 24px;
            text-align: center;
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
            margin-bottom: 32px;
        }

        .ticker-icon {
            animation: flicker 1.5s ease-in-out infinite;
        }

        @keyframes flicker {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .hero-headline {
            font-size: clamp(2.5rem, 8vw, 4.5rem);
            font-weight: 900;
            letter-spacing: -3px;
            line-height: 1.1;
            margin-bottom: 20px;
            color: #fff;
            text-shadow: 0 4px 20px rgba(0, 0, 0, 0.9);
        }

        .hero-headline .accent {
            color: #FF4500;
            text-shadow: 0 0 40px rgba(255, 69, 0, 0.8);
        }

        .hero-subtext {
            font-size: 1.1rem;
            color: #fff;
            font-weight: 400;
            margin-bottom: 40px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            text-shadow: 0 2px 15px rgba(0, 0, 0, 0.9);
        }

        /* ===== LANGUAGE TOGGLE ===== */
        .language-toggle {
            display: flex;
            justify-content: center;
            gap: 0;
            margin-bottom: 24px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 50px;
            padding: 4px;
            width: fit-content;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid rgba(255, 69, 0, 0.3);
        }

        .lang-btn {
            padding: 12px 28px;
            font-size: 0.95rem;
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

        /* ===== INPUT ENGINE ===== */
        .input-engine {
            position: relative;
            max-width: 700px;
            margin: 0 auto 32px;
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
            padding: 20px 8px;
            font-size: 1.1rem;
            color: #fff;
            font-family: 'Inter', monospace;
        }

        .command-input::placeholder {
            color: #888;
        }

        .execute-btn {
            width: 56px;
            height: 56px;
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
            width: 24px;
            height: 24px;
            fill: white;
        }

        /* ===== EXAMPLE CHIPS SECTION ===== */
        .examples-section {
            margin-bottom: 40px;
        }

        .examples-label {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 16px;
            font-weight: 500;
        }

        .example-chips {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            max-width: 700px;
            margin: 0 auto;
        }

        .example-chip {
            padding: 10px 18px;
            background: rgba(255, 69, 0, 0.15);
            border: 1px solid rgba(255, 69, 0, 0.4);
            border-radius: 50px;
            color: #fff;
            font-size: 0.9rem;
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
            margin-right: 6px;
        }

        .example-chip.hidden {
            display: none;
        }

        /* More Options Button */
        .more-options-btn {
            padding: 10px 24px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px dashed rgba(255, 255, 255, 0.4);
            border-radius: 50px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
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

        /* ===== LOADING ===== */
        .loading-container {
            display: none;
            padding: 80px 24px;
        }

        .loading-container.active {
            display: block;
        }

        .loading-ring {
            width: 80px;
            height: 80px;
            border: 4px solid rgba(255, 69, 0, 0.1);
            border-top: 4px solid #FF4500;
            border-radius: 50%;
            margin: 0 auto 32px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 1.2rem;
            color: #FF4500;
            font-weight: 600;
            animation: textPulse 2s ease-in-out infinite;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.9);
        }

        @keyframes textPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* ===== RESULT CARD ===== */
        .result-card {
            display: none;
            max-width: 700px;
            margin: 0 auto;
            padding: 24px;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 69, 0, 0.3);
            border-radius: 24px;
            box-shadow: 0 0 60px rgba(255, 69, 0, 0.3);
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
            border-radius: 16px;
            margin-bottom: 24px;
        }

        .action-buttons {
            display: flex;
            gap: 12px;
        }

        .whatsapp-btn, .retry-btn {
            flex: 1;
            padding: 16px 24px;
            font-size: 1rem;
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
            padding: 16px 24px;
            font-size: 1rem;
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
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 69, 0, 0.3);
        }

        .retry-btn:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: translateY(-2px);
        }

        .download-btn {
            background: #1e90ff;
            color: white;
            flex: 1;
            padding: 16px 24px;
            font-size: 1rem;
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
            margin: 24px auto;
            padding: 16px 24px;
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

        /* Warning Badge */
        .warning-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            background: rgba(255, 0, 0, 0.2);
            border: 1px solid rgba(255, 0, 0, 0.5);
            border-radius: 50px;
            font-size: 0.75rem;
            font-weight: 600;
            color: #ff6b6b;
            margin-bottom: 20px;
        }

        @media (max-width: 768px) {
            .navbar {
                padding: 20px 24px;
            }

            .nav-brand {
                font-size: 1.25rem;
            }

            .container {
                padding: 40px 16px;
            }

            .hero-headline {
                font-size: 2rem;
                letter-spacing: -1px;
            }

            .hero-subtext {
                font-size: 0.95rem;
            }

            .language-toggle {
                width: 100%;
                max-width: 280px;
            }

            .lang-btn {
                padding: 10px 20px;
                font-size: 0.85rem;
            }

            .example-chips {
                gap: 8px;
            }

            .example-chip {
                padding: 8px 14px;
                font-size: 0.8rem;
            }

            .action-buttons {
                flex-direction: column;
            }

            .command-input {
                font-size: 0.95rem;
                padding: 16px 8px;
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
            <span id="statusText">Savage Mode: ON</span>
        </div>
    </nav>

    <div class="container">
        <div class="warning-badge">
            ⚠️ 18+ Content | No Mercy Guaranteed
        </div>

        <div class="live-ticker">
            <span class="ticker-icon">🔥</span>
            <span id="egoCounter">Loading...</span> <span id="tickerText">Egos Destroyed Today</span>
        </div>

        <h1 class="hero-headline">
            <span id="headlineText">Get <span class="accent">Roasted</span> Free</span>
        </h1>
        <p class="hero-subtext" id="subtextText">
            AI that destroys your ego. No filters. Pure savage mode! 🤡
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
                    placeholder="Kisko roast karna hai? Bol na..."
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
            <p class="examples-label" id="examplesLabel">🎯 Popular Roasts:</p>
            
            <!-- HINDI CHIPS -->
            <div class="example-chips" id="hindiChips">
                <button class="example-chip" onclick="useExample('Gym jaane wale log')">
                    <span class="chip-emoji">💪</span>Gym Lovers
                </button>
                <button class="example-chip" onclick="useExample('Engineering students')">
                    <span class="chip-emoji">💻</span>Engineers
                </button>
                <button class="example-chip" onclick="useExample('Monday morning office')">
                    <span class="chip-emoji">😴</span>Monday Blues
                </button>
                <button class="example-chip" onclick="useExample('Diet pe rehne wale')">
                    <span class="chip-emoji">🥗</span>Diet Wale
                </button>
                
                <button class="example-chip hidden hindi-extra" onclick="useExample('Online shopping addiction')">
                    <span class="chip-emoji">🛒</span>Shopaholic
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Netflix binge watchers')">
                    <span class="chip-emoji">📺</span>Netflix Addicts
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Subah jaldi uthne wale')">
                    <span class="chip-emoji">⏰</span>Early Birds
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Cricket experts on social media')">
                    <span class="chip-emoji">🏏</span>Cricket Experts
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Foodies jo sab kuch khaate hain')">
                    <span class="chip-emoji">🍕</span>Foodies
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Procrastinators')">
                    <span class="chip-emoji">⏳</span>Kal Karte Hain
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Selfie lovers')">
                    <span class="chip-emoji">🤳</span>Selfie Queens
                </button>
                <button class="example-chip hidden hindi-extra" onclick="useExample('Overthinkers')">
                    <span class="chip-emoji">🧠</span>Sochte Rehne Wale
                </button>
            </div>
            
            <!-- ENGLISH CHIPS -->
            <div class="example-chips" id="englishChips" style="display: none;">
                <button class="example-chip" onclick="useExample('Gym people')">
                    <span class="chip-emoji">💪</span>Gym Bros
                </button>
                <button class="example-chip" onclick="useExample('Software engineers')">
                    <span class="chip-emoji">💻</span>Engineers
                </button>
                <button class="example-chip" onclick="useExample('Monday mornings')">
                    <span class="chip-emoji">😴</span>Monday Blues
                </button>
                <button class="example-chip" onclick="useExample('People on diet')">
                    <span class="chip-emoji">🥗</span>Diet People
                </button>
                
                <button class="example-chip hidden english-extra" onclick="useExample('Online shopping addicts')">
                    <span class="chip-emoji">🛒</span>Shopaholics
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Netflix binge watchers')">
                    <span class="chip-emoji">📺</span>Netflix Addicts
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Early morning people')">
                    <span class="chip-emoji">⏰</span>Early Birds
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Social media experts')">
                    <span class="chip-emoji">📱</span>SM Experts
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Foodies')">
                    <span class="chip-emoji">🍕</span>Foodies
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Procrastinators')">
                    <span class="chip-emoji">⏳</span>Procrastinators
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Selfie addicts')">
                    <span class="chip-emoji">🤳</span>Selfie Addicts
                </button>
                <button class="example-chip hidden english-extra" onclick="useExample('Overthinkers')">
                    <span class="chip-emoji">🧠</span>Overthinkers
                </button>
            </div>
            
            <button class="more-options-btn" id="moreOptionsBtn" onclick="toggleMoreOptions()">
                + More Options
            </button>
        </div>

        <div class="loading-container" id="loadingContainer">
            <div class="loading-ring"></div>
            <div class="loading-text" id="loadingText">Loading roast...</div>
        </div>

        <div class="result-card" id="resultCard">
            <img src="" alt="Roasted" class="result-image" id="resultImage">
            <div class="action-buttons">
                <button class="whatsapp-btn" id="whatsappBtn" onclick="shareToWhatsApp()">
                    📱 WhatsApp
                </button>
                <button class="instagram-btn" id="instagramBtn" onclick="shareToInstagram()">
                    📸 Instagram
                </button>
                <button class="download-btn" id="downloadBtn" onclick="downloadResult()">
                    ⬇️ Download
                </button>
                <button class="retry-btn" onclick="reset()">
                    🔄 Again
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
        
        const loadingMessagesHindi = [
            "Teri pehchaan dhundh raha hoon...",
            "Relatable content load ho raha hai...",
            "Tera label ban raha hai...",
            "Sach kadwa hota hai, ready ho ja...",
            "Teri aukat calculate ho rahi hai...",
            "Aaine mein dekhne ka waqt aa gaya...",
            "Reality check loading...",
            "Tera roast pak raha hai..."
        ];
        
        const loadingMessagesEnglish = [
            "Finding your identity...",
            "Loading relatable content...",
            "Creating your label...",
            "Truth hurts, get ready...",
            "Calculating your reality...",
            "Mirror check loading...",
            "Reality check incoming...",
            "Cooking your roast..."
        ];

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
                input.placeholder = "Kisko roast karna hai? Bol na...";
                document.getElementById('examplesLabel').textContent = "🎯 Sabse Popular Bezati:";
                document.getElementById('statusText').textContent = "Savage Mode: ON";
                document.getElementById('tickerText').textContent = "Log Roast Hue Aaj";
                document.getElementById('headlineText').innerHTML = 'Apni <span class="accent">Pehchaan</span> Dekh';
                document.getElementById('subtextText').textContent = "Wo roast jo tujhe khud mein dikhega. 100% relatable! 🪞";
            } else {
                input.placeholder = "Who do you want to roast?";
                document.getElementById('examplesLabel').textContent = "🎯 Most Popular Roasts:";
                document.getElementById('statusText').textContent = "Savage Mode: ON";
                document.getElementById('tickerText').textContent = "People Roasted Today";
                document.getElementById('headlineText').innerHTML = 'See Your <span class="accent">True Self</span>';
                document.getElementById('subtextText').textContent = "Roasts that hit too close to home. 100% relatable! 🪞";
            }
            
            moreOptionsExpanded = false;
            document.getElementById('moreOptionsBtn').textContent = '+ More Options';
            document.getElementById('moreOptionsBtn').classList.remove('expanded');
            hideExtraChips();
        }

        function toggleMoreOptions() {
            moreOptionsExpanded = !moreOptionsExpanded;
            const btn = document.getElementById('moreOptionsBtn');
            
            if (moreOptionsExpanded) {
                btn.textContent = '− Less Options';
                btn.classList.add('expanded');
                showExtraChips();
            } else {
                btn.textContent = '+ More Options';
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
                    ? 'Abe kuch toh likh! Khaali mein kya roast karun? 🤡' 
                    : 'Type something first! Cannot roast empty air 🤡';
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
            }, 1200);

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
                    ? 'Kuch gadbad ho gayi! Dobara try kar! 😤' 
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
                ? encodeURIComponent('Dekh meri kaise bezati hui 🔥😂 - Tu bhi try kar: ' + window.location.href)
                : encodeURIComponent('Check out my roast 🔥😂 - Try it yourself: ' + window.location.href);
            window.open('https://wa.me/?text=' + text, '_blank');
        }

        function shareToInstagram() {
            downloadResult();
            const msg = currentLanguage === 'hindi' 
                ? 'Image download ho gaya! 📸 Ab Instagram pe daal!' 
                : 'Image downloaded! 📸 Now share it on Instagram!';
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
    """Save roast to PostgreSQL database"""
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
            print(f"✅ Roast saved to database")
        except Exception as e:
            print(f"❌ Database save error: {e}")
        finally:
            conn.close()

def get_total_roasts():
    """Get total roast count from database"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT total_roasts FROM stats WHERE id = 1')
            result = cursor.fetchone()
            return result['total_roasts'] if result else 14203
        except Exception as e:
            print(f"❌ Database read error: {e}")
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
    """Generate 2-part roast: Identity Label + Relatable One-Liner"""
    
    if language == 'hindi':
        system_prompt = """
Tu ek comedy writer hai jo RELATABLE roasts likhta hai. Tujhe 2 cheezein deni hain:

### OUTPUT FORMAT (STRICTLY FOLLOW):
LABEL: [1-2 word funny Hindi title]
ROAST: [Relatable one-liner that everyone can relate to]

### RULES:

1. **LABEL** = Short funny identity (1-2 words max) in Hindi
   Examples: "Aalsi Insaan", "Gym Fraud", "Diet Topper", "Sapno Ka Saudagar", "Permanently Broke", "Tunda Expert"

2. **ROAST** = Relatable one-liner (max 15 words)
   - Something EVERYONE can relate to
   - No gaali/abuse - just witty observation
   - Should make people say "Haan yaar ye toh main hi hoon!"
   
### RELATABLE EXAMPLES:

Topic: "Gym jaane wale log"
LABEL: Gym Fraud
ROAST: Gym membership lena hi workout tha, ab body bhi chahiye?

Topic: "Monday morning"
LABEL: Somvaar Victim  
ROAST: Alarm snooze karna bhi ek talent hai, 47 baar kiya subah.

Topic: "Diet pe rehne wale"
LABEL: Diet Topper
ROAST: Salad order kiya, fir uske saath extra cheese garlic bread bhi.

Topic: "Engineering students"
LABEL: Branch Topper
ROAST: 4 saal padhai ki fees di, ab LinkedIn pe "Open to Work" laga diya.

Topic: "Online shopping"
LABEL: Shopaholic
ROAST: Sale ka matlab hai: wo cheez lena jo pehle bhi nahi chahiye thi.

### IMPORTANT:
- Be FUNNY not OFFENSIVE
- Be RELATABLE - majority should connect
- Keep it LIGHT and WITTY
- NO abuse/gaali - family friendly savage

Topic to roast: """

    else:
        system_prompt = """
You are a comedy writer who writes RELATABLE roasts. You need to give 2 things:

### OUTPUT FORMAT (STRICTLY FOLLOW):
LABEL: [1-2 word funny English title]
ROAST: [Relatable one-liner that everyone can relate to]

### RULES:

1. **LABEL** = Short funny identity (1-2 words max)
   Examples: "Gym Fraud", "Diet Disaster", "Sleep Champion", "Professional Procrastinator", "Netflix PhD"

2. **ROAST** = Relatable one-liner (max 15 words)
   - Something EVERYONE can relate to
   - No abuse - just witty observation
   - Should make people say "That's literally me!"
   
### RELATABLE EXAMPLES:

Topic: "Gym people"
LABEL: Gym Fraud
ROAST: Buying the gym membership was the workout.

Topic: "Monday mornings"
LABEL: Monday Victim
ROAST: My bed and I have a special relationship. The alarm is just jealous.

Topic: "People on diet"
LABEL: Diet Disaster
ROAST: Ordered a salad, then rewarded myself with a pizza for being healthy.

Topic: "Software engineers"
LABEL: Code Monkey
ROAST: Mass applied to 500 jobs, now waiting for rejection emails to feel wanted.

Topic: "Online shopping"
LABEL: Cart Champion
ROAST: Added to cart at 2am, regretted at 2pm when it arrived.

Topic: "Procrastinators"
LABEL: Tomorrow Expert
ROAST: I'll start being productive tomorrow. Said that yesterday too.

### IMPORTANT:
- Be FUNNY not OFFENSIVE
- Be RELATABLE - majority should connect
- Keep it LIGHT and WITTY
- NO abuse - family friendly savage

Topic to roast: """

    for model_index, model_name in enumerate(AI_MODELS):
        try:
            print(f"Trying model {model_index + 1}/{len(AI_MODELS)}: {model_name}")
            
            completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": topic}
                ],
                model=model_name,
                temperature=1.0,
                max_tokens=100,
                top_p=1,
            )
            
            response = completion.choices[0].message.content.strip()
            
            # Parse the response
            label = ""
            roast = ""
            
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.upper().startswith('LABEL:'):
                    label = line.split(':', 1)[1].strip().strip('"').strip("'")
                elif line.upper().startswith('ROAST:'):
                    roast = line.split(':', 1)[1].strip().strip('"').strip("'")
            
            # Clean up
            label = label.replace('**', '').replace('*', '').strip()
            roast = roast.replace('**', '').replace('*', '').strip()
            
            # Fallback if parsing failed
            if not label or not roast:
                if language == 'hindi':
                    label = "Certified Pagal"
                    roast = response[:80] if len(response) > 10 else "Tujhe roast karne se pehle tujhe samajhna padega, wo impossible hai."
                else:
                    label = "Certified Clown"
                    roast = response[:80] if len(response) > 10 else "You're so unique that even AI couldn't categorize you."
            
            print(f"✅ Success with {model_name}")
            print(f"   Label: {label}")
            print(f"   Roast: {roast}")
            
            return label, roast
        
        except Exception as e:
            print(f"❌ Model {model_name} failed: {e}")
            if model_index < len(AI_MODELS) - 1:
                print("Switching to backup model...")
                continue
    
    # Fallback roasts
    print("All AI models failed, using fallback")
    
    if language == 'hindi':
        fallbacks = [
            ("Certified Aalsi", "Kal se pakka kuch karunga, ye kal kabhi nahi aata."),
            ("Expert Bahanebaz", "Bohot kaam hai aaj, isliye Netflix pe 3 season dekh liye."),
            ("Pro Procrastinator", "Deadline kal hai? Perfect, aaj toh chill karta hoon."),
        ]
    else:
        fallbacks = [
            ("Certified Lazy", "I'll definitely do it tomorrow. Same thing I said yesterday."),
            ("Expert Excuser", "Too busy to work, but watched an entire Netflix series today."),
            ("Pro Procrastinator", "Deadline tomorrow? Perfect day to reorganize my desk."),
        ]
    
    return random.choice(fallbacks)


def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width"""
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
    """Add Identity Label (top) and Roast (bottom) to image"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    img_width, img_height = img.size
    
    # ===== TOP: IDENTITY LABEL =====
    label_font_size = int(img_height * 0.08)
    label_font = get_font(label_font_size)
    
    # Get label dimensions
    label_bbox = label_font.getbbox(label.upper())
    label_width = label_bbox[2] - label_bbox[0]
    label_height = label_bbox[3] - label_bbox[1]
    
    # Position at top center
    label_x = (img_width - label_width) // 2
    label_y = 40
    
    # Draw label background (orange/red banner)
    padding = 20
    banner_left = label_x - padding
    banner_top = label_y - padding // 2
    banner_right = label_x + label_width + padding
    banner_bottom = label_y + label_height + padding
    
    # Draw banner rectangle
    draw.rectangle(
        [banner_left, banner_top, banner_right, banner_bottom],
        fill='#FF4500'
    )
    
    # Draw label text (white on orange)
    draw.text(
        (label_x, label_y),
        label.upper(),
        font=label_font,
        fill="white"
    )
    
    # ===== BOTTOM: RELATABLE ROAST =====
    roast_font_size = int(img_height * 0.055)
    roast_font = get_font(roast_font_size)
    
    max_width = int(img_width * 0.88)
    lines = wrap_text(roast, roast_font, max_width)
    
    line_height = roast_font_size + 10
    total_text_height = len(lines) * line_height
    
    # Position at bottom
    y_position = img_height - total_text_height - 50
    
    for line in lines:
        bbox = roast_font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x_position = (img_width - text_width) // 2
        
        # Draw outline (black)
        outline_range = 3
        for adj_x in range(-outline_range, outline_range + 1):
            for adj_y in range(-outline_range, outline_range + 1):
                draw.text(
                    (x_position + adj_x, y_position + adj_y),
                    line,
                    font=roast_font,
                    fill="black"
                )
        
        # Draw main text (white/gold)
        draw.text(
            (x_position, y_position),
            line,
            font=roast_font,
            fill="#FFFFFF"
        )
        
        y_position += line_height
    
    return img


def save_to_supabase(topic, roast_text, image_buffer, language='hindi'):
    """Save image to Supabase storage (optional)"""
    if supabase is None:
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"roast_{timestamp}_{random.randint(1000, 9999)}.jpg"
        
        image_buffer.seek(0)
        supabase.storage.from_("memes").upload(
            filename,
            image_buffer.read(),
            file_options={"content-type": "image/jpeg"}
        )
        
        public_url = supabase.storage.from_("memes").get_public_url(filename)
        print(f"✅ Image saved to Supabase: {filename}")
        return public_url
        
    except Exception as e:
        print(f"⚠️ Supabase Error: {e}")
        return None


# ===== ROUTES =====
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/stats')
def get_stats():
    """API endpoint to get roast statistics"""
    total = get_total_roasts()
    return jsonify({
        "total_roasts": total,
        "status": "success"
    })


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
        # Generate 2-part roast
        label, roast_text = get_roast(topic, language)
        
        # Create meme image
        random_meme = random.choice(meme_files)
        meme_path = os.path.join(MEMES_FOLDER, random_meme)
        final_image = add_text_to_image(meme_path, label, roast_text)
        
        img_io = BytesIO()
        final_image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        
        # Save to database
        save_roast_to_db(topic, label, roast_text, language)
        
        # Optionally save to Supabase
        try:
            save_to_supabase(topic, roast_text, BytesIO(img_io.getvalue()), language)
        except Exception as e:
            print(f"Supabase save failed: {e}")
        
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    db_status = "connected"
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
        else:
            db_status = "disconnected"
    except:
        db_status = "error"
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "supabase": "connected" if supabase else "not configured",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    if not os.path.exists(MEMES_FOLDER):
        os.makedirs(MEMES_FOLDER)
        print(f"📁 Created '{MEMES_FOLDER}' folder - add meme images here!")
    
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
