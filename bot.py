import telebot
import random
import string
import time
from flask import Flask, request, jsonify
import threading
import os

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    print("ERROR: BOT_TOKEN environment variable not set!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

# Stores generated validation codes
codes = {}

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@bot.message_handler(commands=['start', 'verify'])
def send_verify_code(message):
    user_id = message.from_user.id # This is always an integer
    
    code = generate_code()
    while code in codes:
        code = generate_code()
    
    codes[code] = {
        "user_id": user_id,
        "expires": time.time() + 300,
        "used": False
    }
    
    cleanup_expired()
    
    bot.reply_to(
        message,
        f"🔐 Your verification code is:\n\n"
        f"<code>{code}</code>\n\n"
        f"Enter this code in the app.\n"
        f"Expires in 5 minutes.\n"
        f"⚠️ Don't share this with anyone!",
        parse_mode="HTML"
    )

def cleanup_expired():
    now = time.time()
    expired = [c for c, d in codes.items() if d["expires"] < now]
    for c in expired:
        del codes[c]

def verify_code(code, user_id):
    if code not in codes:
        return False
    
    entry = codes[code]
    if entry["used"]:
        return False
    if entry["expires"] < time.time():
        del codes[code]
        return False
        
    # FIX: Convert both to integers to prevent string vs int comparison bugs
    if int(entry["user_id"]) != int(user_id):
        return False
    
    entry["used"] = True
    return True

app = Flask(__name__)

# Android App sends POST requests here
@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    if not data:
        return jsonify({"valid": False, "error": "Invalid JSON format"}), 400
        
    code = data.get('code', '').strip().upper()
    telegram_user_id = data.get('telegram_user_id')
    
    if not code or not telegram_user_id:
        return jsonify({"valid": False, "error": "Missing code or telegram_user_id"}), 400
    
    try:
        is_valid = verify_code(code, telegram_user_id)
    except ValueError:
        return jsonify({"valid": False, "error": "Invalid user ID layout format"}), 400
    
    if is_valid:
        return jsonify({"valid": True, "message": "Code verified successfully"})
    else:
        return jsonify({"valid": False, "error": "Invalid, expired, or already used code"})

# Render Health Check URL (GET Request)
@app.route('/')
def health():
    return "Bot status: Running cleanly", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    # Start the web service server in a separate thread background process
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot backend web service initialized configuration successfully...")
    bot.infinity_polling()
