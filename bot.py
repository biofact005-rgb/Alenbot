import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, InputMediaPhoto
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os, threading, fitz
import os
import re
import asyncio
from pyrogram.errors import FloodWait

# ==========================================
# ⚙️ CONFIGURATION & SECRETS
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
WEB_APP_URL = os.environ.get("WEB_APP_URL") 
ADMIN_ID = 8718760365 
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "-1000000000000")) 
MAIN_CHANNEL = int(os.environ.get("MAIN_CHANNEL", BIN_CHANNEL)) # Database Channel for modified files

# Force Join Channels
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

def load_db():
    doc = db_collection.find_one({"_id": "aliesn_data"})
    if doc and "data" in doc: return doc["data"]
    return {"users": {}, "videos": [], "last_scanned_msg_id": 1}

def save_db(db_data):
    db_collection.update_one({"_id": "aliesn_data"}, {"$set": {"data": db_data}}, upsert=True)

db_data = load_db()

# ==========================================
# 📄 PDF WATERMARK & BRANDING LOGIC
# ==========================================
def process_pdf(input_pdf, output_pdf):
    doc = fitz.open(input_pdf)
    watermark_text = "@errorkids"
    footer_text = "Click for more lecture and notes join channel"
    channel_link = "https://t.me/errorkids"

    for page_num in range(len(doc)):
        page = doc[page_num]
        rect = page.rect
        
        # Diagonal Light Watermark
        page.insert_text(
            fitz.Point(rect.width / 4, rect.height / 2),
            watermark_text,
            fontsize=60,
            color=(0.5, 0.5, 0.5), 
            fill_opacity=0.15,
            rotate=45 
        )
        
        # Footer Link
        footer_point = fitz.Point(rect.width / 4, rect.height - 30)
        page.insert_text(
            footer_point,
            footer_text,
            fontsize=12,
            color=(0, 0.2, 0.8) 
        )
        link_rect = fitz.Rect(footer_point.x, footer_point.y - 12, footer_point.x + 300, footer_point.y + 5)
        page.insert_link({"kind": fitz.LINK_URI, "uri": channel_link, "from": link_rect})

    doc.save(output_pdf)
    doc.close()

# ==========================================
# 🔒 SECURITY & VERIFICATION LOGIC
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

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
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
        caption = (
            "🔒 <b>ACCESS DENIED!</b>\n\n"
            "<blockquote>⚠️ <b>Verification Required</b>\n"
            "To unlock High-Quality Ad-Free Lectures & PDFs, please join our official channels first.</blockquote>"
        )
        bot.send_photo(m.chat.id, photo=IMAGES['locked'], caption=caption, parse_mode="HTML", reply_markup=force_join_menu())
        return
        
    caption = (
        "⭐ <b>WELCOME TO ALIESN BATCH</b> ⭐\n\n"
        "<blockquote>👤 <b>Student:</b> {0}\n"
        "🆔 <b>User ID:</b> <code>{1}</code>\n"
        "🛡️ <b>Status:</b> Verified ✅</blockquote>\n\n"
        "<blockquote>🎓 Click the button below to start sending lectures!</blockquote>"
    ).format(first_name, uid)
    
    bot.send_photo(m.chat.id, photo=IMAGES['home'], caption=caption, parse_mode="HTML", reply_markup=home_menu())

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_callback(call):
    uid = str(call.from_user.id)
    first_name = call.from_user.first_name
    
    if check_joined(uid):
        bot.answer_callback_query(call.id, "✅ Verification Successful!", show_alert=False)
        caption = (
            "⭐ <b>WELCOME TO ALIESN BATCH</b> ⭐\n\n"
            "<blockquote>👤 <b>Student:</b> {0}\n"
            "🆔 <b>User ID:</b> <code>{1}</code>\n"
            "🛡️ <b>Status:</b> Verified ✅</blockquote>\n\n"
            "<blockquote>🎓 Click the button below to start sending lectures!</blockquote>"
        ).format(first_name, uid)
        
        bot.edit_message_media(
            media=InputMediaPhoto(IMAGES['home'], caption=caption, parse_mode='HTML'),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=home_menu()
        )
    else:
        bot.answer_callback_query(call.id, "❌ Please join both channels to continue!", show_alert=True)

# ==========================================
# 🔍 ADMIN AUTOMATION COMMAND (SCAN)
# ==========================================
@bot.message_handler(commands=['scan'])
def handle_scan(m):
    if str(m.from_user.id) != str(ADMIN_ID): return
    
    status_msg = bot.reply_to(m, "⏳ **Scan Started... processing from Bin Channel**", parse_mode="Markdown")
    last_id = db_data.get('last_scanned_msg_id', 1)
    current_path = None
    fails = 0
    added_count = 0
    
    for msg_id in range(last_id + 1, last_id + 300): # Scan chunk to prevent timeout
        try:
            # Forward silently to admin to inspect
            f_msg = bot.forward_message(m.chat.id, BIN_CHANNEL, msg_id, disable_notification=True)
            
            # Detect Path message
            if f_msg.text and f_msg.text.lower().startswith("path:"):
                path_str = f_msg.text.split(":", 1)[1].strip()
                current_path = [p.strip() for p in path_str.split("/") if p.strip()]
            
            # Detect Sequence Item
            elif f_msg.content_type in ['video', 'document'] and current_path:
                
                # Fetch raw file name exactly as user instructed in ledger
                if f_msg.content_type == 'document':
                    file_name = f_msg.document.file_name
                else:
                    file_name = f_msg.video.file_name if f_msg.video.file_name else "Unknown Video"
                
                title = os.path.splitext(file_name)[0]
                
                if f_msg.content_type == 'document' and file_name.lower().endswith('.pdf'):
                    # PROCESS PDF: Download -> Watermark -> Upload
                    file_info = bot.get_file(f_msg.document.file_id)
                    downloaded = bot.download_file(file_info.file_path)
                    
                    temp_in = f"temp_in_{msg_id}.pdf"
                    temp_out = f"temp_out_{msg_id}.pdf"
                    with open(temp_in, "wb") as f: f.write(downloaded)
                    
                    process_pdf(temp_in, temp_out)
                    
                    with open(temp_out, "rb") as f:
                        sent_msg = bot.send_document(
                            MAIN_CHANNEL, 
                            f, 
                            caption=f"📚 **{title}**\n\n*Extract by ERROR*", 
                            parse_mode="Markdown"
                        )
                        
                    os.remove(temp_in)
                    os.remove(temp_out)
                    new_msg_id = sent_msg.message_id
                    item_type = "document"
                else:
                    # PROCESS VIDEO: Direct Forward to save load
                    sent_msg = bot.copy_message(MAIN_CHANNEL, BIN_CHANNEL, msg_id, caption=f"🎥 **{title}**\n\n*Extract by ERROR*", parse_mode="Markdown")
                    new_msg_id = sent_msg.message_id
                    item_type = "video"
                
                # Assign to DB
                path_found = False
                if 'videos' not in db_data: db_data['videos'] = []
                
                for v in db_data['videos']:
                    if v.get('path') == current_path:
                        # Append as flat object to array
                        v.setdefault('data', []).append({"title": title, "type": item_type, "msg_id": new_msg_id})
                        path_found = True
                        break
                
                if not path_found:
                    db_data['videos'].append({
                        "path": current_path, 
                        "mode": "video", 
                        "data": [{"title": title, "type": item_type, "msg_id": new_msg_id}]
                    })
                
                added_count += 1
            
            # Cleanup admin dump message
            bot.delete_message(m.chat.id, f_msg.message_id)
            db_data['last_scanned_msg_id'] = msg_id
            save_db(db_data)
            fails = 0
            
        except Exception as e:
            fails += 1
            if fails > 15: # End of channel limit reached
                break
    
    bot.edit_message_text(f"✅ **Scan Complete!**\n📂 Safely added `{added_count}` new materials to DB.\nLast Scanned ID: `{db_data.get('last_scanned_msg_id')}`", chat_id=m.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

# ==========================================
# 🌐 API ROUTES (FLASK)
# ==========================================
@app.route('/')
def index(): return render_template('index.html') 

@app.route('/api/get_data')
def get_data():
    import json
    # Generating standard hierarchy from DB format
    tree = {}
    for doc in db_data.get('videos', []):
        path = doc.get('path', [])
        if not path: continue
        curr = tree
        for p in path[:-1]:
            if p not in curr: curr[p] = {}
            curr = curr[p]
        curr[path[-1]] = {"data": doc['data'], "mode": doc.get('mode', 'video')}
        
    return jsonify(tree)

@app.route('/api/admin/delete', methods=['POST'])
def delete_item():
    data = request.json
    if str(data.get('uid')) != str(ADMIN_ID): return jsonify({"error": "Not Admin!"})
    target = data.get('path', []) + [data.get('target')]
    db_data['videos'] = [v for v in db_data.get('videos', []) if not (v.get('path', [])[:len(target)] == target)]
    save_db(db_data)
    return jsonify({"status": "deleted"})

# 🔥 DIRECT SENDER API
@app.route('/api/send_to_chat', methods=['POST'])
def send_to_chat():
    data = request.json
    uid = data.get('uid')
    msg_id = data.get('msg_id')
    title = data.get('title')
    
    try:
        if msg_id:
            bot.copy_message(
                chat_id=uid, 
                from_chat_id=MAIN_CHANNEL, 
                message_id=int(msg_id), 
                protect_content=True, 
                caption=f"📚 **{title}**\n\n*Sent via Aliesn Batch*", 
                parse_mode="Markdown"
            )
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "Invalid Message ID"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.on_message(filters.command("upload") & filters.private)
async def process_txt_upload(client, message):
    # Check karna ki user ne kisi document (.txt) par reply kiya hai ya nahi
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("⚠️ Bhai, please ek **.txt file** par reply karke `/upload` command do.")
        return

    # Check karna ki file .txt hi hai
    file_name = message.reply_to_message.document.file_name
    if not file_name.endswith(".txt"):
        await message.reply("⚠️ Ye .txt file nahi lag rahi. Sahi format wali file bhejo.")
        return

    status_msg = await message.reply("⏳ Downloading .txt file...")
    
    # File download karna
    file_path = await message.reply_to_message.download()
    await status_msg.edit("✅ File read kar raha hoon. Uploading start...")

    current_path = "Uncategorized"
    success_count = 0

    # Txt file ko open karke line-by-line padhna
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 1. Agar line mein 'Path:' likha hai, toh DB ke liye folder path update kar lo
        if line.lower().startswith("path:"):
            current_path = line.split(":", 1)[1].strip()
            continue
        
        # 2. Agar line mein Telegram ka link hai, toh wahan se Message ID extract karna
        # Ye regex https://t.me/c/chat_id/message_id format se message id nikal lega
        link_match = re.search(r"https://t\.me/(?:c/)?\d+/(\d+)", line)
        
        if link_match:
            msg_id = int(link_match.group(1))
            
            try:
                # Bin channel se message utha kar Main Channel me copy karna
                # (Forward ki jagah copy use kar rahe hain taaki 'Forwarded from' na dikhe)
                copied_msg = await client.copy_message(
                    chat_id=MAIN_CHANNEL_ID,
                    from_chat_id=BIN_CHANNEL_ID,
                    message_id=msg_id
                )
                
                # ⬇️ YAHAN TUM APNA MONGODB WALA CODE DAAL DENA ⬇️
                # Example: db.lectures.insert_one({"path": current_path, "file_msg_id": copied_msg.id})
                
                success_count += 1
                
                # FloodWait se bachne ke liye 1.8 se 2 second ka sleep
                await asyncio.sleep(1.8) 

            except FloodWait as e:
                print(f"⚠️ Telegram rate limit! Waiting for {e.value} seconds...")
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"❌ Error aayi msg_id {msg_id} par: {e}")
                continue

    # Kaam khatam hone ke baad downloaded txt file delete kar dena server se
    if os.path.exists(file_path):
        os.remove(file_path)
        
    await status_msg.edit(f"🎉 **Upload Complete!**\nTotal **{success_count}** files successfully upload ho gayi hain aur DB update ho gaya hai.")


if __name__ == "__main__":
    t = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))))
    t.start()
    bot.infinity_polling()
