import os
import time
import telebot
from telebot import types
from backend import save_grievance, get_all_complaints
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, num_threads=4)
user_sessions = {}

def get_session(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"raw_text": None, "media_type": None, "media_file_id": None, "step": "init"}
    return user_sessions[chat_id]

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    get_session(message.chat.id)["step"] = "awaiting_evidence"
    bot.reply_to(message, "🇮🇳 **JanSeva DPI**\n\nPlease send a **description**, **photo**, or **video** of the public infrastructure issue.", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text and msg.text.strip().upper().startswith("STATUS"))
def handle_status(message):
    try:
        tid = message.text.strip().split()[1]
        rows = get_all_complaints()
        ticket = next((r for r in rows if r["id"] == tid), None)
        if ticket:
            bot.reply_to(message, f"📋 **Ticket:** `{tid}`\n🚥 **Status:** {ticket.get('status', 'Unknown')}", parse_mode="Markdown")
        else: bot.reply_to(message, "❌ Ticket not found.")
    except Exception: bot.reply_to(message, "⚠️ Format: `STATUS GRV-123456`")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_media(message):
    if message.text and message.text.startswith('/'): return
    cid = message.chat.id
    session = get_session(cid)
    session["raw_text"] = message.text or message.caption or "Evidence attached."
    if message.photo: session["media_type"], session["media_file_id"] = "photo", message.photo[-1].file_id
    elif message.video: session["media_type"], session["media_file_id"] = "video", message.video.file_id
    
    session["step"] = "awaiting_location"
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Share Exact Location", request_location=True))
    bot.send_message(cid, "✅ Evidence saved. Please tap the button below to share your GPS location:", reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    cid = message.chat.id
    session = get_session(cid)
    if session["step"] != "awaiting_location": return
    bot.reply_to(message, "⏳ Submitting to Government Servers...", reply_markup=types.ReplyKeyboardRemove())
    try:
        res = save_grievance(cid, message.from_user.first_name, session["raw_text"], session.get("media_type"), session.get("media_file_id"), message.location.latitude, message.location.longitude)
        bot.send_message(cid, f"✅ **Logged Successfully**\n🎫 **ID:** `{res.get('ticket_id')}`\n🏢 **Category:** {res.get('category')}", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(cid, "⚠️ Network timeout. Please try again.")
    finally:
        if cid in user_sessions: del user_sessions[cid]

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True, timeout=60)