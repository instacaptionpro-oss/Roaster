import os
import random
import json
import logging
import time
from io import BytesIO
from datetime import datetime
from flask import Flask, request, send_file, jsonify, render_template_string, redirect
from groq import Groq
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

try:
    import requests as req_lib
    GEO_ENABLED = True
except:
    GEO_ENABLED = False

try:
    from search import get_smart_context, get_india_trending
    SEARCH_ENABLED = True
except:
    SEARCH_ENABLED = False

# Battle system modules — loaded after you drop files in core/
try:
    from core.battle_card import generate_battle_card
    BATTLE_CARD_ENABLED = True
except:
    BATTLE_CARD_ENABLED = False

try:
    from core.gemini import (generate_notification, generate_gif_keyword,
                              generate_battle_caption, generate_win_message, generate_loss_message)
    GEMINI_ENABLED = True
except:
    GEMINI_ENABLED = False

try:
    from core.notifications import send_push
    PUSH_ENABLED = True
except:
    PUSH_ENABLED = False

try:
    from core.storage import upload_battle_card
    STORAGE_ENABLED = True
except:
    STORAGE_ENABLED = False

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

app          = Flask(__name__, static_folder='static', static_url_path='/static')
groq_client  = Groq(api_key=os.getenv("GROQ_API_KEY"))
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://roast_db_c13t_user:9PO09Y3SpZ6z5r0eYszLsYGHg0bcYtXx@dpg-d5ubdo24d50c73d1bmdg-a/roast_db_c13t")
MEMES_FOLDER  = "memes"
AI_MODELS     = ["llama-3.3-70b-versatile", "qwen/qwen-2.5-72b-instruct", "meta-llama/llama-3.1-70b-versatile"]
ANALYTICS_KEY = os.getenv("ANALYTICS_KEY", "")


# =====================================================================
# DATABASE
# =====================================================================
def get_db_connection():
    try:    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except: return None


def init_database():
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()

        # Original tables
        cur.execute('''CREATE TABLE IF NOT EXISTS roasts (
            id SERIAL PRIMARY KEY, topic VARCHAR(255), label VARCHAR(100),
            roast TEXT, language VARCHAR(20), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS stats (
            id SERIAL PRIMARY KEY, total_roasts INTEGER DEFAULT 0)''')

        cur.execute('SELECT COUNT(*) as c FROM stats')
        if cur.fetchone()['c'] == 0:
            cur.execute('INSERT INTO stats (total_roasts) VALUES (52341)')

        # Analytics
        cur.execute('''CREATE TABLE IF NOT EXISTS analytics (
            id SERIAL PRIMARY KEY, topic VARCHAR(255), label VARCHAR(100),
            roast_text TEXT, language VARCHAR(20), quality INTEGER, quality_name VARCHAR(20),
            ip_address VARCHAR(45), country VARCHAR(100), country_code VARCHAR(10), city VARCHAR(100),
            user_agent TEXT, device_type VARCHAR(20), response_ms INTEGER,
            success BOOLEAN DEFAULT TRUE, error_msg TEXT, session_id VARCHAR(100),
            hour_of_day INTEGER, day_of_week INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # Battle system
        cur.execute('''CREATE TABLE IF NOT EXISTS battles (
            id SERIAL PRIMARY KEY, battle_id VARCHAR(20) UNIQUE NOT NULL,
            topic VARCHAR(255), mode VARCHAR(10) DEFAULT 'normal',
            status VARCHAR(20) DEFAULT 'pending',
            challenger_id VARCHAR(100), challenger_name VARCHAR(100),
            opponent_id VARCHAR(100), opponent_name VARCHAR(100),
            winner_id VARCHAR(100), loser_id VARCHAR(100),
            total_rounds INTEGER DEFAULT 0, loss_reason VARCHAR(20),
            card_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accepted_at TIMESTAMP, ended_at TIMESTAMP, expires_at TIMESTAMP)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS battle_rounds (
            id SERIAL PRIMARY KEY, battle_id VARCHAR(20) REFERENCES battles(battle_id),
            round_num INTEGER, player_id VARCHAR(100), player_name VARCHAR(100),
            roast_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS push_subscriptions (
            id SERIAL PRIMARY KEY, session_id VARCHAR(100) UNIQUE,
            endpoint TEXT, p256dh TEXT, auth TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS user_roast_count (
            session_id VARCHAR(100) PRIMARY KEY,
            roast_count INTEGER DEFAULT 0, gali_unlocked BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        conn.commit()
        logger.info("DB init OK")
    except Exception as e:
        logger.error(f"DB init error: {e}")
    finally:
        conn.close()


init_database()


# =====================================================================
# DB HELPERS
# =====================================================================
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


def get_geo(ip):
    if not GEO_ENABLED or not ip or ip in ('127.0.0.1','localhost'):
        return {}, 'Unknown', '', 'Unknown'
    try:
        r = req_lib.get(f'http://ip-api.com/json/{ip}', timeout=2)
        d = r.json()
        if d.get('status') == 'success':
            return d, d.get('country','Unknown'), d.get('countryCode',''), d.get('city','Unknown')
    except: pass
    return {}, 'Unknown', '', 'Unknown'


def get_device_type(ua):
    ua = (ua or '').lower()
    if any(x in ua for x in ['mobile','android','iphone','ipad']): return 'mobile'
    if 'tablet' in ua: return 'tablet'
    return 'desktop'


def save_roast_analytics(topic, label, roast_text, language, quality,
                          ip, session_id, response_ms, success=True, error_msg=None):
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        quality_names = {1:'SPARK',2:'FLAME',3:'INFERNO',4:'HELLFIRE',5:'APOCALYPSE'}
        _, country, country_code, city = get_geo(ip)
        ua  = request.headers.get('User-Agent','')
        now = datetime.now()

        if success:
            cur.execute('INSERT INTO roasts (topic,label,roast,language) VALUES (%s,%s,%s,%s)',
                        (topic, label, roast_text, language))
            cur.execute('UPDATE stats SET total_roasts = total_roasts + 1')

        cur.execute('''INSERT INTO analytics
            (topic,label,roast_text,language,quality,quality_name,
             ip_address,country,country_code,city,user_agent,device_type,
             response_ms,success,error_msg,session_id,hour_of_day,day_of_week)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (topic,label,roast_text,language,quality,quality_names.get(quality,'?'),
             ip,country,country_code,city,ua,get_device_type(ua),
             response_ms,success,error_msg,session_id,now.hour,now.weekday()))

        # User roast count — for Gali unlock
        cur.execute('''INSERT INTO user_roast_count (session_id, roast_count) VALUES (%s,1)
            ON CONFLICT (session_id) DO UPDATE
            SET roast_count = user_roast_count.roast_count + 1, updated_at = NOW()''',
            (session_id,))
        cur.execute('''UPDATE user_roast_count SET gali_unlocked=TRUE
            WHERE session_id=%s AND roast_count >= 10''', (session_id,))

        conn.commit()
    except Exception as e:
        logger.error(f"Analytics error: {e}")
    finally:
        conn.close()


def get_user_roast_count(session_id):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('SELECT roast_count,gali_unlocked FROM user_roast_count WHERE session_id=%s', (session_id,))
            r = cur.fetchone()
            return (r['roast_count'], r['gali_unlocked']) if r else (0, False)
        except: return (0, False)
        finally: conn.close()
    return (0, False)


def get_battle(battle_id):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('SELECT * FROM battles WHERE battle_id=%s', (battle_id,))
            return cur.fetchone()
        except: return None
        finally: conn.close()
    return None


def get_battle_rounds(battle_id):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('SELECT * FROM battle_rounds WHERE battle_id=%s ORDER BY round_num', (battle_id,))
            return cur.fetchall()
        except: return []
        finally: conn.close()
    return []


def save_push_subscription(session_id, endpoint, p256dh, auth):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''INSERT INTO push_subscriptions (session_id,endpoint,p256dh,auth)
                VALUES (%s,%s,%s,%s) ON CONFLICT (session_id) DO UPDATE
                SET endpoint=%s,p256dh=%s,auth=%s''',
                (session_id,endpoint,p256dh,auth,endpoint,p256dh,auth))
            conn.commit()
        except Exception as e:
            logger.error(f"Push sub error: {e}")
        finally:
            conn.close()


def generate_battle_id():
    import string
    return "RB-" + ''.join(random.choices(string.digits, k=5))


def _end_battle(battle_id, loser_id, reason):
    battle = get_battle(battle_id)
    if not battle:              return jsonify({"error": "Not found"}), 404
    if battle['status'] != 'active': return jsonify({"error": "Battle not active"}), 400

    winner_id = (battle['challenger_id'] if loser_id == battle['opponent_id']
                 else battle['opponent_id'])

    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB error"}), 500
    try:
        cur = conn.cursor()
        cur.execute('''UPDATE battles SET status='ended', winner_id=%s, loser_id=%s,
            loss_reason=%s, ended_at=NOW() WHERE battle_id=%s''',
            (winner_id, loser_id, reason, battle_id))
        conn.commit()

        winner_name = (battle['challenger_name'] if winner_id == battle['challenger_id']
                       else battle['opponent_name'])
        loser_name  = (battle['challenger_name'] if loser_id  == battle['challenger_id']
                       else battle['opponent_name'])

        if PUSH_ENABLED and GEMINI_ENABLED:
            try:
                send_push(winner_id, generate_win_message(winner_name, battle['topic']))
                send_push(loser_id,  generate_loss_message(loser_name, battle['topic']))
            except: pass

        return jsonify({"status":"ended","winner":winner_name,"loser":loser_name,
                        "loss_reason":reason,"card_url":f"/battle/{battle_id}/card"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# =====================================================================
# IMAGE
# =====================================================================
def add_text_to_image(image_path, label, roast_text):
    img  = Image.open(image_path).convert('RGB')
    draw = ImageDraw.Draw(img)
    W, H = img.size
    try:
        lf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(16,W//20))
        rf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(14,W//26))
    except:
        lf = rf = ImageFont.load_default()

    lh = int(H*0.09)
    draw.rectangle([0,0,W,lh], fill="#8B0000")
    lw = draw.textlength(label, font=lf)
    lx = max(0,(W-lw)//2)
    for dx in range(-2,3):
        for dy in range(-2,3):
            draw.text((lx+dx,(lh-lf.size)//2+dy), label, font=lf, fill="#000000")
    draw.text((lx,(lh-lf.size)//2), label, font=lf, fill="#FF4444")

    words = roast_text.split()
    lines, cur_line = [], ""
    for w in words:
        test = (cur_line+" "+w).strip()
        if draw.textlength(test, font=rf) <= W-24: cur_line = test
        else:
            if cur_line: lines.append(cur_line)
            cur_line = w
    if cur_line: lines.append(cur_line)

    lh2   = rf.size+4
    total = lh2*len(lines)
    y     = H-total-20
    ov    = Image.new('RGBA',img.size,(0,0,0,0))
    od    = ImageDraw.Draw(ov)
    od.rectangle([0,y-10,W,H], fill=(0,0,0,160))
    img   = Image.alpha_composite(img.convert('RGBA'),ov).convert('RGB')
    draw  = ImageDraw.Draw(img)
    for line in lines:
        x = max(0,(W-draw.textlength(line,font=rf))//2)
        for dx in range(-2,3):
            for dy in range(-2,3):
                draw.text((x+dx,y+dy), line, font=rf, fill="#000000")
        draw.text((x,y), line, font=rf, fill="#FFFFFF")
        y += lh2
    return img


# =====================================================================
# AI ROAST
# =====================================================================
QUALITY_INSTRUCTIONS = {
    1: {'label':'SPARK',      'temp':0.8,'words':10,
        'instruction_hi': 'Thoda soft roast kar, zyada brutal mat ho. Friendly teasing style.',
        'instruction_en': 'Keep it light and playful. Mild teasing, nothing too harsh.',
        'instruction_mix':'Thoda soft reh, friendly roast kar.'},
    2: {'label':'FLAME',      'temp':0.9,'words':12,
        'instruction_hi': 'Thoda spicy roast kar. Burn karo but zyada personal mat jao.',
        'instruction_en': 'Make it sting a little. Clever burns, moderately savage.',
        'instruction_mix':'Thoda spicy, medium brutal roast kar.'},
    3: {'label':'INFERNO',    'temp':1.0,'words':15,
        'instruction_hi': 'Brutal roast kar bhai style mein. Savage bol, no mercy.',
        'instruction_en': 'Be brutally savage. No holding back, destroy the topic.',
        'instruction_mix':'Brutal aur savage roast kar, Hinglish mein.'},
    4: {'label':'HELLFIRE',   'temp':1.0,'words':18,
        'instruction_hi': 'Maximum savage roast kar. Ekdum tatti kar de. Soul destroy kar de.',
        'instruction_en': 'Absolutely destroy them. Pure hellfire, soul-crushing roast.',
        'instruction_mix':'Maximum savage, soul destroy kar de roast mein.'},
    5: {'label':'APOCALYPSE', 'temp':1.0,'words':20,
        'instruction_hi': 'APOCALYPSE level roast kar. Existence hi end kar de. Ancestors ko rula de. Koi mercy nahi.',
        'instruction_en': 'APOCALYPSE mode. Obliterate their existence. Make their ancestors cry. Zero mercy, maximum destruction.',
        'instruction_mix':'APOCALYPSE level — existence khatam kar de, ancestors rula de, zero mercy.'},
}


def get_roast(topic, language='hindi', quality=3):
    quality = max(1,min(5,int(quality)))
    q       = QUALITY_INSTRUCTIONS[quality]
    context = ""
    if SEARCH_ENABLED:
        try:
            from search import get_smart_context
            data    = get_smart_context(topic, language)
            context = data.get('topic_info','')[:400]
        except: pass

    ctx_line = f'Context: {context}\n\n' if context else ''
    w        = q['words']

    prompts = {
        'hindi':   f"Tu India ka sabse brutal roaster hai.\n{q['instruction_hi']}\n\n{ctx_line}Topic: {topic}\n\nLABEL: 2 word funny title\nROAST: {w}-{w+4} words, {q['label']} level, natural Hindi",
        'english': f"You are a roaster at {q['label']} intensity level.\n{q['instruction_en']}\n\n{ctx_line}Topic: {topic}\n\nLABEL: 2 word funny title\nROAST: {w}-{w+4} words, {q['label']} level, natural English",
        'mix':     f"Tu {q['label']} level ka roaster hai.\n{q['instruction_mix']}\n\n{ctx_line}Topic: {topic}\n\nLABEL: 2 word funny title\nROAST: {w}-{w+4} words, {q['label']} level, Hinglish"
    }

    for model in AI_MODELS:
        try:
            res  = groq_client.chat.completions.create(
                messages=[{"role":"user","content":prompts.get(language,prompts['hindi'])}],
                model=model, temperature=q['temp'], max_tokens=100)
            text = res.choices[0].message.content.strip()
            label, roast = "", ""
            for line in text.split('\n'):
                if 'LABEL:' in line.upper(): label = line.split(':',1)[1].strip().strip('"*').upper()
                elif 'ROAST:' in line.upper(): roast = line.split(':',1)[1].strip().strip('"*')
            if not label: label = f"{q['label']} ROAST"
            if not roast: roast = text[:100].replace('*','')
            return label, roast
        except: continue

    return (f"{q['label']} ROAST", "AI thak gaya tujhe roast karte karte")


# =====================================================================
# ROUTES
# =====================================================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def stats():
    return jsonify({"total_roasts": get_total_roasts()})

@app.route('/api/health')
def health():
    return jsonify({"status":"ok","battle_card":BATTLE_CARD_ENABLED,
                    "gemini":GEMINI_ENABLED,"push":PUSH_ENABLED})

@app.route('/roast')
def roast():
    topic      = request.args.get('topic','').strip()
    lang       = request.args.get('lang','hindi')
    quality    = request.args.get('quality',3)
    session_id = request.args.get('session_id','unknown')
    ratio      = request.args.get('ratio','1:1')

    if not topic: return jsonify({"error":"No topic"}),400

    memes = [f for f in os.listdir(MEMES_FOLDER)
             if f.endswith(('.jpg','.jpeg','.png'))] if os.path.exists(MEMES_FOLDER) else []
    if not memes: return jsonify({"error":"No memes"}),500

    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    t0 = time.time()

    try:
        label, roast_text = get_roast(topic, lang, quality)
        img = add_text_to_image(os.path.join(MEMES_FOLDER, random.choice(memes)), label, roast_text)

        # Ratio crop
        W2, H2 = img.size
        if ratio == '9:16':
            th = int(W2*16/9)
            if th > H2: nw=int(H2*9/16); img=img.crop(((W2-nw)//2,0,(W2+nw)//2,H2))
            else: img=img.crop((0,(H2-th)//2,W2,(H2+th)//2))
        elif ratio == '16:9':
            tw = int(H2*16/9)
            if tw > W2: nh=int(W2*9/16); img=img.crop((0,(H2-nh)//2,W2,(H2+nh)//2))
            else: img=img.crop(((W2-tw)//2,0,(W2+tw)//2,H2))

        buf = BytesIO()
        img.save(buf,'JPEG',quality=95)
        buf.seek(0)

        ms = int((time.time()-t0)*1000)
        save_roast_analytics(topic,label,roast_text,lang,quality,ip,session_id,ms,True)
        return send_file(BytesIO(buf.getvalue()), mimetype='image/jpeg')

    except Exception as e:
        ms = int((time.time()-t0)*1000)
        save_roast_analytics(topic,'','',lang,quality,ip,session_id,ms,False,str(e))
        logger.error(f"Roast error: {e}")
        return jsonify({"error":str(e)}),500

@app.route('/api/gali-status')
def gali_status():
    session_id = request.args.get('session_id','')
    count, unlocked = get_user_roast_count(session_id)
    return jsonify({"roast_count":count,"gali_unlocked":unlocked,"roasts_to_gali":max(0,10-count)})

# ── Battle routes ─────────────────────────────────────────────────────
@app.route('/battle/create', methods=['POST'])
def battle_create():
    data            = request.json or {}
    topic           = data.get('topic','').strip()
    mode            = data.get('mode','normal')
    challenger_id   = data.get('session_id','unknown')
    challenger_name = data.get('name','Anonymous')
    if not topic: return jsonify({"error":"Topic required"}),400

    if mode == 'gali':
        _, unlocked = get_user_roast_count(challenger_id)
        if not unlocked: return jsonify({"error":"Gali mode locked. Need 10 roasts first."}),403

    battle_id = generate_battle_id()
    conn = get_db_connection()
    if not conn: return jsonify({"error":"DB error"}),500
    try:
        cur = conn.cursor()
        cur.execute('''INSERT INTO battles
            (battle_id,topic,mode,status,challenger_id,challenger_name,expires_at)
            VALUES (%s,%s,%s,'pending',%s,%s, NOW() + INTERVAL '24 hours')''',
            (battle_id,topic,mode,challenger_id,challenger_name))
        conn.commit()
        return jsonify({"battle_id":battle_id,
                        "battle_url":f"{request.host_url}battle/{battle_id}",
                        "topic":topic,"mode":mode})
    except Exception as e:
        return jsonify({"error":str(e)}),500
    finally:
        conn.close()

@app.route('/battle/<battle_id>')
def battle_view(battle_id):
    battle = get_battle(battle_id)
    if not battle: return "Battle not found",404
    rounds = get_battle_rounds(battle_id)
    return render_template_string(BATTLE_TEMPLATE, battle=battle, rounds=rounds)

@app.route('/battle/<battle_id>/accept', methods=['POST'])
def battle_accept(battle_id):
    data          = request.json or {}
    opponent_id   = data.get('session_id','unknown')
    opponent_name = data.get('name','Anonymous')
    battle = get_battle(battle_id)
    if not battle: return jsonify({"error":"Not found"}),404
    if battle['status'] != 'pending': return jsonify({"error":"Already started"}),400
    conn = get_db_connection()
    if not conn: return jsonify({"error":"DB error"}),500
    try:
        cur = conn.cursor()
        cur.execute('''UPDATE battles SET status='active',opponent_id=%s,opponent_name=%s,
            accepted_at=NOW(),expires_at=NOW()+INTERVAL '24 hours' WHERE battle_id=%s''',
            (opponent_id,opponent_name,battle_id))
        conn.commit()
        if PUSH_ENABLED and GEMINI_ENABLED:
            try:
                msg = generate_notification('battle_started',{'opponent':opponent_name,'topic':battle['topic']})
                send_push(battle['challenger_id'],msg)
            except: pass
        return jsonify({"status":"active","battle_id":battle_id})
    except Exception as e:
        return jsonify({"error":str(e)}),500
    finally:
        conn.close()

@app.route('/battle/<battle_id>/roast', methods=['POST'])
def battle_roast(battle_id):
    data      = request.json or {}
    player_id = data.get('session_id','unknown')
    language  = data.get('lang','hindi')
    quality   = data.get('quality',3)
    battle    = get_battle(battle_id)
    if not battle: return jsonify({"error":"Not found"}),404
    if battle['status'] != 'active': return jsonify({"error":"Battle not active"}),400
    if player_id not in (battle['challenger_id'],battle['opponent_id']):
        return jsonify({"error":"You are not in this battle"}),403
    try:
        label, roast_text = get_roast(battle['topic'], language, quality)
        player_name = (battle['challenger_name'] if player_id==battle['challenger_id']
                       else battle['opponent_name'])
        conn = get_db_connection()
        if not conn: return jsonify({"error":"DB error"}),500
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as c FROM battle_rounds WHERE battle_id=%s', (battle_id,))
        round_num = cur.fetchone()['c']+1
        cur.execute('''INSERT INTO battle_rounds (battle_id,round_num,player_id,player_name,roast_text)
            VALUES (%s,%s,%s,%s,%s)''',(battle_id,round_num,player_id,player_name,roast_text))
        cur.execute('UPDATE battles SET total_rounds=%s WHERE battle_id=%s',(round_num,battle_id))
        conn.commit(); conn.close()
        opponent_id = (battle['opponent_id'] if player_id==battle['challenger_id']
                       else battle['challenger_id'])
        if PUSH_ENABLED and GEMINI_ENABLED:
            try:
                send_push(opponent_id,generate_notification('roast_received',
                    {'from':player_name,'topic':battle['topic']}))
            except: pass
        return jsonify({"round":round_num,"roast":roast_text,"label":label,"player":player_name})
    except Exception as e:
        logger.error(f"Battle roast error: {e}")
        return jsonify({"error":str(e)}),500

@app.route('/battle/<battle_id>/surrender', methods=['POST'])
def battle_surrender(battle_id):
    data = request.json or {}
    return _end_battle(battle_id, data.get('session_id','unknown'), 'surrendered')

@app.route('/battle/<battle_id>/status')
def battle_status(battle_id):
    battle = get_battle(battle_id)
    if not battle: return jsonify({"error":"Not found"}),404
    rounds = get_battle_rounds(battle_id)
    return jsonify({"status":battle['status'],"total_rounds":battle['total_rounds'],
                    "winner":battle['winner_id'],"rounds":[dict(r) for r in rounds],
                    "card_url":battle['card_url']})

@app.route('/battle/<battle_id>/card')
def battle_card_route(battle_id):
    battle = get_battle(battle_id)
    if not battle: return jsonify({"error":"Not found"}),404
    if battle['status'] != 'ended': return jsonify({"error":"Battle not ended yet"}),400
    if battle['card_url']: return redirect(battle['card_url'])
    if not BATTLE_CARD_ENABLED: return jsonify({"error":"Card module not loaded"}),500
    rounds   = get_battle_rounds(battle_id)
    w_roasts = sum(1 for r in rounds if r['player_id']==battle['winner_id'])
    l_roasts = sum(1 for r in rounds if r['player_id']==battle['loser_id'])
    started  = battle['accepted_at'] or battle['created_at']
    ended    = battle['ended_at']    or datetime.now()
    duration = ended - started
    dh, dm   = divmod(int(duration.total_seconds()//60),60)
    wname = (battle['challenger_name'] if battle['winner_id']==battle['challenger_id'] else battle['opponent_name'])
    lname = (battle['challenger_name'] if battle['loser_id'] ==battle['challenger_id'] else battle['opponent_name'])
    card_path = generate_battle_card({"battle_id":battle_id,"winner_name":wname,"loser_name":lname,
        "winner_roasts":w_roasts,"loser_roasts":l_roasts,"duration_hrs":dh,"duration_mins":dm,
        "loss_reason":battle['loss_reason'] or 'timeout',"total_rounds":battle['total_rounds'],
        "topic":battle['topic'],"mode":battle['mode']})
    card_url = None
    if STORAGE_ENABLED:
        try:
            card_url = upload_battle_card(card_path, battle_id)
            conn = get_db_connection()
            if conn:
                cur=conn.cursor(); cur.execute('UPDATE battles SET card_url=%s WHERE battle_id=%s',(card_url,battle_id))
                conn.commit(); conn.close()
        except Exception as e:
            logger.error(f"Card upload: {e}")
    if card_url: return redirect(card_url)
    return send_file(card_path, mimetype='image/jpeg')

# ── Push subscription ─────────────────────────────────────────────────
@app.route('/api/push/subscribe', methods=['POST'])
def push_subscribe():
    d = request.json or {}
    save_push_subscription(d.get('session_id'),d.get('endpoint'),d.get('p256dh'),d.get('auth'))
    return jsonify({"ok":True})

@app.route('/api/push/vapid-key')
def vapid_key():
    return jsonify({"public_key":os.getenv("VAPID_PUBLIC_KEY","")})

# ── Analytics ─────────────────────────────────────────────────────────
@app.route('/api/analytics')
def analytics():
    key = request.headers.get('X-Analytics-Key','')
    if ANALYTICS_KEY and key != ANALYTICS_KEY: return jsonify({"error":"Unauthorized"}),401
    conn = get_db_connection()
    if not conn: return jsonify({"error":"DB error"}),500
    try:
        cur = conn.cursor(); result = {}
        cur.execute('SELECT COUNT(*) as total, COUNT(CASE WHEN success THEN 1 END) as ok FROM analytics')
        result['overview'] = dict(cur.fetchone())
        cur.execute('SELECT language,COUNT(*) as cnt FROM analytics WHERE success=TRUE GROUP BY language ORDER BY cnt DESC')
        result['by_language'] = [dict(r) for r in cur.fetchall()]
        cur.execute('SELECT quality_name,COUNT(*) as cnt FROM analytics WHERE success=TRUE GROUP BY quality_name ORDER BY cnt DESC')
        result['by_quality'] = [dict(r) for r in cur.fetchall()]
        cur.execute('SELECT topic,COUNT(*) as cnt FROM analytics WHERE success=TRUE GROUP BY topic ORDER BY cnt DESC LIMIT 10')
        result['top_topics'] = [dict(r) for r in cur.fetchall()]
        cur.execute('SELECT country,COUNT(*) as cnt FROM analytics WHERE success=TRUE GROUP BY country ORDER BY cnt DESC LIMIT 10')
        result['top_countries'] = [dict(r) for r in cur.fetchall()]
        cur.execute('SELECT COUNT(*) as battles,COUNT(CASE WHEN status=\'ended\' THEN 1 END) as completed FROM battles')
        result['battles'] = dict(cur.fetchone())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error":str(e)}),500
    finally:
        conn.close()


# =====================================================================
# TEMPLATES
# =====================================================================
HTML_TEMPLATE  = open('index.html').read() if os.path.exists('index.html') else "<h1>Roaster AI</h1>"

BATTLE_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Roast Battle</title>
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="background:#0a0008;color:#fff;font-family:sans-serif;text-align:center;padding:40px">
<h1>⚔️ ROAST BATTLE</h1>
<h2>Topic: {{ battle.topic }}</h2>
<p>{{ battle.battle_id }} &nbsp;·&nbsp; {{ battle.status }}</p>
{% if battle.status == 'pending' %}<button onclick="acceptBattle()">⚔️ Accept Battle</button>
{% elif battle.status == 'ended' %}
<p>🏆 Winner: {{ battle.winner_id }}</p>
<a href="/battle/{{ battle.battle_id }}/card">View Result Card</a>
{% else %}<p>Battle in progress — {{ battle.total_rounds }} rounds</p>{% endif %}
<script>
const BID="{{battle.battle_id}}";
function acceptBattle(){
  const name=prompt("Your name?")||"Anonymous";
  fetch("/battle/"+BID+"/accept",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({session_id:localStorage.getItem("sid")||"guest",name})
  }).then(r=>r.json()).then(()=>location.reload());
}
</script></body></html>"""


if __name__ == '__main__':
    os.makedirs(MEMES_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
