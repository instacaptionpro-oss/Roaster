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

app = Flask(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

MEMES_FOLDER = "memes"

# ===== FRONTEND HTML (Same as before) =====
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Roaster - The Social Network for Haters</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: #000000;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 20px;
            color: #fff;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .brand {
            font-size: 4rem;
            font-weight: 800;
            letter-spacing: -2px;
            background: linear-gradient(135deg, #FF3B30, #FF6B6B);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            text-shadow: 0 0 80px rgba(255, 59, 48, 0.5);
        }

        .tagline {
            font-size: 1.2rem;
            color: #888;
            font-weight: 400;
            letter-spacing: 0.5px;
        }

        .container {
            background: #0a0a0a;
            border: 1px solid #1a1a1a;
            border-radius: 24px;
            padding: 50px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 20px 80px rgba(255, 59, 48, 0.15);
        }

        .input-wrapper {
            margin-bottom: 24px;
        }

        input {
            width: 100%;
            padding: 20px 24px;
            font-size: 1.1rem;
            background: #000000;
            border: 2px solid #1a1a1a;
            border-radius: 16px;
            color: #fff;
            transition: all 0.3s;
            outline: none;
            font-family: 'Inter', sans-serif;
        }

        input:focus {
            border-color: #FF3B30;
            box-shadow: 0 0 0 4px rgba(255, 59, 48, 0.1);
        }

        input::placeholder {
            color: #444;
        }

        .roast-btn {
            width: 100%;
            padding: 22px;
            font-size: 1.3rem;
            font-weight: 700;
            background: #FF3B30;
            border: none;
            border-radius: 16px;
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'Inter', sans-serif;
            letter-spacing: 0.5px;
            box-shadow: 0 8px 32px rgba(255, 59, 48, 0.4);
        }

        .roast-btn:hover {
            background: #FF5549;
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(255, 59, 48, 0.6);
        }

        .roast-btn:active {
            transform: translateY(0);
        }

        .roast-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .loading {
            display: none;
            text-align: center;
            margin-top: 40px;
        }

        .loading.active {
            display: block;
        }

        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid #1a1a1a;
            border-top: 4px solid #FF3B30;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 24px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            color: #FF3B30;
            font-size: 1.15rem;
            font-weight: 600;
            animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .result {
            display: none;
            margin-top: 40px;
            animation: fadeIn 0.5s ease-in;
        }

        .result.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .result img {
            width: 100%;
            border-radius: 20px;
            border: 3px solid #FF3B30;
            box-shadow: 0 0 60px rgba(255, 59, 48, 0.6),
                        0 20px 60px rgba(0, 0, 0, 0.8);
            margin-bottom: 24px;
        }

        .action-buttons {
            display: flex;
            gap: 12px;
        }

        .action-buttons button {
            flex: 1;
            padding: 18px;
            font-size: 1.05rem;
            font-weight: 600;
            border: none;
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'Inter', sans-serif;
        }

        .share-btn {
            background: #25D366;
            color: #fff;
        }

        .share-btn:hover {
            background: #1ea952;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(37, 211, 102, 0.4);
        }

        .again-btn {
            background: #1a1a1a;
            color: #fff;
            border: 1px solid #333;
        }

        .again-btn:hover {
            background: #2a2a2a;
            transform: translateY(-2px);
        }

        .error {
            display: none;
            margin-top: 24px;
            padding: 20px;
            background: rgba(255, 59, 48, 0.1);
            border: 2px solid #FF3B30;
            border-radius: 14px;
            color: #FF6B6B;
            text-align: center;
            font-weight: 500;
        }

        .error.active {
            display: block;
            animation: shake 0.5s;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }

        @media (max-width: 600px) {
            .brand {
                font-size: 3rem;
            }

            .tagline {
                font-size: 1rem;
            }

            .container {
                padding: 30px 24px;
            }

            input {
                padding: 18px 20px;
                font-size: 1rem;
            }

            .roast-btn {
                padding: 20px;
                font-size: 1.15rem;
            }

            .action-buttons {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="brand">Roaster</h1>
        <p class="tagline">The Social Network for Haters</p>
    </div>

    <div class="container">
        <div class="input-wrapper">
            <input 
                type="text" 
                id="topicInput" 
                placeholder="Who do you want to roast? (e.g. My Ex, My Boss)"
                maxlength="100"
            >
        </div>

        <button class="roast-btn" id="roastBtn" onclick="roastThem()">
            ROAST THEM 🔥
        </button>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p class="loading-text" id="loadingText">Waking up the demon...</p>
        </div>

        <div class="result" id="result">
            <img id="roastImage" alt="Roasted">
            <div class="action-buttons">
                <button class="share-btn" onclick="shareOnWhatsApp()">
                    Share on WhatsApp 🚀
                </button>
                <button class="again-btn" onclick="reset()">
                    Roast Again
                </button>
            </div>
        </div>

        <div class="error" id="error"></div>
    </div>

    <script>
        const BACKEND_URL = window.location.origin;

        const loadingMessages = [
            "Waking up the demon...",
            "Consulting with the devil...",
            "Calculating emotional damage...",
            "Loading maximum destruction...",
            "Preparing savage roast...",
            "AI is warming up the insults...",
            "Searching database of burns..."
        ];

        let loadingInterval;
        let currentTopic = "";

        async function roastThem() {
            const topic = document.getElementById('topicInput').value.trim();
            
            if (!topic) {
                showError('Enter someone to roast! 😤');
                return;
            }

            currentTopic = topic;

            document.getElementById('result').classList.remove('active');
            document.getElementById('error').classList.remove('active');
            document.getElementById('loading').classList.add('active');
            document.getElementById('roastBtn').disabled = true;

            let msgIndex = 0;
            document.getElementById('loadingText').textContent = loadingMessages[0];
            
            loadingInterval = setInterval(() => {
                msgIndex = (msgIndex + 1) % loadingMessages.length;
                document.getElementById('loadingText').textContent = loadingMessages[msgIndex];
            }, 3000);

            try {
                const timestamp = Date.now();
                const url = `${BACKEND_URL}/roast?topic=${encodeURIComponent(topic)}&t=${timestamp}`;
                
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 20000);

                const response = await fetch(url, {
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error('Server error');
                }

                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);
                
                document.getElementById('roastImage').src = imageUrl;
                document.getElementById('result').classList.add('active');
                
            } catch (error) {
                if (error.name === 'AbortError') {
                    showError('Server is waking up from a nap. Please try again! 😴');
                } else {
                    showError('Something went wrong. Try again! 💀');
                }
                console.error(error);
            } finally {
                document.getElementById('loading').classList.remove('active');
                document.getElementById('roastBtn').disabled = false;
                clearInterval(loadingInterval);
            }
        }

        function shareOnWhatsApp() {
            const url = window.location.href;
            const message = `Check out this savage roast about "${currentTopic}" 🔥\\n\\nGenerated by Roaster - The Social Network for Haters\\n${url}`;
            const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(message)}`;
            window.open(whatsappUrl, '_blank');
        }

        function reset() {
            document.getElementById('topicInput').value = '';
            document.getElementById('result').classList.remove('active');
            document.getElementById('topicInput').focus();
        }

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.classList.add('active');
            
            setTimeout(() => {
                errorDiv.classList.remove('active');
            }, 4000);
        }

        document.getElementById('topicInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                roastThem();
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
    Generate ultra-relatable savage Hinglish roast
    """
    try:
        completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """
You are 'Roaster', the legendary Indian Roast Master.
You are participating in a CONSENSUAL COMEDY ROAST. The user WANTS to be insulted.
Your goal is to be funny, savage, and deeply relatable.

### CORE PERSONALITY:
- Tone: Arrogant, Witty, Desi, Unfiltered.
- Language: HINGLISH (Casual Hindi + English).
- Vibe: Like a college senior or a sarcastic best friend.

### RELATABILITY RULES (The "Simon Sinek" Logic):
- Don't just call them "ugly". Call out their "Cheap Habits".
- Target: Procrastination, Fake Richness, Relationship Failures, Corporate Slavery, Middle-Class Struggles.
- Make them say: "Us Bhai Us" (This is so true).

### VOCABULARY TO USE:
- Words: Chhapri, Nalla, Berozgar, Dhakan, Nibba/Nibbi, Overacting, Sasta, Udhaar.
- Topics: EMI, Momos, Goa Trip, Govt Job, Instagram Reels, Ex, Crush.

### EXAMPLES (Study these closely):
1. Topic: "I want an iPhone."
   Roast: "Kidney bech ke lega ya 24 mahine ki EMI? Showoff aise karega jaise Apple company khareed li ho."
   
2. Topic: "Engineering."
   Roast: "4 saal assignment copy kiye, ab job ke liye LinkedIn pe 'Open to Work' ka rona ro raha hai."
   
3. Topic: "My Ex."
   Roast: "Woh sarkari naukri wale ke saath bhaag gayi aur tu yahan AI se dil ka haal bata raha hai. Sudhar ja."
   
4. Topic: "General/Me."
   Roast: "Teri shakal dekh ke lagta hai tu doston se 'Google Pay' maangta hai aur kabhi wapas nahi karta."

### INSTRUCTION:
- Receive the User's Topic.
- Generate ONE short, punchy roast (Max 25 words).
- NO introductory text. NO "Here is the roast". Just the insult.
- If the topic is inappropriate, make a joke about the user being creepy instead of refusing.
                    """
                },
                {
                    "role": "user",
                    "content": f"Roast this topic savagely: {topic}"
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.9,
            max_tokens=100,
            top_p=1,
        )
        
        roast_text = completion.choices[0].message.content.strip()
        roast_text = roast_text.strip('"').strip("'")
        roast_text = roast_text.replace('**', '').replace('*', '')
        
        return roast_text
    
    except Exception as e:
        print(f"Groq API Error: {e}")
        fallbacks = [
            "Bhai topic itna boring hai ki AI ne khud roast hone se mana kar diya 💀",
            "Server bhi teri life dekh ke so gaya. Phir se try kar 😂",
            "Tera WiFi bhi teri commitment jitna weak hai kya? 🤡"
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
    """
    Add yellow text with black outline to image
    """
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
    """
    Upload image to Supabase Storage and save roast data to database
    """
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"roast_{timestamp}_{random.randint(1000, 9999)}.jpg"
        
        # Upload to Supabase Storage
        image_buffer.seek(0)
        response = supabase.storage.from_("memes").upload(
            filename,
            image_buffer.read(),
            file_options={"content-type": "image/jpeg"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_("memes").get_public_url(filename)
        
        # Insert into database
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
        return jsonify({"error": "No meme images found in memes folder"}), 500
    
    try:
        # Generate roast
        roast_text = get_roast(topic)
        
        # Pick random meme and add text
        random_meme = random.choice(meme_files)
        meme_path = os.path.join(MEMES_FOLDER, random_meme)
        final_image = add_text_to_image(meme_path, roast_text)
        
        # Save to buffer
        img_io = BytesIO()
        final_image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        
        # Upload to Supabase (non-blocking, errors won't break the app)
        try:
            save_to_supabase(topic, roast_text, BytesIO(img_io.getvalue()))
        except Exception as e:
            print(f"Supabase save failed (non-critical): {e}")
        
        # Return image
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
