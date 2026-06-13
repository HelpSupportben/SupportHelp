import telebot
from telebot import types
import json
import os
import random
import threading
import time
import requests
from flask import Flask

TOKEN = "ТВОЙ_ТОКЕН_БОТА"
ADMIN_ID = 7837011810

bot = telebot.TeleBot(TOKEN)

# ---------- WEB SERVICE ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "Market Store работает!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# ---------- АВТО ПИНГ ----------
def auto_ping():
    while True:
        try:
            requests.get("https://supporthelp.onrender.com/")
        except:
            pass
        time.sleep(300)

threading.Thread(target=auto_ping).start()

# ---------- ФАЙЛЫ ----------
PRODUCTS_FILE = "products.json"
ORDERS_FILE = "orders.json"

def load_json(file_name):
    if not os.path.exists(file_name):
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(file_name, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_json(file_name, data):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

products = load_json(PRODUCTS_FILE)
orders = load_json(ORDERS_FILE)

user_states = {}

# ---------- МЕНЮ ----------
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.add("🛒 Каталог товаров")
    markup.add("➕ Создать товар")
    markup.add("📦 Мои товары", "🧾 Мои заказы")

    return markup


# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в Market Store!\n\n"
        "Маркетплейс цифровых товаров.\n"
        "Создавайте товары, покупайте и продавайте безопаснее.",
        reply_markup=main_menu()
    )


# ---------- СОЗДАТЬ ТОВАР ----------
@bot.message_handler(func=lambda m: m.text == "➕ Создать товар")
def create_product(message):
    user_states[message.chat.id] = {"step": "name"}

    bot.send_message(
        message.chat.id,
        "📦 Введите название товара:"
    )


@bot.message_handler(func=lambda m: message_state(m.chat.id, "name"))
def get_name(message):
    user_states[message.chat.id]["name"] = message.text
    user_states[message.chat.id]["step"] = "price"

    bot.send_message(
        message.chat.id,
        "💸 Введите цену товара:"
    )


@bot.message_handler(func=lambda m: message_state(m.chat.id, "price"))
def get_price(message):
    if not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ Цена должна быть числом.\nНапример: 100"
        )
        return

    user_states[message.chat.id]["price"] = message.text
    user_states[message.chat.id]["step"] = "card"

    bot.send_message(
        message.chat.id,
        "💳 Введите номер карты:"
    )


@bot.message_handler(func=lambda m: message_state(m.chat.id, "card"))
def get_card(message):
    user_states[message.chat.id]["card"] = message.text
    user_states[message.chat.id]["step"] = "description"

    bot.send_message(
        message.chat.id,
        "📝 Введите описание товара:"
    )


@bot.message_handler(func=lambda m: message_state(m.chat.id, "description"))
def get_description(message):
    user_states[message.chat.id]["description"] = message.text
    user_states[message.chat.id]["step"] = "data"

    bot.send_message(
        message.chat.id,
        "🔐 Введите данные товара:\n"
        "(логин, пароль, промокод и т.д.)"
    )


@bot.message_handler(func=lambda m: message_state(m.chat.id, "data"))
def get_data(message):
    data = user_states[message.chat.id]

    product_id = str(random.randint(1000, 9999))

    products[product_id] = {
        "name": data["name"],
        "price": data["price"],
        "card": data["card"],
        "description": data["description"],
        "product_data": message.text,
        "seller_id": message.chat.id,
        "seller_username": message.from_user.username
    }

    save_json(PRODUCTS_FILE, products)

    user_states.pop(message.chat.id)

    bot.send_message(
        message.chat.id,
        f"✅ Товар #{product_id} создан!"
    )


# ---------- КАТАЛОГ ----------
@bot.message_handler(func=lambda m: m.text == "🛒 Каталог товаров")
def catalog(message):
    if not products:
        bot.send_message(message.chat.id, "🛒 Каталог пуст.")
        return

    for product_id, product in products.items():
        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "✅ Купить",
                callback_data=f"buy_{product_id}"
            )
        )

        bot.send_message(
            message.chat.id,
            f"📦 Товар #{product_id}\n\n"
            f"Название: {product['name']}\n"
            f"Цена: {product['price']} грн\n"
            f"Описание: {product['description']}\n\n"
            f"Продавец: @{product['seller_username']}\n\n"
            f"⚠️ Карта и данные скрыты до покупки.",
            reply_markup=markup
        )


# ---------- ПОКУПКА ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_product(call):
    product_id = call.data.split("_")[1]

    if product_id not in products:
        bot.answer_callback_query(call.id, "❌ Товар уже купили")
        return

    product = products[product_id]

    order_id = str(random.randint(1000, 9999))

    orders[order_id] = {
        "buyer_id": call.message.chat.id,
        "product_id": product_id
    }

    save_json(ORDERS_FILE, orders)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data=f"approve_{order_id}"
        ),
        types.InlineKeyboardButton(
            "❌ Отклонить",
            callback_data=f"decline_{order_id}"
        )
    )

    bot.send_message(
        ADMIN_ID,
        f"🧾 Новый чек по заказу #{order_id}\n\n"
        f"📦 Товар: {product['name']}\n"
        f"💸 Цена: {product['price']} грн\n"
        f"👤 Покупатель: @{call.from_user.username}\n"
        f"🆔 ID: {call.from_user.id}",
        reply_markup=markup
    )

    bot.send_message(
        call.message.chat.id,
        f"💳 Оплатите на карту:\n"
        f"{product['card']}\n\n"
        f"После оплаты отправьте чек админу."
    )


# ---------- ПОДТВЕРЖДЕНИЕ ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):
    order_id = c.data.split("_")[1]

    if order_id not in orders:
        return

    order = orders[order_id]
    product_id = order["product_id"]

    if product_id not in products:
        return

    product = products[product_id]

    bot.send_message(
        order["buyer_id"],
        f"🎉 Оплата подтверждена!\n\n"
        f"📦 Товар: {product['name']}\n\n"
        f"🔐 Данные:\n{product['product_data']}"
    )

    del products[product_id]
    del orders[order_id]

    save_json(PRODUCTS_FILE, products)
    save_json(ORDERS_FILE, orders)

    bot.edit_message_reply_markup(
        c.message.chat.id,
        c.message.message_id,
        reply_markup=None
    )


# ---------- ОТКЛОНИТЬ ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("decline_"))
def decline(c):
    bot.edit_message_reply_markup(
        c.message.chat.id,
        c.message.message_id,
        reply_markup=None
    )

    bot.send_message(
        c.message.chat.id,
        "❌ Заказ отклонён."
    )


def message_state(chat_id, step):
    return (
        chat_id in user_states
        and user_states[chat_id]["step"] == step
    )


print("Бот запущен...")
bot.infinity_polling()
