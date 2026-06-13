import telebot
import json
import os

TOKEN = "8905836608:AAFx6B17MbqH9tblWOhC8nsFmz-Rp34hRhQ"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "last_ticket": 565,
            "tickets": {}
        }

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@bot.message_handler(commands=['жалоба'])
def report(message):
    if message.chat.type == "private":
        bot.reply_to(message, "❌ Жалобы только в группе")
        return

    text = message.text.replace("/жалоба", "").strip()

    if not text:
        bot.reply_to(message, "⚠️ Напишите текст жалобы")
        return

    data = load_data()

    data["last_ticket"] += 1
    ticket_id = data["last_ticket"]

    data["tickets"][str(ticket_id)] = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "text": text,
        "status": "open"
    }

    save_data(data)

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    bot.send_message(
        message.chat.id,
        f"✅ Заявка #{ticket_id} создана!\n📩 Жалоба отправлена администрации"
    )


print("Бот запущен")
bot.infinity_polling()
