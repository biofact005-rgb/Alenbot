import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, InputMediaPhoto
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os, threading

# ==========================================
# ⚙️ CONFIGURATION & SECRETS
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
WEB_APP_URL = os.environ.get("WEB_APP_URL") 
ADMIN_ID = 8718760365 
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "-1000000000000")) 
MAIN_CHANNEL = int(os.environ.get("MAIN_CHANNEL", "-1000000000000")) # Yaha save honge final scanned messages

# Force Join Channels
CHANNEL_1 = os.environ.get("CHANNEL_1", "@errorkids")
CHANNEL_2 = os.environ.get("CHANNEL_2", "@testbotupdate") 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)

# 🎨 PREMIUM IMAGES
IMAGES = {
    "home": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&q=80" 
}

from pymongo import MongoClient
MONGO_URI = os.environ.get("MONGO_URI") 
client = MongoClient(MONGO_URI)
db = client['bseb_video_db'] 
db_collection = db['app_data']
pending_coll = db['pending_posts'] # Isme BIN channel ka data temporarily save hoga

def load_db():
    doc = db_collection.find_one({"_id": "aliesn_data"})
    if doc and "data" in doc: return doc["data"]
    return {"users": {}, "videos": []}

def save_db(db_data):
    db_collection.update_one({"_id": "aliesn_data"}, {"$set": {"data": db_data}}, upsert=True)

db_data = load_db()

# ==========================================
# 🚀 VIP UI MENUS
# ==========================================
def home_menu():
    markup = InlineKeyboardMarkup()
    try:
        markup.row(InlineKeyboardButton("▶️ ENTER ALIESN BATCH 🍿", web_app=WebAppInfo(url=WEB_APP_URL), style="success"))
    except TypeError:
        markup.row(InlineKeyboardButton("▶️ ENTER ALIESN BATCH 🍿", web_app=WebAppInfo(url=WEB_APP_URL)))
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    first_name = m.from_user.first_name
    
    if uid not in db_data['users']:
        db_data['users'][uid] = {"name": first_name}
        save_db(db_data)
        
    caption = f"⭐ <b>WELCOME TO ALIESN BATCH</b> ⭐\n\n<blockquote>👤 <b>Student:</b> {first_name}\n🆔 <b>User ID:</b> <code>{uid}</code>\n🛡️ <b>Status:</b> Verified ✅</blockquote>"
    bot.send_photo(m.chat.id, photo=IMAGES['home'], caption=caption, parse_mode="HTML", reply_markup=home_menu())

# ==========================================
# 📥 BIN CHANNEL LISTENER (SILENT SAVER)
# ==========================================
@bot.channel_post_handler(func=lambda m: str(m.chat.id) == str(BIN_CHANNEL))
def handle_bin_post(m):
    # Jo bhi BIN me aayega, database me chup chap save ho jayega
    post_data = {
        "msg_id": m.message_id,
        "text": m.text or m.caption or "",
        "type": m.content_type
    }
    if m.content_type == 'document':
        post_data['file_name'] = m.document.file_name
    
    pending_coll.insert_one(post_data)

# ==========================================
# 🔄 /SCAN COMMAND (THE BRAHMASTRA)
# ==========================================
@bot.message_handler(commands=['scan'])
def scan_bin(m):
    if str(m.from_user.id) != str(ADMIN_ID): return
    
    # 1. Pura pending data uthao (Line wise)
    pending = list(pending_coll.find().sort("msg_id", 1))
    if not pending:
        return bot.reply_to(m, "⚠️ **No new messages in Bin Channel to scan.**", parse_mode="Markdown")
    
    bot.reply_to(m, f"⏳ **Scanning {len(pending)} pending messages...**", parse_mode="Markdown")
    
    current_path = []
    added_count = 0
    
    for p in pending:
        msg_id = p['msg_id']
        text = p['text']
        mtype = p['type']
        
        # Check if message is setting a Path (e.g. "Path: Batch / PHY / CH 1")
        if mtype == 'text' and text.lower().startswith('path:'):
            path_str = text.split(':', 1)[1].strip()
            current_path = [x.strip() for x in path_str.split('/') if x.strip()]
            
            # Message read ho gaya, list se delete kardo
            pending_coll.delete_one({"_id": p['_id']})
            continue
        
        # Agar media hai aur Path set hai toh process karo
        if current_path and mtype in ['video', 'document', 'audio', 'photo']:
            try:
                # Coping from Bin Channel to Main Channel
                copied = bot.copy_message(MAIN_CHANNEL, BIN_CHANNEL, msg_id)
                new_msg_id = copied.message_id
                
                # Extract clean title
                title = text.split('\n')[0].strip() if text else (p.get('file_name', 'Untitled').split('.')[0])
                
                # Database me Insert logic
                doc_found = False
                for v in db_data.get('videos', []):
                    if v.get('path') == current_path:
                        v.setdefault('data', []).append({"title": title, "msg_id": new_msg_id, "type": mtype})
                        doc_found = True
                        break
                        
                if not doc_found:
                    db_data.setdefault('videos', []).append({
                        "path": current_path, 
                        "data": [{"title": title, "msg_id": new_msg_id, "type": mtype}]
                    })
                
                added_count += 1
            except Exception as e:
                print(f"Error copying msg {msg_id}: {e}")
                
        # Kaam hone ke baad us item ko pending list se hamesha ke liye delete kardo
        pending_coll.delete_one({"_id": p['_id']})
        
    save_db(db_data)
    bot.reply_to(m, f"✅ **Scan Complete!**\n🔥 Added **{added_count}** files to the App library.", parse_mode="Markdown")

# ==========================================
# 🌐 API ROUTES (FLASK)
# ==========================================
@app.route('/')
def index(): return render_template('index.html') 

@app.route('/api/get_data')
def get_data():
    tree = {}
    for doc in db_data.get('videos', []):
        path = doc.get('path', [])
        if not path: continue
        curr = tree
        for p in path[:-1]:
            if p not in curr: curr[p] = {}
            curr = curr[p]
        # Data attach karte hain directly us branch me
        curr[path[-1]] = {"data": doc['data']}
        
    return jsonify(tree)

@app.route('/api/admin/delete', methods=['POST'])
def delete_item():
    data = request.json
    if str(data.get('uid')) != str(ADMIN_ID): return jsonify({"error": "Not Admin!"})
    target = data.get('path', []) + [data.get('target')]
    db_data['videos'] = [v for v in db_data.get('videos', []) if not (v.get('path', [])[:len(target)] == target)]
    save_db(db_data)
    return jsonify({"status": "deleted"})

# 🔥 FASTEST FILE SENDER API
@app.route('/api/send_to_chat', methods=['POST'])
def send_to_chat():
    data = request.json
    uid = data.get('uid')
    msg_id = data.get('msg_id')
    title = data.get('title')
    item_type = data.get('type') 
    
    try:
        if msg_id:
            caption = f"📚 **{title}**\n\n*Downloaded via Aliesn Batch*"
            # Copy Message directly from Main Channel
            bot.copy_message(chat_id=uid, from_chat_id=MAIN_CHANNEL, message_id=msg_id, protect_content=True, caption=caption, parse_mode="Markdown")
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "No ID"})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    t = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))))
    t.start()
    bot.infinity_polling()
