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
        print("✅ Supabase connected successfully")
    except Exception as e:
        print(f"⚠️ Supabase connection failed: {e}")
        supabase = None
else:
    print("⚠️ Supabase credentials not found")

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
    <!-- (paste the full HTML content from the Index.html file provided above here) -->
</head>
<body>
    <!-- (rest of the HTML) -->
</body>
</html>
"""
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
            
            /* BACKGROUND IMAGE */
            background-image: url('https://i.postimg.cc/R0g9tGYB/Mr.jpg');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }

        /* Dark overlay for text readability */
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
            margin-bottom: 64px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            text-shadow: 0 2px 15px rgba(0, 0, 0, 0.9);
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
            <span>System Online</span>
        </div>
    </nav>

    <div class="container">
        <div class="live-ticker">
            <span class="ticker-icon">🔥</span>
            <span id="egoCounter">14,203</span> Egos Destroyed Today
        </div>

        <h1 class="hero-headline">
            Silence Your <span class="accent">Ego.</span>
        </h1>
        <p class="hero-subtext">
            The AI that humbles you. No Filters. Just Reality.
        </p>

        <div class="input-engine">
            <div class="command-line">
                <span class="command-prefix">></span>
                <input 
                    type="text" 
                    class="command-input" 
                    id="topicInput"
                    placeholder="Roast my Ex / Boss / Life..."
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
            <div class="loading-text" id="loadingText">Consulting with Satan...</div>
        </div>

        <div class="result-card" id="resultCard">
            <img src="" alt="Roasted" class="result-image" id="resultImage">
            <div class="action-buttons">
                <button class="whatsapp-btn" id="whatsappBtn" onclick="shareToWhatsApp()">
                    📱 Share on WhatsApp
                </button>
                <button class="instagram-btn" id="instagramBtn" onclick="shareToInstagram()">
                    📸 Share to Instagram
                </button>
                <button class="download-btn" id="downloadBtn" onclick="downloadResult()">
                    ⬇️ Download
                </button>
                <button class="retry-btn" onclick="reset()">
                    🔄 Roast Again
                </button>
            </div>
        </div>

        <div class="error-message" id="errorMessage"></div>
    </div>

    <script>
        const API_URL = window.location.origin;

        let egoCount = 14203;
        setInterval(() => {
            egoCount += Math.floor(Math.random() * 3);
            document.getElementById('egoCounter').textContent = egoCount.toLocaleString();
        }, 5000);

        const loadingMessages = [
            "Consulting with Satan...",
            "Analyzing your bad life choices...",
            "Finding the ugliest meme template...",
            "Calculating emotional damage...",
            "Waking up the demons...",
            "Preparing maximum destruction..."
        ];

        let loadingInterval;
        let currentTopic = "";
        let lastImageBlob = null;
        let lastImageBlobUrl = null;

        async function executeRoast() {
            const topic = document.getElementById('topicInput').value.trim();
            
            if (!topic) {
                showError('Enter something to roast! 😤');
                return;
            }

            currentTopic = topic;

            document.getElementById('resultCard').classList.remove('active');
            document.getElementById('errorMessage').classList.remove('active');
            document.getElementById('loadingContainer').classList.add('active');
            document.getElementById('executeBtn').disabled = true;

            let msgIndex = 0;
            document.getElementById('loadingText').textContent = loadingMessages[0];
            
            loadingInterval = setInterval(() => {
                msgIndex = (msgIndex + 1) % loadingMessages.length;
                document.getElementById('loadingText').textContent = loadingMessages[msgIndex];
            }, 2000);

            try {
                const timestamp = Date.now();
                const url = `${API_URL}/roast?topic=${encodeURIComponent(topic)}&t=${timestamp}`;
                
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 25000);

                const response = await fetch(url, {
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error('Server error');
                }

                const blob = await response.blob();
                // store blob for sharing/downloading
                lastImageBlob = blob;
                const imageUrl = URL.createObjectURL(blob);
                lastImageBlobUrl = imageUrl;

                document.getElementById('resultImage').src = imageUrl;
                document.getElementById('resultCard').classList.add('active');
                
            } catch (error) {
                if (error.name === 'AbortError') {
                    showError('Server is waking up. Please try again! 😴');
                } else {
                    showError('Something went wrong. Try again! 💀');
                }
                console.error(error);
            } finally {
                document.getElementById('loadingContainer').classList.remove('active');
                document.getElementById('executeBtn').disabled = false;
                clearInterval(loadingInterval);
            }
        }

        async function shareToWhatsApp() {
            try {
                if (navigator.share && lastImageBlob) {
                    // Use Web Share API with file (mobile browsers)
                    const file = new File([lastImageBlob], `roast-${Date.now()}.jpg`, { type: lastImageBlob.type || 'image/jpeg' });
                    await navigator.share({
                        files: [file],
                        text: `My ego just got destroyed by AI 💀. Only legends can handle this. Try it: ${window.location.href}`
                    });
                } else {
                    // Fallback to wa.me text share
                    const message = `My ego just got destroyed by AI 💀. Only legends can handle this. Try it: ${window.location.href}`;
                    const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(message)}`;
                    window.open(whatsappUrl, '_blank');
                }
            } catch (err) {
                console.error('WhatsApp share failed', err);
                showError('Sharing failed. Try downloading and sharing manually.');
            }
        }

        async function shareToInstagram() {
            try {
                if (navigator.share && lastImageBlob) {
                    // Attempt Web Share API with file (best on mobile)
                    const file = new File([lastImageBlob], `roast-${Date.now()}.jpg`, { type: lastImageBlob.type || 'image/jpeg' });
                    await navigator.share({
                        files: [file],
                        text: `Roast: ${currentTopic}`
                    });
                } else {
                    // Instagram doesn't support prefilled image uploads via web reliably.
                    showError('Direct Instagram sharing not supported in this browser. Download and upload to Instagram.');
                    // Open Instagram website as a convenience
                    window.open('https://www.instagram.com/', '_blank');
                }
            } catch (err) {
                console.error('Instagram share failed', err);
                showError('Sharing failed. Try downloading and uploading manually.');
            }
        }

        function downloadResult() {
            if (!lastImageBlobUrl) {
                showError('No image available to download.');
                return;
            }

            const a = document.createElement('a');
            a.href = lastImageBlobUrl;
            a.download = `roast-${Date.now()}.jpg`;
            document.body.appendChild(a);
            a.click();
            a.remove();

            // Optional: revoke object URL after a short delay
            setTimeout(() => {
                try {
                    URL.revokeObjectURL(lastImageBlobUrl);
                } catch (e) {}
            }, 10000);
        }

        function reset() {
            document.getElementById('topicInput').value = '';
            document.getElementById('resultCard').classList.remove('active');
            document.getElementById('topicInput').focus();
            // revoke previous blob URL if any
            if (lastImageBlobUrl) {
                try {
                    URL.revokeObjectURL(lastImageBlobUrl);
                } catch (e) {}
                lastImageBlobUrl = null;
                lastImageBlob = null;
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.classList.add('active');
            
            setTimeout(() => {
                errorDiv.classList.remove('active');
            }, 4000);
        }

        document.getElementById('topicInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                executeRoast();
            }
        });

        window.addEventListener('load', () => {
            document.getElementById('topicInput').focus();
        });
    </script>
</body>
</html>
"""

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
    """
    Generate roast with automatic fallback to backup models
    """
    system_prompt = """
You are 'Roaster', India's most witty and unpredictable Stand-up Comedian.
Your goal is to Roast the user based on the specific topic they provide.

### THE GOLDEN RULES:
1. **CONTEXT IS KING:** Do not just use random slang. If the topic is "Coding", roast the bugs. If the topic is "Love", roast the heartbreak. If the topic is "Gym", roast the protein powder.
2. **NO REPETITION:** Do not rely on "Udhaar", "Momos", or "Chhapri" unless it fits perfectly. Be creative. Use new metaphors every time.
3. **OBSERVATIONAL HUMOR:** Be like a detective. Find the specific insecurity in the topic and attack it.
4. **LANGUAGE:** Natural Hinglish. Speak like a college student talking to his friend.

### TONE:
- Sarcastic, Witty, Fast.
- Less "Abusive", More "Intellectual Damage".
- Use Pop Culture references (Bollywood, Cricketers, memes, Politicians) IF it fits.

### EXAMPLES OF CREATIVE RANGE:

Topic: "My Boss"
Roast: "He acts like the CEO of Google but manages the team like a Whatsapp Group Admin." (Context: Management).

Topic: "I go to the Gym"
Roast: "Body banne se pehle Instagram stories bann gayi. Protein shake kam, photosyanthesis zyada chal raha hai." (Context: Showoff).

Topic: "Python Coding"
Roast: "Tere code mein itne errors hain ki IDE bhi suicide karne ka soch raha hai." (Context: Tech).

Topic: "My Ex"
Roast: "She treated you like a 'Free Trial' subscription. Use kiya, expire hua, aur naya account bana liya." (Context: Modern Tech Metaphor).

### INSTRUCTION:
Generate a savage, unique, and context-specific roast for the user's topic.
Max 25 words.
NO introductory text. Just the roast.
    """
    
    for model_index, model_name in enumerate(AI_MODELS):
        try:
            print(f"🤖 Trying model {model_index + 1}/{len(AI_MODELS)}: {model_name}")
            
            completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Roast this topic with intelligent humor: {topic}"
                    }
                ],
                model=model_name,
                temperature=1.1,
                max_tokens=120,
                top_p=1,
            )
            
            roast_text = completion.choices[0].message.content.strip()
            roast_text = roast_text.strip('"').strip("'")
            roast_text = roast_text.replace('**', '').replace('*', '')
            
            print(f"✅ Success with {model_name}")
            return roast_text
        
        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ Model {model_name} failed: {e}")
            
            if "rate" in error_msg or "limit" in error_msg or "quota" in error_msg:
                if model_index < len(AI_MODELS) - 1:
                    print(f"⏭️ Switching to backup model...")
                    continue
                else:
                    print("⚠️ All models exhausted")
            else:
                if model_index < len(AI_MODELS) - 1:
                    continue
    
    print("💀 All AI models failed, using fallback roast")
    fallbacks = [
        f"Bhai {topic} ko roast karne se pehle khud ko sambhal le, tera future toh already dark mode mein hai 💀",
        f"{topic}? Yeh topic bhi teri love life jaisa hai - kuch hai hi nahi samajhne ko 😂",
        f"AI ne 3 baar try kiya aur haar maan li. {topic} roast-proof hai lagta hai 🤡"
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
        print("⚠️ Supabase not configured")
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
        
        print(f"✅ Saved to Supabase: {filename}")
        return public_url
        
    except Exception as e:
        print(f"❌ Supabase Error: {e}")
        return None

# ===== ROUTES =====
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/roast', methods=['GET'])
def roast():
    topic = request.args.get('topic', '').strip()
    
    if not topic:
        return jsonify({"error": "Please provide a 'topic' parameter"}), 400
    
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
