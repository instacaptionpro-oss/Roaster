import os
import random
import textwrap
from io import BytesIO
from flask import Flask, request, send_file, jsonify
from groq import Groq
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Memes folder path
MEMES_FOLDER = "memes"

def get_font(size=40):
    """
    Try to load a good font, fallback to default if not available
    """
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux (Render)
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "C:\\Windows\\Fonts\\Arial.ttf",  # Windows
        "arial.ttf",
        "DejaVuSans-Bold.ttf"
    ]
    
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    
    # Fallback to default PIL font
    return ImageFont.load_default()

def generate_roast(topic):
    """
    Generate a savage Hinglish roast using Groq
    """
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a savage roast master. Generate short, funny, brutal Hinglish roasts. Maximum 20 words. Use Hindi-English mix. Be creative and edgy but not offensive about religion, caste, or serious topics."
                },
                {
                    "role": "user",
                    "content": f"Roast this: {topic}"
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=1.2,
            max_tokens=100
        )
        
        roast_text = chat_completion.choices[0].message.content.strip()
        # Remove quotes if AI adds them
        roast_text = roast_text.strip('"').strip("'")
        return roast_text
    
    except Exception as e:
        print(f"Groq API Error: {e}")
        return f"Bro, {topic}? Seriously? Even AI gave up on roasting this! 💀"

def wrap_text(text, font, max_width):
    """
    Wrap text to fit within max_width
    """
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
    Add wrapped text with outline to image
    """
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    # Image dimensions
    img_width, img_height = img.size
    
    # Font size (adaptive based on image size)
    font_size = int(img_height * 0.06)  # 6% of image height
    font = get_font(font_size)
    
    # Wrap text (90% of image width for padding)
    max_width = int(img_width * 0.9)
    lines = wrap_text(text, font, max_width)
    
    # Calculate total text height
    line_height = font_size + 10
    total_text_height = len(lines) * line_height
    
    # Start position (centered vertically at bottom third)
    y_position = img_height - total_text_height - 50
    
    # Draw each line
    for line in lines:
        # Get text bounding box for centering
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x_position = (img_width - text_width) // 2
        
        # Draw black outline (stroke effect)
        outline_range = 3
        for adj_x in range(-outline_range, outline_range + 1):
            for adj_y in range(-outline_range, outline_range + 1):
                draw.text(
                    (x_position + adj_x, y_position + adj_y),
                    line,
                    font=font,
                    fill="black"
                )
        
        # Draw white text on top
        draw.text(
            (x_position, y_position),
            line,
            font=font,
            fill="white"
        )
        
        y_position += line_height
    
    return img

@app.route('/')
def home():
    return jsonify({
        "message": "🔥 Roast AI Backend is Live!",
        "usage": "/roast?topic=your_topic",
        "example": "/roast?topic=my coding skills"
    })

@app.route('/roast', methods=['GET'])
def roast():
    """
    Main roast endpoint
    """
    # Get topic from query parameter
    topic = request.args.get('topic', '').strip()
    
    if not topic:
        return jsonify({"error": "Please provide a 'topic' parameter"}), 400
    
    # Check if memes folder exists and has images
    if not os.path.exists(MEMES_FOLDER):
        return jsonify({"error": "Memes folder not found"}), 500
    
    meme_files = [f for f in os.listdir(MEMES_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not meme_files:
        return jsonify({"error": "No meme images found in memes folder"}), 500
    
    try:
        # Step A: Generate roast
        roast_text = generate_roast(topic)
        
        # Step B: Pick random meme
        random_meme = random.choice(meme_files)
        meme_path = os.path.join(MEMES_FOLDER, random_meme)
        
        # Step C: Add text to image
        final_image = add_text_to_image(meme_path, roast_text)
        
        # Step D: Return image
        img_io = BytesIO()
        final_image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/jpeg')
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
