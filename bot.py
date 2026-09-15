import os
import time
import telebot
from telebot import types
from requests.exceptions import Timeout, RequestException
from backend import save_grievance, get_all_complaints
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")

bot = telebot.TeleBot(BOT_TOKEN, num_threads=4)
user_sessions = {}

def get_session(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"raw_text": None, "media_type": None, "media_file_id": None, "step": "init"}
    return user_sessions[chat_id]

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    get_session(message.chat.id)["step"] = "awaiting_evidence"
    welcome_msg = (
        "🇮🇳 **Government of India | JanSeva DPI**\n\n"
        "Welcome to the National Grievance Infrastructure. \n\n"
        "To report an issue, please send a **description**, **photo**, or **video** of the public infrastructure issue.\n\n"
        "Reply `STATUS <Ticket-ID>` at any time to track an existing grievance."
    )
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text and msg.text.strip().upper().startswith("STATUS"))
def handle_status(message):
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            return bot.reply_to(message, "⚠️ Please provide a Ticket ID. Format: `STATUS GRV-123456`")
        
        tid = parts[1]
        rows = get_all_complaints()
        ticket = next((r for r in rows if r["id"] == tid), None)
        
        if ticket:
            response = (
                f"📋 **Ticket:** `{tid}`\n"
                f"🚥 **Stage:** {ticket.get('status', 'Unknown')}\n"
                f"🏢 **Office:** {ticket.get('office_name', 'Pending Assignment')}\n"
                f"👤 **Officer:** {ticket.get('assigned_officer', 'Awaiting Nodal Officer')}\n"
                f"⚡ **Priority:** {ticket.get('severity', 'Unknown')}"
            )
            bot.reply_to(message, response, parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Ticket not found in Central Database. Please verify the ID.")
    except Exception as e:
        bot.reply_to(message, "⚠️ System error while fetching ticket status. Please try again later.")
        print(f"Status Fetch Error: {e}")

@bot.message_handler(content_types=['text', 'photo', 'video', 'animation', 'document'])
def handle_media(message):
    if message.text and message.text.startswith('/'):
        return
    cid = message.chat.id
    session = get_session(cid)
    
    session["raw_text"] = message.text or message.caption or "Evidence attached."
    
    if message.photo:
        session["media_type"], session["media_file_id"] = "photo", message.photo[-1].file_id
    elif message.video:
        session["media_type"], session["media_file_id"] = "video", message.video.file_id
    elif message.animation:
        session["media_type"], session["media_file_id"] = "video", message.animation.file_id
    elif message.document:
        session["media_type"], session["media_file_id"] = "document", message.document.file_id

    session["step"] = "awaiting_location"
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Share Exact Location", request_location=True))
    bot.send_message(cid, "✅ Evidence buffered securely.\n\nPlease tap the button below to share your live GPS location for precise spatial routing to the appropriate municipal office:", reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    cid = message.chat.id
    session = get_session(cid)
    
    if session["step"] != "awaiting_location" or not session.get("raw_text"):
        return bot.send_message(cid, "⚠️ Please provide a description or photo of the issue first.")
    
    lat = message.location.latitude
    lon = message.location.longitude
    bot.reply_to(message, "⏳ Submitting to AI Jurisdictional Router...", reply_markup=types.ReplyKeyboardRemove())
    
    try:
        res = save_grievance(
            chat_id=cid, 
            user_name=message.from_user.first_name or "Citizen", 
            raw_text=session["raw_text"], 
            media_type=session.get("media_type"), 
            media_file_id=session.get("media_file_id"), 
            lat=lat, 
            lon=lon
        )
        msg = (
            f"🇮🇳 **Ticket Logged Successfully**\n"
            f"🎫 **ID:** `{res.get('ticket_id', 'UNKNOWN')}`\n"
            f"🏢 **Routed To:** {res.get('office_name', 'Pending Assignment')}\n"
            f"👤 **Nodal Officer:** {res.get('assigned_officer', 'Awaiting Officer')}\n\n"
            f"Use `STATUS {res.get('ticket_id', 'UNKNOWN')}` to track progress."
        )
        bot.send_message(cid, msg, parse_mode="Markdown")
        
    except (Timeout, RequestException) as net_err:
        bot.send_message(cid, "⚠️ Network timeout while routing to Government Servers. Please try again in a moment.")
        print(f"Network Error: {net_err}")
    except Exception as e:
        bot.send_message(cid, "⚠️ An internal error occurred while processing your grievance. Our engineers have been notified.")
        print(f"Ingestion Error: {e}")
    finally:
        if cid in user_sessions:
            del user_sessions[cid]

if __name__ == "__main__":
    print("Govt Telegram Bot Ingestion Engine starting...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling crashed: {e}. Restarting in 10s...")
            time.sleep(10)