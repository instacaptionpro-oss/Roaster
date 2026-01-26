import os
import random
import requests
import textwrap
import io
import base64
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from groq import Groq
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
CORS(app)

# --- 1. CONFIGURATION ---
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- 2. THE CINEMATIC FRONTEND (Inside Python) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ROASTER - Silence Your Ego</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #FF4500;
            --glow: rgba(255, 69, 0, 0.6);
            --glass-bg: rgba(0, 0, 0, 0.7);
            --glass-border: rgba(255, 69, 0, 0.3);
            --text-main: #ffffff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: #000;
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            overflow-x: hidden;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .bg-image {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -2;
            background-image: url('https://i.postimg.cc/R0g9tGYB/Mr.jpg'); 
            background-size: cover; background-position: center;
            animation: breathe 15s ease-in-out infinite;
        }
        @keyframes breathe { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
        .bg-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
            background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.8) 60%, #000000 100%);
        }
        #fireCanvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none; }
        nav { padding: 20px; display: flex; justify-content: space-between; align-items: center; z-index: 100; position: relative; }
        .logo { font-weight: 800; font-size: 1.5rem; letter-spacing: -1px; text-shadow: 0 0 20px var(--primary); color: #fff; }
        .status-pill { font-size: 0.7rem; background: rgba(0,0,0,0.8); color: #00ff00; padding: 5px 12px; border-radius: 20px; border: 1px solid rgba(0,255,0,0.3); backdrop-filter: blur(5px); }
        .container { width: 90%; max-width: 600px; margin: 0 auto; text-align: center; flex: 1; display: flex; flex-direction: column; justify-content: center; padding-top: 100px; position: relative; z-index: 10; }
        h1 { font-size: 3.2rem; line-height: 1; font-weight: 800; margin-bottom: 15px; text-shadow: 0 10px 40px rgba(0,0,0,0.9); }
        .highlight { color: var(--primary); text-shadow: 0 0 30px var(--glow); }
        p.subtitle { color: #ddd; font-size: 1.1rem; margin-bottom: 50px; line-height: 1.5; font-weight: 500; text-shadow: 0 2px 10px #000; }
        .input-wrapper { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 50px; padding: 5px; display: flex; align-items: center; box-shadow: 0 20px 50px rgba(0,0,0,0.9); transition: all 0.3s ease; backdrop-filter: blur(12px); }
        .input-wrapper:focus-within { border-color: var(--primary); box-shadow: 0 0 30px rgba(255, 69, 0, 0.4); background: #000; }
        input { flex: 1; background: transparent; border: none; color: white; font-size: 1.1rem; padding: 15px 20px; outline: none; }
        .btn-go { background: var(--primary); color: white; border: none; width: 55px; height: 55px; border-radius: 50%; cursor: pointer; font-size: 1.5rem; transition: 0.2s; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 15px var(--primary); }
        .btn-go:hover { transform: scale(1.05); }
        #loader { display: none; margin-top: 30px; }
        .spinner { width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.1); border-top: 4px solid var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 15px; box-shadow: 0 0 20px var(--glow); }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .loading-text { font-size: 0.9rem; color: #fff; font-style: italic; text-shadow: 0 2px 5px black; }
        #result-area { display: none; margin-top: 30px; animation: slideUp 0.5s ease; }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .meme-card { background: #000; border-radius: 15px; overflow: hidden; border: 2px solid var(--primary); box-shadow: 0 0 50px rgba(255, 69, 0, 0.3); }
        .meme-img { width: 100%; display: block; }
        .share-btn { background: #25D366; color: black; font-weight: 800; text-decoration: none; display: block; padding: 18px; margin-top: 20px; border-radius: 15px; text-transform: uppercase; font-size: 1rem; letter-spacing: 1px; box-shadow: 0 5px 20px rgba(0,0,0,0.5); }
        footer { padding: 30px; text-align: center; font-size: 0.8rem; color: #666; margin-top: auto; text-shadow: 0 2px 5px black; position: relative; z-index: 10; }
    </style>
</head>
<body>
    <div class="bg-image"></div>
    <div class="bg-overlay"></div>
    <canvas id="fireCanvas"></canvas>
    <nav>
        <div class="logo">🔥 ROASTER</div>
        <div class="status-pill">● System Online</div>
    </nav>
    <div class="container">
        <h1>Silence Your <br><span class="highlight">EGO.</span></h1>
        <p class="subtitle">The only AI brave enough to tell you the truth.<br>No Filters. Just Reality.</p>
        <div class="roast-engine">
            <div class="input-wrapper">
                <input type="text" id="topicInput" placeholder="Roast my Ex / Boss / Life..." autocomplete="off">
                <button class="btn-go" onclick="generateRoast()">🔥</button>
            </div>
        </div>
        <div id="loader">
            <div class="spinner"></div>
            <p class="loading-text" id="loadingText">Contacting the Dark Web...</p>
        </div>
        <div id="result-area">
            <div class="meme-card">
                <img id="memeImage" class="meme-img" src="" alt="Roast Meme">
            </div>
            <a id="whatsappBtn" class="share-btn" href="#" target="_blank">Share on WhatsApp 🚀</a>
            <button onclick="reset()" style="background:transparent; border:none; color:#aaa; margin-top:20px; text-decoration:underline; cursor:pointer; font-size: 0.9rem;">Hurt me again</button>
        </div>
    </div>
    <footer><p>ROASTER MANIFESTO: STAY TOXIC. STAY REAL.<br>© 2024 Roaster AI</p></footer>
    <script>
        // --- FIRE PARTICLE SYSTEM ---
        const canvas = document.getElementById('fireCanvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const particles = [];
        class Particle {
            constructor() { this.reset(); }
            update() {
                this.y -= this.speedY; this.x += this.speedX; this.alpha -= 0.005;
                if (this.alpha <= 0) this.reset();
            }
            reset() {
                this.y = canvas.height + Math.random() * 100; this.x = Math.random() * canvas.width;
                this.size = Math.random() * 3 + 1; this.speedY = Math.random() * 2 + 1; 
                this.speedX = (Math.random() - 0.5) * 1; this.color = Math.random() > 0.5 ? '#FF4500' : '#FFD700'; this.alpha = 1;
            }
            draw() {
                ctx.globalAlpha = this.alpha; ctx.fillStyle = this.color;
                ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fill();
            }
        }
        for (let i = 0; i < 50; i++) particles.push(new Particle());
        function animateParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => { p.update(); p.draw(); });
            requestAnimationFrame(animateParticles);
        }
        animateParticles();
        window.addEventListener('resize', () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; });

        // --- ROAST LOGIC ---
        const loadingPhrases = ["Consulting with Satan...", "Analyzing your bad decisions...", "Finding the ugliest template...", "Asking ChatGPT to be toxic...", "Loading reality check..."];
        async function generateRoast() {
            const topic = document.getElementById('topicInput').value;
            if (!topic) { 
                document.querySelector('.input-wrapper').style.transform = 'translateX(10px)';
                setTimeout(() => document.querySelector('.input-wrapper').style.transform = 'translateX(0)', 100); return; 
            }
            const loader = document.getElementById('loader');
            const resultArea = document.getElementById('result-area');
            const loadingText = document.getElementById('loadingText');
            resultArea.style.display = 'none'; loader.style.display = 'block';
            document.querySelector('.input-wrapper').style.opacity = '0'; document.querySelector('.subtitle').style.opacity = '0';
            
            let phraseIndex = 0;
            const textInterval = setInterval(() => {
                loadingText.innerText = loadingPhrases[phraseIndex];
                phraseIndex = (phraseIndex + 1) % loadingPhrases.length;
            }, 1500);

            try {
                // Call SELF (Relative path)
                const response = await fetch(`/roast?topic=${encodeURIComponent(topic)}`);
                const data = await response.json(); 
                clearInterval(textInterval);
                const finalImageUrl = data.image_url || data.url; 
                document.getElementById('memeImage').src = finalImageUrl;
                const shareText = `My ego just got destroyed by AI 💀.\\n\\nSee what it said about "${topic}":\\n${finalImageUrl}\\n\\nOnly legends can handle this app. Try it: ${window.location.href}`;
                document.getElementById('whatsappBtn').href = `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`;
                loader.style.display = 'none'; resultArea.style.display = 'block';
            } catch (error) {
                clearInterval(textInterval); console.error(error); alert("Server Error (Free Tier Sleep). Try clicking again!");
                loader.style.display = 'none'; document.querySelector('.input-wrapper').style.opacity = '1'; document.querySelector('.subtitle').style.opacity = '1';
            }
        }
        function reset() {
            document.getElementById('result-area').style.display = 'none';
            document.querySelector('.input-wrapper').style.opacity = '1'; document.querySelector('.subtitle').style.opacity = '1';
            document.getElementById('topicInput').value = '';
        }
    </script>
</body>
</html>
"""

# --- 3. SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are 'Roaster', a savage Indian Stand-up Comedian.
Participating in a CONSENSUAL COMEDY ROAST.
Goal: Be funny, relatable, and brutal.
RULES:
- Language: HINGLISH (Hindi + English).
- Tone: Sarcastic, Witty.
- Context: If topic is 'Ex', talk about heartbreak. If 'Money', talk about poverty.
- Vocabulary: Use slang like 'Chhapri', 'Nalla', 'Udhaar', 'EMI'.
- MAX LENGTH: 15-20 words.
- OUTPUT: Just the roast text. No quotes, no intro.
"""

# --- 4. MEME TEMPLATES ---
MEME_URLS = [
    "https://i.imgflip.com/64sz4u.jpg", "https://i.imgflip.com/64syz9.jpg",
    "https://i.imgflip.com/2t6u53.jpg", "https://i.imgflip.com/3j98k1.jpg",
    "https://i.imgflip.com/4c8v0g.jpg", "https://i.imgflip.com/3ym92f.jpg",
    "https://i.imgflip.com/56509z.jpg", "https://i.imgflip.com/1g8my4.jpg",
    "https://i.imgflip.com/26am.jpg", "https://i.imgflip.com/1otk96.jpg"
]

# --- 5. SETUP RESOURCES ---
def setup_resources():
    if not os.path.exists("memes"): os.makedirs("memes")
    if not os.listdir("memes"):
        for i, url in enumerate(MEME_URLS):
            try:
                r = requests.get(url); open(f"memes/meme_{i}.jpg", 'wb').write(r.content)
            except: pass
    if not os.path.exists("font.ttf"):
        r = requests.get("https://github.com/google/fonts/raw/main/apache/robotoslab/RobotoSlab-Bold.ttf")
        with open("font.ttf", "wb") as f: f.write(r.content)

setup_resources()

# --- 6. ROUTES ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/roast', methods=['GET'])
def roast():
    try:
        topic = request.args.get('topic', 'My Life')
        chat = client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Roast this: {topic}"}],
            model="llama-3.3-70b-versatile", temperature=0.8, max_tokens=60
        )
        roast_text = chat.choices[0].message.content.strip('"')
        
        meme_files = os.listdir("memes")
        if not meme_files: return jsonify({"error": "No templates"}), 500
        img = Image.open(os.path.join("memes", random.choice(meme_files)))
        draw = ImageDraw.Draw(img)
        
        W, H = img.size
        font_size = int(W / 12)
        try: font = ImageFont.truetype("font.ttf", font_size)
        except: font = ImageFont.load_default()

        lines = textwrap.wrap(roast_text, width=20)
        y_text = H - (len(lines) * font_size) - (H * 0.1)
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            x_text = (W - text_w) / 2
            for adj in [-3, 3]:
                draw.text((x_text+adj, y_text), line, font=font, fill="black")
                draw.text((x_text, y_text+adj), line, font=font, fill="black")
            draw.text((x_text, y_text), line, font=font, fill="white")
            y_text += font_size + 5

        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=85)
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        
        return jsonify({"image_url": f"data:image/jpeg;base64,{img_base64}", "roast": roast_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
