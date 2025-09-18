import os
import json
import random
import logging
from datetime import date
from flask import Flask, request
import telebot
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
RENDER_URL = os.getenv("RENDER_URL")
PORT = int(os.getenv("PORT", 10000))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# Users va kanallar
if os.path.exists("users.json"):
    with open("users.json", "r") as f:
        users = json.load(f)
else:
    users = {}

if os.path.exists("channels.json"):
    with open("channels.json", "r") as f:
        channels = json.load(f)
else:
    channels = []

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# Start handler
@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.from_user.id)
    if user_id not in users:
        users[user_id] = {"balance":0, "spins":0, "referred_by":None, "last_bonus_date":None, "ref_count":0}
        save_data("users.json", users)
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🎰 Spin", "🎁 Bonus", "👤 Profil")
    keyboard.add("💸 Pul yechish", "👥 Referal")
    if int(user_id) == ADMIN_ID:
        keyboard.add("⚙️ Admin panel")
    bot.send_message(user_id, "Salom! Botga xush kelibsiz 👋", reply_markup=keyboard)

# Spin
@bot.message_handler(func=lambda m: m.text=="🎰 Spin")
def spin_game(message):
    user_id = str(message.from_user.id)
    spins = users[user_id]["spins"]
    if spins < 1:
        bot.send_message(user_id,"❌ Sizda spin yo‘q! Referral orqali ishlang.")
        return
    bot.send_animation(user_id,"https://media.giphy.com/media/3o6Zta2Xv3d0Xv4zC/giphy.gif", caption="🎰 Baraban aylanmoqda...")
    reward = random.randint(1000,10000)
    users[user_id]["balance"] += reward
    users[user_id]["spins"] -= 1
    save_data("users.json", users)
    bot.send_message(user_id,f"✅ Siz {reward} so‘m yutdingiz!\n💰 Balansingiz: {users[user_id]['balance']} so‘m")

# Daily bonus
@bot.message_handler(func=lambda m: m.text=="🎁 Bonus")
def daily_bonus(message):
    user_id = str(message.from_user.id)
    today = str(date.today())
    if users[user_id]["last_bonus_date"] == today:
        bot.send_message(user_id,"❌ Siz bugun bonus oldingiz, ertaga qayta urinib ko‘ring!")
        return
    users[user_id]["spins"] += 1
    users[user_id]["last_bonus_date"] = today
    save_data("users.json", users)
    bot.send_message(user_id,"🎁 Sizga 1 spin berildi!")

# Profil
@bot.message_handler(func=lambda m: m.text=="👤 Profil")
def profile(message):
    user_id = str(message.from_user.id)
    data = users[user_id]
    bot.send_message(user_id,f"👤 ID: {user_id}\n💰 Balans: {data['balance']} so‘m\n🎰 Spinlar: {data['spins']}\n👥 Taklif qiluvchi: {data['referred_by']}")

# Pul yechish
@bot.message_handler(func=lambda m: m.text=="💸 Pul yechish")
def withdraw(message):
    user_id = str(message.from_user.id)
    msg = bot.send_message(message.chat.id,"💸 Yechmoqchi bo‘lgan summani yozing (minimal 100000 so‘m):")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    user_id = str(message.from_user.id)
    try:
        amount = int(message.text)
    except:
        bot.send_message(user_id,"❌ Faqat raqam kiriting!")
        return
    if amount < 100000:
        bot.send_message(user_id,"❌ Minimal pul yechish 100000 so‘m!")
        return
    # Keyingi: karta raqam, summani tasdiqlash
    bot.send_message(user_id,f"✅ Pul yechish so‘rovi qabul qilindi: {amount} so‘m")
    users[user_id]["balance"] -= amount
    save_data("users.json",users)

# Referal
@bot.message_handler(func=lambda m: m.text=="👥 Referal")
def referal(message):
    user_id = str(message.from_user.id)
    referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(user_id,f"👥 Do‘stlaringizni taklif qiling!\nHar bir do‘st uchun 1 spin olasiz!\nReferal linkingiz:\n{referral_link}")

# Admin panel
@bot.message_handler(func=lambda m: m.text=="⚙️ Admin panel" and m.from_user.id==ADMIN_ID)
def admin_panel(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ Kanal qo‘shish","➖ Kanal o‘chirish")
    keyboard.add("📊 Statistika","⬅️ Orqaga")
    bot.send_message(ADMIN_ID,"⚙️ Admin panelga xush kelibsiz!",reply_markup=keyboard)

# Kanal qo‘shish/o‘chirish va statistika funksiyalari...
# (shu yerda kanal va referal statistika kodlari)

# Webhook Flask
@app.route("/"+BOT_TOKEN,methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK",200

@app.route("/")
def index():
    return "Bot faqat Telegram orqali ishlaydi!",200

def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL+"/"+BOT_TOKEN)

if __name__=="__main__":
    set_webhook()
    app.run(host="0.0.0.0",port=PORT)
