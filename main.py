import telebot
from telebot import types
import json
import os
import random
import threading
import time
import requests
from flask import Flask

TOKEN = "8906467783:AAGLIan8IWevV1Pb3VjNTO3NNHltY3bnFqs"
ADMIN_ID = 7837011810

bot = telebot.TeleBot(TOKEN)

PRODUCTS_FILE = "products.json"
ORDERS_FILE = "orders.json"

app = Flask(__name__)

@app.route("/")
def home():
    return "Market Store работает!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def auto_ping():
    while True:
        try:
            requests.get("https://supporthelp.onrender.com/", timeout=10)
            print("Ping OK")
        except Exception as e:
            print("Ping error:", e)
        time.sleep(300)

def load_json(file_name):
    if not os.path.exists(file_name):
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump({}, f)

    try:
        with open(file_name, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file_name, data):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def make_id(data):
    new_id = str(random.randint(1000, 9999))
    while new_id in data:
        new_id = str(random.randint(1000, 9999))
    return new_id

user_states = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Каталог товаров")
    markup.add("➕ Создать товар")
    markup.add("📦 Мои товары", "🧾 Мои заказы")
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в Market Store!\n\n"
        "Маркетплейс цифровых товаров.",
        reply_markup=main_menu()
    )

def message_state(chat_id, step):
    return chat_id in user_states and user_states[chat_id]["step"] == step

@bot.message_handler(func=lambda m: m.text == "➕ Создать товар")
def create_product(message):
    user_states[message.chat.id] = {"step": "name", "data": {}}
    bot.send_message(message.chat.id, "📦 Введите название товара:")

@bot.message_handler(func=lambda m: message_state(m.chat.id, "name"))
def get_name(message):
    user_states[message.chat.id]["data"]["name"] = message.text
    user_states[message.chat.id]["step"] = "price"
    bot.send_message(message.chat.id, "💸 Введите цену товара:")

@bot.message_handler(func=lambda m: message_state(m.chat.id, "price"))
def get_price(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Цена должна быть числом.")
        return

    user_states[message.chat.id]["data"]["price"] = message.text
    user_states[message.chat.id]["step"] = "card"
    bot.send_message(message.chat.id, "💳 Введите номер карты:")

@bot.message_handler(func=lambda m: message_state(m.chat.id, "card"))
def get_card(message):
    user_states[message.chat.id]["data"]["card"] = message.text
    user_states[message.chat.id]["step"] = "description"
    bot.send_message(message.chat.id, "📝 Введите описание товара:")

@bot.message_handler(func=lambda m: message_state(m.chat.id, "description"))
def get_description(message):
    user_states[message.chat.id]["data"]["description"] = message.text
    user_states[message.chat.id]["step"] = "data"
    bot.send_message(message.chat.id, "🔐 Введите данные товара:")

@bot.message_handler(func=lambda m: message_state(m.chat.id, "data"))
def get_data(message):
    products = load_json(PRODUCTS_FILE)

    data = user_states[message.chat.id]["data"]
    product_id = make_id(products)

    products[product_id] = {
        "name": data["name"],
        "price": data["price"],
        "card": data["card"],
        "description": data["description"],
        "product_data": message.text,
        "seller_id": message.chat.id,
        "seller_username": message.from_user.username or "без_username"
    }

    save_json(PRODUCTS_FILE, products)
    user_states.pop(message.chat.id)

    bot.send_message(
        message.chat.id,
        f"✅ Товар #{product_id} создан и сохранён!\n\n"
        f"📦 {data['name']}\n"
        f"💸 {data['price']} грн"
    )

@bot.message_handler(func=lambda m: m.text == "🛒 Каталог товаров")
def catalog(message):
    products = load_json(PRODUCTS_FILE)

    if not products:
        bot.send_message(message.chat.id, "🛒 Каталог пуст.")
        return

    for product_id, product in products.items():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Купить", callback_data=f"buy_{product_id}"))

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_product(call):
    products = load_json(PRODUCTS_FILE)
    orders = load_json(ORDERS_FILE)

    product_id = call.data.split("_")[1]

    if product_id not in products:
        bot.answer_callback_query(call.id, "❌ Товар уже купили.")
        return

    product = products[product_id]

    if call.message.chat.id == product["seller_id"]:
        bot.answer_callback_query(call.id, "❌ Нельзя купить свой товар.")
        return

    order_id = make_id(orders)

    orders[order_id] = {
        "buyer_id": call.message.chat.id,
        "buyer_username": call.from_user.username or "без_username",
        "product_id": product_id,
        "status": "waiting"
    }

    save_json(ORDERS_FILE, orders)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{order_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{order_id}")
    )

    bot.send_message(
        int(product["seller_id"]),
        f"🧾 Новый заказ #{order_id}\n\n"
        f"📦 Товар: {product['name']}\n"
        f"💸 Цена: {product['price']} грн\n"
        f"👤 Покупатель: @{call.from_user.username or 'без_username'}",
        reply_markup=markup
    )

    bot.send_message(
        call.message.chat.id,
        f"✅ Заказ #{order_id} создан!\n\n"
        f"💳 Оплатите на карту продавца:\n{product['card']}\n\n"
        f"После оплаты продавец подтвердит заказ."
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):
    products = load_json(PRODUCTS_FILE)
    orders = load_json(ORDERS_FILE)

    order_id = c.data.split("_")[1]

    if order_id not in orders:
        bot.answer_callback_query(c.id, "Заказ не найден.")
        return

    order = orders[order_id]
    product_id = order["product_id"]

    if product_id not in products:
        bot.answer_callback_query(c.id, "Товар уже удалён.")
        return

    product = products[product_id]

    if c.message.chat.id != product["seller_id"] and c.from_user.id != ADMIN_ID:
        bot.answer_callback_query(c.id, "Нет доступа.")
        return

    bot.send_message(
        int(order["buyer_id"]),
        f"🎉 Оплата подтверждена!\n\n"
        f"📦 Товар: {product['name']}\n\n"
        f"🔐 Данные товара:\n{product['product_data']}"
    )

    del products[product_id]
    del orders[order_id]

    save_json(PRODUCTS_FILE, products)
    save_json(ORDERS_FILE, orders)

    try:
        bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=None)
    except:
        pass

    bot.send_message(c.message.chat.id, "✅ Заказ подтверждён. Товар удалён из каталога.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("decline_"))
def decline(c):
    orders = load_json(ORDERS_FILE)

    order_id = c.data.split("_")[1]

    if order_id in orders:
        buyer_id = orders[order_id]["buyer_id"]
        del orders[order_id]
        save_json(ORDERS_FILE, orders)
        bot.send_message(int(buyer_id), "❌ Заказ отклонён продавцом.")

    try:
        bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=None)
    except:
        pass

    bot.send_message(c.message.chat.id, "❌ Заказ отклонён.")

@bot.message_handler(func=lambda m: m.text == "📦 Мои товары")
def my_products(message):
    products = load_json(PRODUCTS_FILE)

    text = "📦 Ваши товары:\n\n"
    found = False

    for product_id, product in products.items():
        if product["seller_id"] == message.chat.id:
            found = True
            text += f"#{product_id} — {product['name']} — {product['price']} грн\n"

    if not found:
        text = "У вас пока нет товаров."

    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🧾 Мои заказы")
def my_orders(message):
    orders = load_json(ORDERS_FILE)

    text = "🧾 Ваши заказы:\n\n"
    found = False

    for order_id, order in orders.items():
        if order["buyer_id"] == message.chat.id:
            found = True
            text += f"#{order_id} — {order['status']}\n"

    if not found:
        text = "У вас пока нет заказов."

    bot.send_message(message.chat.id, text)

print("Бот запущен...")

threading.Thread(target=run_web).start()
threading.Thread(target=auto_ping, daemon=True).start()

bot.infinity_polling(skip_pending=True)
