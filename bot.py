import os
import time
import telebot
from telebot import types
from backend import save_grievance, get_all_complaints

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_sessions[message.chat.id] = {"raw_text": None, "media_type": None, "media_file_id": None}
    bot.reply_to(message, "🏛️ **JanSeva DPI**\nWelcome. Describe the public issue, upload a photo/video, or reply `STATUS <Ticket-ID>` to track an existing grievance:")

@bot.message_handler(func=lambda msg: msg.text and msg.text.strip().upper().startswith("STATUS"))
def handle_status(message):
    tid = message.text.strip().split()[1] if len(message.text.strip().split()) > 1 else None
    if not tid: return bot.reply_to(message, "⚠️ Format: `STATUS GRV-123456`")
    
    rows = get_all_complaints()
    ticket = next((r for r in rows if r["id"] == tid), None)
    if ticket:
        bot.reply_to(message, f"📋 **Ticket:** `{tid}`\n🚥 **Stage:** {ticket['status']}\n🏢 **Office:** {ticket['office_name']}\n👤 **Officer:** {ticket['assigned_officer']}\n⚡ **Priority:** {ticket['severity']}", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Ticket not found in Central Database.")

# Added animation (GIF) and document support
@bot.message_handler(content_types=['text', 'photo', 'video', 'animation', 'document'])
def handle_media(message):
    cid = message.chat.id
    if cid not in user_sessions: user_sessions[cid] = {}
    s = user_sessions[cid]
    s["raw_text"] = message.text or message.caption or "Evidence attached."
    
    if message.photo: 
        s["media_type"], s["media_file_id"] = "photo", message.photo[-1].file_id
    elif message.video: 
        s["media_type"], s["media_file_id"] = "video", message.video.file_id
    elif message.animation: 
        s["media_type"], s["media_file_id"] = "video", message.animation.file_id
    elif message.document: 
        s["media_type"], s["media_file_id"] = "document", message.document.file_id
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Share Exact Location", request_location=True))
    bot.send_message(cid, "Evidence buffered successfully. Please share your live GPS location for precise spatial routing:", reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    cid = message.chat.id
    if cid not in user_sessions: return bot.send_message(cid, "Start by describing your issue.")
    lat, lon = message.location.latitude, message.location.longitude
    s = user_sessions[cid]
    
    bot.reply_to(message, "⏳ AI processing jurisdictional routing...", reply_markup=types.ReplyKeyboardRemove())
    res = save_grievance(cid, message.from_user.first_name, s.get("raw_text"), s.get("media_type"), s.get("media_file_id"), lat, lon)
    msg = f"✅ **Ticket Logged:** `{res['ticket_id']}`\n🏢 **Routed To:** {res['office_name']}\n👤 **Officer:** {res['assigned_officer']}"
    bot.send_message(cid, msg, parse_mode="Markdown")
    del user_sessions[cid]

if __name__ == "__main__":
    while True:
        try: bot.infinity_polling(skip_pending=True)
        except Exception: time.sleep(10)