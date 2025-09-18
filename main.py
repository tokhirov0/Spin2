import os
import json
import random
import logging
from datetime import date
from flask import Flask, request
import telebot
from dotenv import load_dotenv

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# .env faylidan o‘zgaruvchilarni yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
RENDER_URL = os.getenv("RENDER_URL")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/{BOT_TOKEN}"

if not BOT_TOKEN or not ADMIN_ID or not RENDER_URL:
    logger.error("Iltimos .env faylini to‘liq to‘ldiring!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# Foydalanuvchilar va kanallar
try:
    with open("users.json", "r") as f:
        users = json.load(f)
except:
    users = {}
    logger.info("users.json yaratildi yoki bo'sh yuklandi.")

try:
    with open("channels.json", "r") as f:
        channels = json.load(f)
except:
    channels = []
    logger.info("channels.json yaratildi yoki bo'sh yuklandi.")

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f)
    logger.info(f"{file} saqlandi.")

# /start buyrug‘i
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None

    # Kanal tekshiruvi
    if channels:
        not_subscribed = []
        for ch in channels:
            try:
                status = bot.get_chat_member(ch, int(user_id)).status
                if status in ["left", "kicked"]:
                    not_subscribed.append(ch)
            except:
                not_subscribed.append(ch)
        if not_subscribed:
            keyboard = telebot.types.InlineKeyboardMarkup()
            for ch in not_subscribed:
                keyboard.add(telebot.types.InlineKeyboardButton("Obuna bo‘lish", url=f"https://t.me/{ch[1:]}"))
            bot.send_message(user_id, "❗ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=keyboard)
            return

    # Referral bonus
    if referrer_id and referrer_id != user_id and referrer_id in users:
        users[referrer_id]["spins"] += 1
        bot.send_message(referrer_id, "🎉 Do‘stingiz botga qo‘shildi! Sizga 1 spin qo‘shildi.")

    # Yangi foydalanuvchi qo‘shish
    if user_id not in users:
        users[user_id] = {"balance": 0, "spins": 0, "referred_by": referrer_id, "last_bonus_date": None}
        save_data("users.json", users)

    # Keyboard
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🎰 Spin", "🎁 Bonus", "👤 Profil")
    keyboard.add("💸 Pul yechish", "👥 Referal")
    if int(user_id) == ADMIN_ID:
        keyboard.add("⚙️ Admin panel")
    bot.send_message(user_id, "Salom! Botga xush kelibsiz 👋", reply_markup=keyboard)

# Spin o‘yini
@bot.message_handler(func=lambda m: m.text == "🎰 Spin")
def spin_game(message):
    user_id = str(message.from_user.id)
    if users[user_id]["spins"] < 1:
        bot.send_message(user_id, "❌ Sizda spin yo‘q!")
        return

    bot.send_animation(user_id, "https://media.giphy.com/media/3o6Zta2Xv3d0Xv4zC/giphy.gif", caption="🎰 Baraban aylanmoqda...")
    reward = random.randint(1000, 10000)
    users[user_id]["balance"] += reward
    users[user_id]["spins"] -= 1
    save_data("users.json", users)
    bot.send_message(user_id, f"✅ Siz {reward} so‘m yutdingiz!\n💰 Balansingiz: {users[user_id]['balance']} so‘m")

# Kunlik bonus
@bot.message_handler(func=lambda m: m.text == "🎁 Bonus")
def daily_bonus(message):
    user_id = str(message.from_user.id)
    today = date.today().isoformat()
    if users[user_id]["last_bonus_date"] == today:
        bot.send_message(user_id, "❌ Siz bugun bonusni oldingiz!")
        return
    users[user_id]["spins"] += 1
    users[user_id]["last_bonus_date"] = today
    save_data("users.json", users)
    bot.send_message(user_id, "🎁 Sizga 1 spin qo‘shildi!")

# Profil
@bot.message_handler(func=lambda m: m.text == "👤 Profil")
def profile(message):
    user_id = str(message.from_user.id)
    data = users[user_id]
    bot.send_message(user_id, f"👤 ID: <code>{user_id}</code>\n💰 Balans: {data['balance']} so‘m\n🎰 Spinlar: {data['spins']}\n👥 Taklif qiluvchi: {data['referred_by']}")

# Pul yechish
@bot.message_handler(func=lambda m: m.text == "💸 Pul yechish")
def withdraw(message):
    user_id = str(message.from_user.id)
    msg = bot.send_message(message.chat.id, "💸 Nech pul yechasiz? (minimal 100000 so‘m)")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    user_id = str(message.from_user.id)
    try:
        amount = int(message.text)
    except:
        bot.send_message(user_id, "❌ Faqat raqam kiriting!")
        return
    if amount < 100000:
        bot.send_message(user_id, "❌ Minimal pul yechish 100000 so‘m!")
        return
    card_msg = bot.send_message(user_id, "💳 Kartangiz raqamini kiriting:")
    bot.register_next_step_handler(card_msg, lambda m: confirm_withdraw(m, amount))

def confirm_withdraw(message, amount):
    user_id = str(message.from_user.id)
    card_number = message.text
    users[user_id]["balance"] -= amount
    save_data("users.json", users)
    bot.send_message(user_id, f"✅ {amount} so‘m yechish so‘rovingiz qabul qilindi. Kartaga o‘tkazildi: {card_number}")

# Referral
@bot.message_handler(func=lambda m: m.text == "👥 Referal")
def referal(message):
    user_id = str(message.from_user.id)
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    bot.send_message(user_id, f"👥 Do‘stlaringizni taklif qiling!\nHar bir do‘st uchun 1 spin olasiz!\nReferal linkingiz:\n{referral_link}")

# Admin panel
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin panel" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ Kanal qo‘shish", "➖ Kanal o‘chirish")
    keyboard.add("📊 Statistika", "⬅️ Orqaga")
    bot.send_message(ADMIN_ID, "⚙️ Admin panelga xush kelibsiz!", reply_markup=keyboard)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot faqat Telegram orqali ishlaydi!", 200

def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook o‘rnatildi: {WEBHOOK_URL}")

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=PORT)
