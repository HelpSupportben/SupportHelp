import telebot
import json
import random
import threading
import time
import requests
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "ВСТАВЬ_ТОКЕН_БОТА"
ADMIN_ID = 7837011810
PING_URL = "https://supporthelp.onrender.com/"

bot = telebot.TeleBot(TOKEN)

PRODUCTS_FILE = "products.json"
ORDERS_FILE = "orders.json"

user_states = {}

app = Flask(__name__)

@app.route("/")
def home():
    return "Market Store bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

def auto_ping():
    while True:
        try:
            requests.get(PING_URL, timeout=10)
            print("Ping success")
        except Exception as e:
            print("Ping error:", e)
        time.sleep(240)

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def make_id(data):
    new_id = str(random.randint(1000, 9999))
    while new_id in data:
        new_id = str(random.randint(1000, 9999))
    return new_id

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛒 Каталог товаров", callback_data="catalog"))
    kb.add(InlineKeyboardButton("➕ Создать товар", callback_data="create_product"))
    kb.add(InlineKeyboardButton("📦 Мои товары", callback_data="my_products"))
    kb.add(InlineKeyboardButton("🧾 Мои заказы", callback_data="my_orders"))
    return kb

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в Market Store!\n\n"
        "Маркетплейс цифровых товаров.\n"
        "Создавайте товары, покупайте и продавайте безопаснее.",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "catalog")
def catalog(call):
    products = load_json(PRODUCTS_FILE)

    active_products = {
        pid: p for pid, p in products.items()
        if p.get("status") == "active"
    }

    if not active_products:
        bot.send_message(call.message.chat.id, "🛒 Каталог пуст.")
        return

    kb = InlineKeyboardMarkup()
    for product_id, p in active_products.items():
        kb.add(InlineKeyboardButton(
            f"{p['name']} — {p['price']} грн",
            callback_data=f"view_{product_id}"
        ))

    bot.send_message(call.message.chat.id, "🛒 Каталог товаров:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def view_product(call):
    product_id = call.data.split("_")[1]
    products = load_json(PRODUCTS_FILE)

    if product_id not in products or products[product_id].get("status") != "active":
        bot.send_message(call.message.chat.id, "❌ Товар уже куплен или удалён.")
        return

    p = products[product_id]

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Купить", callback_data=f"buy_{product_id}"))

    seller = p.get("seller_username")
    seller_text = f"@{seller}" if seller else "без username"

    bot.send_message(
        call.message.chat.id,
        f"📦 Товар #{product_id}\n\n"
        f"Название: {p['name']}\n"
        f"Цена: {p['price']} грн\n"
        f"Описание: {p['description']}\n\n"
        f"Продавец: {seller_text}\n\n"
        f"⚠️ Карта и данные товара скрыты до покупки.",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "create_product")
def create_product(call):
    if call.from_user.username is None:
        bot.send_message(call.message.chat.id, "❌ Чтобы создавать товары, установите username в Telegram.")
        return

    user_states[call.from_user.id] = {"step": "name", "data": {}}
    bot.send_message(call.message.chat.id, "➕ Создание товара\n\nВведите название товара:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def product_steps(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    step = state["step"]

    if not message.text:
        bot.send_message(message.chat.id, "❌ Отправьте текстом.")
        return

    text = message.text.strip()

    if step == "name":
        if len(text) < 2:
            bot.send_message(message.chat.id, "❌ Название слишком короткое.")
            return

        state["data"]["name"] = text[:60]
        state["step"] = "price"
        bot.send_message(message.chat.id, "💸 Введите цену товара в грн:")
        return

    if step == "price":
        if not text.isdigit():
            bot.send_message(message.chat.id, "❌ Цена должна быть числом. Например: 100")
            return

        price = int(text)
        if price < 1 or price > 100000:
            bot.send_message(message.chat.id, "❌ Цена должна быть от 1 до 100000 грн.")
            return

        state["data"]["price"] = price
        state["step"] = "description"
        bot.send_message(message.chat.id, "📝 Введите описание товара:")
        return

    if step == "description":
        state["data"]["description"] = text[:500]
        state["step"] = "card"
        bot.send_message(message.chat.id, "💳 Введите номер карты для оплаты:")
        return

    if step == "card":
        clean_card = text.replace(" ", "")

        if len(clean_card) < 10:
            bot.send_message(message.chat.id, "❌ Номер карты слишком короткий.")
            return

        state["data"]["card"] = text[:80]
        state["step"] = "content"
        bot.send_message(
            message.chat.id,
            "🔐 Введите данные товара, которые покупатель получит после подтверждения оплаты:"
        )
        return

    if step == "content":
        products = load_json(PRODUCTS_FILE)
        product_id = make_id(products)

        products[product_id] = {
            "seller_id": str(user_id),
            "seller_username": message.from_user.username,
            "name": state["data"]["name"],
            "price": state["data"]["price"],
            "description": state["data"]["description"],
            "card": state["data"]["card"],
            "content": text[:1000],
            "status": "active"
        }

        save_json(PRODUCTS_FILE, products)
        del user_states[user_id]

        bot.send_message(
            message.chat.id,
            f"✅ Товар #{product_id} создан и добавлен в каталог!\n\n"
            f"📦 Название: {products[product_id]['name']}\n"
            f"💸 Цена: {products[product_id]['price']} грн"
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_product(call):
    product_id = call.data.split("_")[1]
    products = load_json(PRODUCTS_FILE)

    if product_id not in products or products[product_id].get("status") != "active":
        bot.send_message(call.message.chat.id, "❌ Этот товар уже куплен или недоступен.")
        return

    p = products[product_id]

    if str(call.from_user.id) == p["seller_id"]:
        bot.send_message(call.message.chat.id, "❌ Нельзя купить свой товар.")
        return

    orders = load_json(ORDERS_FILE)
    order_id = make_id(orders)

    products[product_id]["status"] = "reserved"
    save_json(PRODUCTS_FILE, products)

    orders[order_id] = {
        "buyer_id": str(call.from_user.id),
        "buyer_username": call.from_user.username,
        "seller_id": p["seller_id"],
        "product_id": product_id,
        "status": "waiting_payment"
    }

    save_json(ORDERS_FILE, orders)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📸 Я оплатил", callback_data=f"paid_{order_id}"))

    bot.send_message(
        call.message.chat.id,
        f"✅ Заказ #{order_id} создан!\n\n"
        f"📦 Товар: {p['name']}\n"
        f"💸 Цена: {p['price']} грн\n\n"
        f"💳 Карта продавца:\n{p['card']}\n\n"
        f"После оплаты нажмите кнопку и отправьте скриншот чека.",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def paid(call):
    order_id = call.data.split("_")[1]
    orders = load_json(ORDERS_FILE)

    if order_id not in orders:
        bot.send_message(call.message.chat.id, "❌ Заказ не найден.")
        return

    order = orders[order_id]

    if str(call.from_user.id) != order["buyer_id"]:
        bot.send_message(call.message.chat.id, "❌ Это не ваш заказ.")
        return

    if order["status"] != "waiting_payment":
        bot.send_message(call.message.chat.id, "❌ Чек уже отправлен или заказ закрыт.")
        return

    bot.send_message(call.message.chat.id, f"📸 Отправьте скриншот оплаты заказа #{order_id}")
    bot.register_next_step_handler(call.message, get_receipt, order_id)

def get_receipt(message, order_id):
    orders = load_json(ORDERS_FILE)
    products = load_json(PRODUCTS_FILE)

    if order_id not in orders:
        bot.send_message(message.chat.id, "❌ Заказ не найден.")
        return

    order = orders[order_id]

    if str(message.from_user.id) != order["buyer_id"]:
        bot.send_message(message.chat.id, "❌ Это не ваш заказ.")
        return

    if order["status"] != "waiting_payment":
        bot.send_message(message.chat.id, "❌ Чек уже отправлен.")
        return

    product_id = order["product_id"]

    if product_id not in products:
        bot.send_message(message.chat.id, "❌ Товар не найден.")
        return

    product = products[product_id]
    orders[order_id]["status"] = "waiting_seller"
    save_json(ORDERS_FILE, orders)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{order_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{order_id}")
    )

    buyer_username = order.get("buyer_username")
    buyer_text = f"@{buyer_username}" if buyer_username else "без username"

    text_for_seller = (
        f"🧾 Новый чек по заказу #{order_id}\n\n"
        f"📦 Товар: {product['name']}\n"
        f"💸 Цена: {product['price']} грн\n"
        f"👤 Покупатель: {buyer_text}\n"
        f"🆔 ID покупателя: {order['buyer_id']}\n\n"
        f"Подтвердите только если деньги реально пришли."
    )

    seller_id = int(order["seller_id"])

    if message.photo:
        bot.send_photo(
            seller_id,
            message.photo[-1].file_id,
            caption=text_for_seller,
            reply_markup=kb
        )
    else:
        bot.send_message(
            seller_id,
            text_for_seller + "\n\n⚠️ Покупатель отправил не фото.",
            reply_markup=kb
        )

    bot.send_message(
        message.chat.id,
        f"✅ Чек отправлен продавцу!\n\n"
        f"🧾 Заказ #{order_id}\n"
        f"⏳ Ожидайте подтверждения."
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_order(call):
    order_id = call.data.split("_")[1]
    orders = load_json(ORDERS_FILE)
    products = load_json(PRODUCTS_FILE)

    if order_id not in orders:
        bot.answer_callback_query(call.id, "Заказ не найден.")
        return

    order = orders[order_id]

    if order["status"] != "waiting_seller":
        bot.answer_callback_query(call.id, "Заказ уже обработан.")
        return

    if str(call.from_user.id) != order["seller_id"] and call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Вы не продавец этого товара.")
        return

    product_id = order["product_id"]

    if product_id not in products:
        bot.answer_callback_query(call.id, "Товар не найден.")
        return

    product = products[product_id]

    orders[order_id]["status"] = "done"
    products[product_id]["status"] = "sold"

    save_json(ORDERS_FILE, orders)
    save_json(PRODUCTS_FILE, products)

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except:
        pass

    bot.send_message(
        int(order["buyer_id"]),
        f"🎉 Оплата подтверждена!\n\n"
        f"📦 Товар: {product['name']}\n\n"
        f"🔐 Данные товара:\n{product['content']}"
    )

    bot.send_message(
        call.message.chat.id,
        f"✅ Заказ #{order_id} подтверждён. Товар выдан покупателю.\n\n"
        f"Товар убран из каталога."
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject_order(call):
    order_id = call.data.split("_")[1]
    orders = load_json(ORDERS_FILE)
    products = load_json(PRODUCTS_FILE)

    if order_id not in orders:
        bot.answer_callback_query(call.id, "Заказ не найден.")
        return

    order = orders[order_id]

    if order["status"] != "waiting_seller":
        bot.answer_callback_query(call.id, "Заказ уже обработан.")
        return

    if str(call.from_user.id) != order["seller_id"] and call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Вы не продавец этого товара.")
        return

    product_id = order["product_id"]

    orders[order_id]["status"] = "rejected"

    if product_id in products:
        products[product_id]["status"] = "active"

    save_json(ORDERS_FILE, orders)
    save_json(PRODUCTS_FILE, products)

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except:
        pass

    bot.send_message(
        int(order["buyer_id"]),
        f"❌ Заказ #{order_id} отклонён продавцом.\n\n"
        f"Товар снова доступен в каталоге."
    )

    bot.send_message(
        call.message.chat.id,
        f"❌ Заказ #{order_id} отклонён. Товар возвращён в каталог."
    )

@bot.callback_query_handler(func=lambda call: call.data == "my_products")
def my_products(call):
    products = load_json(PRODUCTS_FILE)
    user_id = str(call.from_user.id)

    text = "📦 Ваши товары:\n\n"
    found = False

    for product_id, p in products.items():
        if p.get("seller_id") == user_id:
            found = True
            text += f"#{product_id} — {p['name']} — {p['price']} грн — {p.get('status')}\n"

    if not found:
        text = "У вас пока нет товаров."

    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "my_orders")
def my_orders(call):
    orders = load_json(ORDERS_FILE)
    products = load_json(PRODUCTS_FILE)
    user_id = str(call.from_user.id)

    text = "🧾 Ваши заказы:\n\n"
    found = False

    for order_id, order in orders.items():
        if order.get("buyer_id") == user_id:
            found = True
            product = products.get(order["product_id"], {})
            text += f"#{order_id} — {product.get('name', 'товар')} — {order.get('status')}\n"

    if not found:
        text = "У вас пока нет заказов."

    bot.send_message(call.message.chat.id, text)

print("Bot started")

threading.Thread(target=run_web).start()
threading.Thread(target=auto_ping, daemon=True).start()

bot.infinity_polling(skip_pending=True)
