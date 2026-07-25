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
MAIN_CHANNEL = int(os.environ.get("MAIN_CHANNEL", "-1000000000000")) 

CHANNEL_1 = os.environ.get("CHANNEL_1", "@errorkids")
CHANNEL_2 = os.environ.get("CHANNEL_2", "@testbotupdate") 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)

MAINTENANCE_MODE = False

# 🎨 PREMIUM IMAGES
IMAGES = {
    "locked": "https://graph.org/file/95b88e6251f19b911c08f-c36ee2ffe4f047e079.jpg", 
    "home": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&q=80" 
}

from pymongo import MongoClient
MONGO_URI = os.environ.get("MONGO_URI") 
client = MongoClient(MONGO_URI)
db = client['bseb_video_db'] 
db_collection = db['app_data']
pending_coll = db['pending_posts']

def load_db():
    doc = db_collection.find_one({"_id": "aliesn_data"})
    if doc and "data" in doc: return doc["data"]
    return {"users": {}, "videos": []}

def save_db(db_data):
    db_collection.update_one({"_id": "aliesn_data"}, {"$set": {"data": db_data}}, upsert=True)

db_data = load_db()

# ==========================================
# 🔒 SECURITY & VERIFICATION LOGIC (Restored!)
# ==========================================
def check_joined(user_id):
    if str(user_id) == str(ADMIN_ID): return True
    try:
        for ch in [CHANNEL_1, CHANNEL_2]:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        return False

@bot.message_handler(commands=['maintenance'])
def toggle_maintenance(m):
    global MAINTENANCE_MODE
    if str(m.from_user.id) != str(ADMIN_ID): return
    cmd = m.text.lower()
    if "on" in cmd:
        MAINTENANCE_MODE = True
        bot.reply_to(m, "🚧 **Maintenance Mode is now ON.**\nNormal users cannot access the bot.", parse_mode="Markdown")
    else:
        MAINTENANCE_MODE = False
        bot.reply_to(m, "✅ **Maintenance Mode is now OFF.**\nBot is live for everyone.", parse_mode="Markdown")

# ==========================================
# 🚀 VIP UI MENUS
# ==========================================
def force_join_menu():
    markup = InlineKeyboardMarkup()
    try:
        markup.row(InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}", style="primary"))
        markup.row(InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}", style="primary"))
        markup.row(InlineKeyboardButton("✅ VERIFY & CONTINUE", callback_data="verify_join", style="success"))
    except TypeError:
        markup.row(InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@', '')}"))
        markup.row(InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@', '')}"))
        markup.row(InlineKeyboardButton("✅ VERIFY & CONTINUE", callback_data="verify_join"))
    return markup

def home_menu():
    markup = InlineKeyboardMarkup()
    try:
        markup.row(InlineKeyboardButton("▶️ ENTER ALIESN BATCH 🍿", web_app=WebAppInfo(url=WEB_APP_URL), style="success"))
        markup.row(
            InlineKeyboardButton("🆘 Help", url="https://t.me/errorkidk_bot", style="primary"),
            InlineKeyboardButton("🔄 Update", url="https://t.me/testbotupdate", style="primary")
        )
    except TypeError:
        markup.row(InlineKeyboardButton("▶️ ENTER ALIESN BATCH 🍿", web_app=WebAppInfo(url=WEB_APP_URL)))
        markup.row(
            InlineKeyboardButton("🆘 Help", url="https://t.me/errorkidk_bot"),
            InlineKeyboardButton("🔄 Update", url="https://t.me/testbotupdate")
        )
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    global MAINTENANCE_MODE
    uid = str(m.from_user.id)
    first_name = m.from_user.first_name
    
    if MAINTENANCE_MODE and uid != str(ADMIN_ID):
        return bot.send_photo(m.chat.id, photo=IMAGES['locked'], caption="🚧 <b>BOT IS UNDER MAINTENANCE</b> 🚧\n\n<blockquote>System is updating. Please try again later.</blockquote>", parse_mode="HTML")

    if uid not in db_data['users']:
        db_data['users'][uid] = {"name": first_name}
        save_db(db_data)
        
    if not check_joined(m.from_user.id):
        caption = "🔒 <b>ACCESS DENIED!</b>\n\n<blockquote>⚠️ <b>Verification Required</b>\nTo unlock High-Quality Ad-Free Lectures & PDFs, please join our official channels first.</blockquote>"
        bot.send_photo(m.chat.id, photo=IMAGES['locked'], caption=caption, parse_mode="HTML", reply_markup=force_join_menu())
        return
        
    caption = f"⭐ <b>WELCOME TO ALIESN BATCH</b> ⭐\n\n<blockquote>👤 <b>Student:</b> {first_name}\n🆔 <b>User ID:</b> <code>{uid}</code>\n🛡️ <b>Status:</b> Verified ✅</blockquote>\n\n<blockquote>🎓 Click the button below to start fetching HD lectures!</blockquote>"
    bot.send_photo(m.chat.id, photo=IMAGES['home'], caption=caption, parse_mode="HTML", reply_markup=home_menu())

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_callback(call):
    uid = str(call.from_user.id)
    first_name = call.from_user.first_name
    
    if check_joined(uid):
        bot.answer_callback_query(call.id, "✅ Verification Successful!", show_alert=False)
        caption = f"⭐ <b>WELCOME TO ALIESN BATCH</b> ⭐\n\n<blockquote>👤 <b>Student:</b> {first_name}\n🆔 <b>User ID:</b> <code>{uid}</code>\n🛡️ <b>Status:</b> Verified ✅</blockquote>"
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['home'], caption=caption, parse_mode='HTML'), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=home_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Please join both channels to continue!", show_alert=True)

# ==========================================
# 📥 BIN CHANNEL LISTENER (SILENT SAVER)
# ==========================================
@bot.channel_post_handler(func=lambda m: str(m.chat.id) == str(BIN_CHANNEL))
def handle_bin_post(m):
    post_data = {
        "msg_id": m.message_id,
        "text": m.text or m.caption or "",
        "type": m.content_type
    }
    if m.content_type == 'document':
        post_data['file_name'] = m.document.file_name
    pending_coll.insert_one(post_data)




# ==========================================
# ⚡ FAST TEXT-BASED BULK UPLOAD
# ==========================================
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('path:'))
def handle_text_upload(m):
    # Sirf ADMIN is command ko use kar sakta hai
    if str(m.from_user.id) != str(ADMIN_ID): return #[span_0](start_span)[span_0](end_span)

    lines = m.text.strip().split('\n')
    
    # Line 1 se path nikalna (e.g., NEET / Physics / Chapter 1)
    path_str = lines[0].split(':', 1)[1].strip()
    current_path = [x.strip() for x in path_str.split('/') if x.strip()]
    
    added_count = 0
    new_files = []
    
    # Line 2 se saare links ko read karna
    for index, line in enumerate(lines[1:]):
        link = line.strip()
        if not link.startswith('http'): 
            continue # Agar line link nahi hai, toh skip karo
            
        try:
            # Link ke aakhri hisse se msg_id nikalna
            msg_id = int(link.split('/')[-1])
            
            # Default title assign karna kyunki link me title nahi hota
            title = f"Lecture Part {index + 1}"
            
            new_files.append({
                "title": title,
                "msg_id": msg_id,
                "type": "video" # Default type video set kar rahe hain[span_1](start_span)[span_1](end_span)
            })
            added_count += 1
        except ValueError:
            pass # Agar link me ID number nahi mili, toh skip karo

    # Agar valid files mili, toh database me save karo
    if new_files:
        doc_found = False
        for v in db_data.get('videos', []): #[span_2](start_span)[span_2](end_span)
            if v.get('path') == current_path: #[span_3](start_span)[span_3](end_span)
                v.setdefault('data', []).extend(new_files) #[span_4](start_span)[span_4](end_span)
                doc_found = True
                break
                
        if not doc_found:
            db_data.setdefault('videos', []).append({ #[span_5](start_span)[span_5](end_span)
                "path": current_path, 
                "data": new_files
            })
            
        save_db(db_data) #[span_6](start_span)[span_6](end_span)
        bot.reply_to(m, f"✅ **Upload Successful!**\n🔥 Added **{added_count}** links to `{path_str}`.", parse_mode="Markdown")
    else:
        bot.reply_to(m, "❌ Koi valid link nahi mila. Format check karo.")

# ==========================================
# 🔄 /SCAN COMMAND (THE BRAHMASTRA)
# ==========================================
@bot.message_handler(commands=['scan'])
def scan_bin(m):
    if str(m.from_user.id) != str(ADMIN_ID): return
    
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
        
        if mtype == 'text' and text.lower().startswith('path:'):
            path_str = text.split(':', 1)[1].strip()
            current_path = [x.strip() for x in path_str.split('/') if x.strip()]
            pending_coll.delete_one({"_id": p['_id']})
            continue
        
        if current_path and mtype in ['video', 'document', 'audio', 'photo']:
            try:
                copied = bot.copy_message(MAIN_CHANNEL, BIN_CHANNEL, msg_id)
                new_msg_id = copied.message_id
                title = text.split('\n')[0].strip() if text else (p.get('file_name', 'Untitled').split('.')[0])
                
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

@app.route('/api/send_to_chat', methods=['POST'])
def send_to_chat():
    data = request.json
    uid = data.get('uid')
    msg_id = data.get('msg_id')
    title = data.get('title')
    item_type = data.get('type') 
    
    try:
        if msg_id:
            # Custom caption wala logic hata diya gaya hai, ab sirf protect_content rahega
            bot.copy_message(chat_id=uid, from_chat_id=MAIN_CHANNEL, message_id=msg_id, protect_content=True)
            return jsonify({"status": "success"})

        else:
            return jsonify({"error": "No ID"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/send_end_message', methods=['POST'])
def send_end_message():
    try:
        data = request.json
        uid = data.get('uid')
        
        End_message = (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>Cʜᴀᴘᴛᴇʀ Cᴏᴍᴘʟᴇᴛᴇᴅ</b> ✨\n\n"
            f"<blockquote>👤 <b>Exᴛʀᴀᴄᴛᴇᴅ & Uᴘʟᴏᴀᴅᴇᴅ ʙʏ:</b>\n"
            f"👑 <a href='https://t.me/errorkidk'>E R R O R</a> 👑</blockquote>\n\n"
            f"<i>Sᴛᴜᴅʏ Hᴀʀᴅ 📚 Aɴᴅ Dᴏɴ'ᴛ Fᴏʀɢᴇᴛ Tᴏ Sʜᴀʀᴇ Tʜɪs Bᴏᴛ Wɪᴛʜ Yᴏᴜʀ Fʀɪᴇɴᴅs! 🚀 ❤️</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        # Bot message bhejega (HTML parse mode zaroori hai tags ke liye)
        bot.send_message(
            chat_id=uid, 
            text=End_message, 
            parse_mode="HTML", 
            disable_web_page_preview=True
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"End message error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == "__main__":
    t = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))))
    t.start()
    bot.infinity_polling()
