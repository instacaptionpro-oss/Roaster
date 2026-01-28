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

load_dotenv()

# Enable static file serving
app = Flask(__name__, static_folder='static', static_url_path='/static')

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

supabase = None
if supabase_url and supabase_key:
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        print("Supabase connected successfully")
    except Exception as e:
        print(f"Supabase connection failed: {e}")
        supabase = None
else:
    print("Supabase credentials not found")

MEMES_FOLDER = "memes"

# AI Model Configuration (Primary + Backups)
AI_MODELS = [
    "llama-3.3-70b-versatile",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.1-70b-versatile"
]

# ===== FRONTEND HTML WITH BACKGROUND IMAGE =====
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Roaster AI - Silence Your Ego</title>
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
            padding: 80px 24px;
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
            font-size: clamp(3rem, 8vw, 5.5rem);
            font-weight: 900;
            letter-spacing: -3px;
            line-height: 1.1;
            margin-bottom: 24px;
            color: #fff;
            text-shadow: 0 4px 20px rgba(0, 0, 0, 0.9);
        }

        .hero-headline .accent {
            color: #FF4500;
            text-shadow: 0 0 40px rgba(255, 69, 0, 0.8);
        }

        .hero-subtext {
            font-size: 1.25rem;
            color: #fff;
            font-weight: 400;
            margin-bottom: 40px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            text-shadow: 0 2px 15px rgba(0, 0, 0, 0.9);
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

        .input-engine {
            position: relative;
            max-width: 700px;
            margin: 0 auto 48px;
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
                padding: 48px 20px;
            }

            .hero-headline {
                font-size: 2.5rem;
            }

            .hero-subtext {
                font-size: 1rem;
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
            <span>Gali Mode: ON</span>
        </div>
    </nav>

    <div class="container">
        <div class="warning-badge">
            ⚠️ 18+ Content | Gaaliyon ka Guarantee
        </div>

        <div class="live-ticker">
            <span class="ticker-icon">🔥</span>
            <span id="egoCounter">14,203</span> Bezati Hui Aaj
        </div>

        <h1 class="hero-headline">
            Teri <span class="accent">Bezati</span> Free Mein
        </h1>
        <p class="hero-subtext">
            Itna roast karega ki teri aatma bhi cringe karegi. Maa kasam no filter! 🤡
        </p>

        <!-- ===== EXAMPLE CHIPS ===== -->
        <div class="examples-section">
            <p class="examples-label">🎯 Seedha Bezati Shuru Kar:</p>
            <div class="example-chips">
                <button class="example-chip" onclick="useExample('Meri ex jo mujhe chod ke mere dost ke saath bhaag gayi')">
                    <span class="chip-emoji">💔</span>Randi Ex
                </button>
                <button class="example-chip" onclick="useExample('Mera dost jo hamesha mera paisa khaata hai')">
                    <span class="chip-emoji">💸</span>Chor Dost
                </button>
                <button class="example-chip" onclick="useExample('LinkedIn pe rozgar dhundhne wale engineers')">
                    <span class="chip-emoji">💻</span>Berozgar Engineers
                </button>
                <button class="example-chip" onclick="useExample('Gym jaake sirf selfie leta hai')">
                    <span class="chip-emoji">💪</span>Nakli Gym Bro
                </button>
                <button class="example-chip" onclick="useExample('Mummy Papa ki expectations')">
                    <span class="chip-emoji">👨‍👩‍👦</span>Sharma Ji Ka Beta
                </button>
                <button class="example-chip" onclick="useExample('Crypto mein paisa doobaya')">
                    <span class="chip-emoji">📉</span>Gawar Crypto Bro
                </button>
                <button class="example-chip" onclick="useExample('Exam ke ek raat pehle padhne wale')">
                    <span class="chip-emoji">📚</span>Nalayak Student
                </button>
                <button class="example-chip" onclick="useExample('500 followers wala influencer')">
                    <span class="chip-emoji">📱</span>Chapri Influencer
                </button>
                <button class="example-chip" onclick="useExample('Shaadi mein rishtedar')">
                    <span class="chip-emoji">👴</span>Gandu Rishtedaar
                </button>
                <button class="example-chip" onclick="useExample('Startup founder bina funding ke')">
                    <span class="chip-emoji">🚀</span>Fattu Startup Bro
                </button>
                <button class="example-chip" onclick="useExample('Tinder pe serious relationship dhundh raha')">
                    <span class="chip-emoji">🔥</span>Tharki Tinder User
                </button>
                <button class="example-chip" onclick="useExample('Monday subah ka alarm')">
                    <span class="chip-emoji">😴</span>Monday Ki M**
                </button>
                <button class="example-chip" onclick="useExample('Mera boss jo khud kuch nahi karta')">
                    <span class="chip-emoji">🤡</span>Chutiya Boss
                </button>
                <button class="example-chip" onclick="useExample('Wo ladka jo har ladki ko bhabhi bolta hai')">
                    <span class="chip-emoji">🙏</span>Bhabhi Simp
                </button>
                <button class="example-chip" onclick="useExample('PUBG khel ke pro player samjhta hai')">
                    <span class="chip-emoji">🎮</span>Noob Gamer
                </button>
            </div>
        </div>

        <div class="input-engine">
            <div class="command-line">
                <span class="command-prefix">></span>
                <input 
                    type="text" 
                    class="command-input" 
                    id="topicInput"
                    placeholder="Kisko gaali deni hai? Bol na bsdk..."
                    maxlength="100"
                >
                <button class="execute-btn" id="executeBtn" onclick="executeRoast()">
                    <svg class="arrow-icon" viewBox="0 0 24 24">
                        <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
                    </svg>
                </button>
            </div>
        </div>

        <div class="loading-container" id="loadingContainer">
            <div class="loading-ring"></div>
            <div class="loading-text" id="loadingText">Gaaliyan load ho rahi hain...</div>
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
                    🔄 Aur Gaali
                </button>
            </div>
        </div>

        <div class="error-message" id="errorMessage"></div>
    </div>

    <script>
        let currentImageUrl = '';
        let currentTopic = '';
        
        const loadingMessages = [
            "Gaaliyan load ho rahi hain...",
            "Teri izzat ki kabar khod raha hoon...",
            "Satan se teri report maang raha hoon...",
            "Tera janam kundali dekh raha hoon...",
            "Teri aukat calculate ho rahi hai...",
            "Teri L lag rahi hai wait kar...",
            "Teri mummy ko call laga raha hoon...",
            "Bohot bura hone wala hai tere saath...",
            "Emotional damage loading...",
            "Teri bezati ka script likh raha hoon...",
            "Sharma ji ke bete se comparison ho raha...",
            "Tera future dekh ke AI bhi ro diya...",
            "Tere failures count ho rahe hain..."
        ];

        // Animate ego counter
        function animateCounter() {
            const counter = document.getElementById('egoCounter');
            let count = 14203;
            setInterval(() => {
                count += Math.floor(Math.random() * 5);
                counter.textContent = count.toLocaleString();
            }, 2000);
        }
        animateCounter();

        // Use example chip
        function useExample(topic) {
            document.getElementById('topicInput').value = topic;
            document.getElementById('topicInput').focus();
            
            // Add a little animation feedback
            const input = document.getElementById('topicInput');
            input.style.background = 'rgba(255, 69, 0, 0.2)';
            setTimeout(() => {
                input.style.background = 'transparent';
            }, 300);
        }

        // Enter key support
        document.getElementById('topicInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                executeRoast();
            }
        });

        async function executeRoast() {
            const topic = document.getElementById('topicInput').value.trim();
            
            if (!topic) {
                showError('Abe kuch toh likh! Khaali mein kya roast karun? 🤡');
                return;
            }

            currentTopic = topic;
            
            // Hide previous results and errors
            document.getElementById('resultCard').classList.remove('active');
            document.getElementById('errorMessage').classList.remove('active');
            
            // Show loading
            document.getElementById('loadingContainer').classList.add('active');
            document.getElementById('executeBtn').disabled = true;

            // Cycle loading messages
            let msgIndex = 0;
            const loadingInterval = setInterval(() => {
                msgIndex = (msgIndex + 1) % loadingMessages.length;
                document.getElementById('loadingText').textContent = loadingMessages[msgIndex];
            }, 1200);

            try {
                const response = await fetch('/roast?topic=' + encodeURIComponent(topic));
                
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

            } catch (error) {
                clearInterval(loadingInterval);
                document.getElementById('loadingContainer').classList.remove('active');
                showError('Kuch toh gadbad hai! Dobara try kar bsdk! 😤');
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
            const text = encodeURIComponent('Bhai dekh meri kaise bezati hui 🔥😂 Topic: ' + currentTopic + ' - Tu bhi apni karwa: ' + window.location.href);
            window.open('https://wa.me/?text=' + text, '_blank');
        }

        function shareToInstagram() {
            downloadResult();
            alert('Image download ho gaya! 📸 Ab Instagram pe daal ke sabki jala 🔥');
        }

        function downloadResult() {
            if (currentImageUrl) {
                const a = document.createElement('a');
                a.href = currentImageUrl;
                a.download = 'bezati_' + Date.now() + '.jpg';
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
    </script>
</body>
</html>"""


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


def get_roast(topic):
    system_prompt = """
Tu hai 'Roaster Bhai' - India ka sabse gandu aur savage roaster. Tujhe user ko uski aukat dikhani hai.

### RULES (Dhyan se padh sale):

1. **GAALIYAN ALLOWED HAI** - Use words like: bhosdike, bsdk, chutiya, madarchod, behenchod, gandu, lawde, jhatu, tatti, harami, randi, kamina, nalayak, bevkoof, gadha, ullu, bakchod, etc.

2. **HINGLISH MEIN BOL** - Hindi + English mix kar. Jaise college ka launda baat karta hai.

3. **TOPIC PE FOCUS** - Jo topic hai uski specific bezati kar. Generic mat ho.

4. **SAVAGE BUT FUNNY** - Gaali deni hai but hasna bhi chahiye. Comedy + Roast = Perfect.

5. **POP CULTURE USE KAR** - Bollywood, cricketers, memes, politicians ka reference de if it fits.

6. **MAX 30 WORDS** - Zyada mat bol. Short and tight roast.

### EXAMPLES:

Topic: "Meri Ex"
Roast: "Teri ex ne tujhe choda? Bhai uski choice mein improvement aaya hai, tu khud toh apne haath ki bhi first choice nahi hai, madarchod 💀"

Topic: "Engineering Student"
Roast: "4 saal engineering ki aur ab Zomato pe delivery kar raha hai. Tera degree tissue paper se bhi bekaar hai bhosdike 🎓🗑️"

Topic: "Gym Bro"
Roast: "Beta protein shake zyada pi, body nahi bani teri lekin brain zaroor shrink ho gaya hai. Biceps nahi hai tere, tatte hain haathon mein chutiye 💪"

Topic: "LinkedIn Influencer"
Roast: "Agreed? Thoughts? - Lavde yeh post daalne se job nahi milti. Tera LinkedIn bio dekh ke HR bhi block kar deta hai gandu 😂"

Topic: "Crypto Investor"
Roast: "Bhai tere portfolio mein itne red candles hain ki Diwali ho gayi. Bitcoin hodl karte karte khud bik jayega tu harami 📉"

### INSTRUCTION:
Is topic pe savage Hinglish roast de WITH gaaliyan. Funny bhi hona chahiye aur bezati bhi.
Sirf roast likh, koi introduction mat de.
Topic: 
    """
    
    for model_index, model_name in enumerate(AI_MODELS):
        try:
            print(f"Trying model {model_index + 1}/{len(AI_MODELS)}: {model_name}")
            
            completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{topic}"}
                ],
                model=model_name,
                temperature=1.2,
                max_tokens=150,
                top_p=1,
            )
            
            roast_text = completion.choices[0].message.content.strip()
            roast_text = roast_text.strip('"').strip("'")
            roast_text = roast_text.replace('**', '').replace('*', '')
            
            print(f"Success with {model_name}")
            return roast_text
        
        except Exception as e:
            error_msg = str(e).lower()
            print(f"Model {model_name} failed: {e}")
            
            if "rate" in error_msg or "limit" in error_msg or "quota" in error_msg:
                if model_index < len(AI_MODELS) - 1:
                    print("Switching to backup model...")
                    continue
            else:
                if model_index < len(AI_MODELS) - 1:
                    continue
    
    print("All AI models failed, using fallback roast")
    fallbacks = [
        f"Bhai {topic}? Teri life itni sad hai ki AI bhi tujhpe roast likhne se mana kar diya. Khud hi itna bada joke hai tu chutiye 💀",
        f"{topic} ke baare mein kya bolun? Tera existence hi sabse bada roast hai bhosdike 😂",
        f"AI ne 3 baar try kiya {topic} roast karne ka par haar gaya. Tu roast-proof nahi hai, tu itna bekar hai ki roast karne layak bhi nahi hai gandu 🤡",
        f"Bhai {topic}? Sharma ji ka beta bhi tujhse better hai. Ja jaake chai bana nalayak 🍵",
        f"{topic} ko roast karne gaya tha, teri puri life history dekh ke AI depression mein chala gaya madarchod 😭"
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


def add_text_to_image(image_path, text):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    img_width, img_height = img.size
    
    font_size = int(img_height * 0.07)
    font = get_font(font_size)
    
    max_width = int(img_width * 0.88)
    lines = wrap_text(text, font, max_width)
    
    line_height = font_size + 12
    total_text_height = len(lines) * line_height
    
    y_position = img_height - total_text_height - 60
    
    for line in lines:
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x_position = (img_width - text_width) // 2
        
        outline_range = 4
        for adj_x in range(-outline_range, outline_range + 1):
            for adj_y in range(-outline_range, outline_range + 1):
                draw.text(
                    (x_position + adj_x, y_position + adj_y),
                    line,
                    font=font,
                    fill="black"
                )
        
        draw.text(
            (x_position, y_position),
            line,
            font=font,
            fill="#FFD700"
        )
        
        y_position += line_height
    
    return img


def save_to_supabase(topic, roast_text, image_buffer):
    if supabase is None:
        print("Supabase not configured")
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"roast_{timestamp}_{random.randint(1000, 9999)}.jpg"
        
        image_buffer.seek(0)
        response = supabase.storage.from_("memes").upload(
            filename,
            image_buffer.read(),
            file_options={"content-type": "image/jpeg"}
        )
        
        public_url = supabase.storage.from_("memes").get_public_url(filename)
        
        data = {
            "topic": topic,
            "roast_text": roast_text,
            "image_url": public_url,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("roasts").insert(data).execute()
        
        print(f"Saved to Supabase: {filename}")
        return public_url
        
    except Exception as e:
        print(f"Supabase Error: {e}")
        return None


# ===== ROUTES =====
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route('/roast', methods=['GET'])
def roast():
    topic = request.args.get('topic', '').strip()
    
    if not topic:
        return jsonify({"error": "Kuch toh likh pehle!"}), 400
    
    if not os.path.exists(MEMES_FOLDER):
        return jsonify({"error": "Memes folder not found"}), 500
    
    meme_files = [f for f in os.listdir(MEMES_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not meme_files:
        return jsonify({"error": "No meme images found"}), 500
    
    try:
        roast_text = get_roast(topic)
        
        random_meme = random.choice(meme_files)
        meme_path = os.path.join(MEMES_FOLDER, random_meme)
        final_image = add_text_to_image(meme_path, roast_text)
        
        img_io = BytesIO()
        final_image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        
        try:
            save_to_supabase(topic, roast_text, BytesIO(img_io.getvalue()))
        except Exception as e:
            print(f"Supabase save failed: {e}")
        
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
