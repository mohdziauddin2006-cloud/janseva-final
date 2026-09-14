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
    bot.reply_to(message, "🏛️ **JanSeva DPI Intake**\nDescribe the civic issue, upload media (photo/video/document), or reply `STATUS <Ticket-ID>`:")

@bot.message_handler(func=lambda msg: msg.text and msg.text.strip().upper().startswith("STATUS"))
def handle_status(message):
    ticket_id = message.text.strip().split()[1] if len(message.text.strip().split()) > 1 else None
    if not ticket_id: return bot.reply_to(message, "⚠️ Format: `STATUS GRV-123456`", parse_mode="Markdown")
    
    rows = get_all_complaints()
    ticket = next((r for r in rows if r[0] == ticket_id), None)
    if ticket:
        status, office, officer, sev = ticket[12], ticket[13], ticket[14], ticket[10]
        bot.reply_to(message, f"📋 **Ticket:** `{ticket_id}`\n🚥 **Lifecycle:** {status}\n🏢 **Jurisdiction:** {office}\n👤 **Assigned To:** {officer}\n⚡ **Priority:** {sev}", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Ticket not found in Central Ledger.")

@bot.message_handler(content_types=['text', 'photo', 'video', 'animation', 'voice', 'audio', 'document'])
def handle_media(message):
    cid = message.chat.id
    if cid not in user_sessions: user_sessions[cid] = {}
    s = user_sessions[cid]
    s["raw_text"] = message.text or message.caption or "Evidence attached."
    
    if message.photo: s["media_type"], s["media_file_id"] = "photo", message.photo[-1].file_id
    elif message.video: s["media_type"], s["media_file_id"] = "video", message.video.file_id
    elif message.animation: s["media_type"], s["media_file_id"] = "animation", message.animation.file_id
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Share Exact Location", request_location=True))
    bot.send_message(cid, "Evidence securely buffered. Share GPS location for spatial routing:", reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    cid = message.chat.id
    if cid not in user_sessions: return bot.send_message(cid, "Start by describing your issue.")
    lat, lon = message.location.latitude, message.location.longitude
    s = user_sessions[cid]
    
    bot.reply_to(message, "⏳ AI processing jurisdictional routing...", reply_markup=types.ReplyKeyboardRemove())
    res = save_grievance(cid, message.from_user.first_name, s.get("raw_text"), s.get("media_type"), s.get("media_file_id"), lat, lon)
    
    msg = (f"✅ **Ticket Logged:** `{res['ticket_id']}`\n🏢 **Routed To:** {res['office_name']}\n"
           f"👤 **Officer:** {res['assigned_officer']}\n📝 **Subject:** {res['summary']}")
    bot.send_message(cid, msg, parse_mode="Markdown")
    del user_sessions[cid]

if __name__ == "__main__":
    while True:
        try: bot.infinity_polling(skip_pending=True)
        except Exception: time.sleep(10)