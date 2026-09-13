import os
import time
import telebot
from telebot import types
from backend import save_grievance

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_sessions[message.chat.id] = {"raw_text": None, "media_type": None, "media_file_id": None}
    bot.reply_to(message, "🏛️ **JanSeva AI**\nPlease describe your issue or upload a photo/video/audio:")

# Added 'animation', 'audio', and 'document' to the allowed list
@bot.message_handler(content_types=['text', 'photo', 'video', 'animation', 'voice', 'audio', 'document'])
def handle_media(message):
    cid = message.chat.id
    if cid not in user_sessions:
        user_sessions[cid] = {}
    
    s = user_sessions[cid]
    s["raw_text"] = message.text or message.caption or "Evidence attached."
    
    # Safely extract the file ID no matter what type of media it is
    if message.photo: s["media_type"], s["media_file_id"] = "photo", message.photo[-1].file_id
    elif message.video: s["media_type"], s["media_file_id"] = "video", message.video.file_id
    elif message.animation: s["media_type"], s["media_file_id"] = "animation", message.animation.file_id
    elif message.voice: s["media_type"], s["media_file_id"] = "voice", message.voice.file_id
    elif message.audio: s["media_type"], s["media_file_id"] = "audio", message.audio.file_id
    elif message.document: s["media_type"], s["media_file_id"] = "document", message.document.file_id
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Share Exact Location", request_location=True))
    bot.send_message(cid, "Evidence saved. Please share your GPS location to check for nearby hazards:", reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    cid = message.chat.id
    if cid not in user_sessions:
        return bot.send_message(cid, "Start by describing your issue or sending media.")

    lat, lon = message.location.latitude, message.location.longitude
    s = user_sessions[cid]
    u_name = message.from_user.first_name
    
    bot.reply_to(message, "⏳ Analyzing with AI & scanning 50m radius...", reply_markup=types.ReplyKeyboardRemove())
    
    res = save_grievance(cid, u_name, s.get("raw_text"), s.get("media_type"), s.get("media_file_id"), lat, lon)
    
    msg = (f"✅ **Ticket Logged:** `{res['ticket_id']}`\n"
           f"📁 Dept: {res['category']}\n⚡ Priority: {res['severity']}\n"
           f"📝 AI Summary: {res['summary']}")
    bot.send_message(cid, msg, parse_mode="Markdown")
    del user_sessions[cid]

if __name__ == "__main__":
    while True:
        try:
            print("🤖 Bot running...")
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print("Waiting for old Render instance to close...")
            time.sleep(10)