import telebot
import json
import random
import threading
import time
import requests
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8906467783:AAFgh0Y6Yqnw8cNynkPDKnCXdR9yQMQy8BY"
ADMIN_ID = 7837011810
PING_URL = "https://supporthelp.onrender.com/"

bot = telebot.TeleBot(TOKEN)

PRODUCTS_FILE = "products.json"
ORDERS_FILE = "orders.json"

user_states = {}

BAD_WORDS = [
    "наркотик", "оружие", "скам", "обман", "кардинг",
    "слив", "18+", "порно", "взлом", "ворованный",
    "украденный", "дроп", "паспорт", "банк карта"
]

SUSPICIOUS_WORDS = [
    "аккаунт", "логин", "пароль", "cookie", "куки",
    "steam", "roblox", "telegram", "discord", "почта"
]

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

def check_product(name, description, content):
    text = f"{name} {description} {content}".lower()

    for word in BAD_WORDS:
        if word in text:
            return "reject"

    for word in SUSPICIOUS_WORDS:
        if word in text:
            return "moderation"

    if len(description) < 5:
        return "moderation"

    return "active"

def menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛒 Каталог", callback_data="catalog"))
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
        "Товары проходят автоматическую проверку.",
        reply_markup=menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "catalog")
def catalog(call):
    products = load_json(PRODUCTS_FILE)

    kb = InlineKeyboardMarkup()
    found = False

    for product_id, p in products.items():
        if p.get("status") == "active":
            found = True
            kb.add(InlineKeyboardButton(
                f"{p['name']} — {p['price']} грн",
                callback_data=f"view_{product_id}"
            ))

    if not found:
        bot.send_message(call.message.chat.id, "🛒 Каталог пуст.")
        return

    bot.send_message(call.message.chat.id, "🛒 Каталог товаров:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def view_product(call):
    product_id = call.data.split("_")[1]
    products = load_json(PRODUCTS_FILE)

    if product_id not in products or products[product_id].get("status") != "active":
        bot.send_message(call.message.chat.id, "❌ Товар недоступен.")
        return

    p = products[product_id]

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Купить", callback_data=f"buy_{product_id}"))

    seller = p.get("seller_username") or "без username"

    bot.send_message(
        call.message.chat.id,
        f"📦 Товар #{product_id}\n\n"
        f"Название: {p['name']}\n"
        f"Цена: {p['price']} грн\n"
        f"Описание: {p['description']}\n\n"
        f"Продавец: @{seller}\n\n"
        f"Карта и данные товара скрыты до покупки.",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "create_product")
def create_product(call):
    if call.from_user.username is None:
        bot.send_message(call.message.chat.id, "❌ Сначала установите username в Telegram.")
        return

    user_states[call.from_user.id] = {"step": "name", "data": {}}
    bot.send_message(call.message.chat.id, "➕ Введите название товара:")

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
        state["data"]["name"] = text[:60]
        state["step"] = "price"
        bot.send_message(message.chat.id, "💸 Введите цену в грн:")
        return

    if step == "price":
        if not text.isdigit():
            bot.send_message(message.chat.id, "❌ Цена должна быть числом.")
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
        bot.send_message(message.chat.id, "💳 Введите карту для оплаты:")
        return

    if step == "card":
        if len(text.replace(" ", "")) < 10:
            bot.send_message(message.chat.id, "❌ Карта слишком короткая.")
            return

        state["data"]["card"] = text[:80]
        state["step"] = "content"
        bot.send_message(message.chat.id, "🔐 Введите данные товара для покупателя:")
        return

    if step == "content":
        products = load_json(PRODUCTS_FILE)
        product_id = make_id(products)

        name = state["data"]["name"]
        price = state["data"]["price"]
        description = state["data"]["description"]
        card = state["data"]["card"]
        content = text[:1000]

        status = check_product(name, description, content)

        if status == "reject":
            del user_states[user_id]
            bot.send_message(
                message.chat.id,
                "❌ Товар отклонён автоматической модерацией.\n"
                "Причина: запрещённый или опасный товар."
            )
            return

        products[product_id] = {
            "seller_id": str(user_id),
            "seller_username": message.from_user.username,
            "name": name,
            "price": price,
            "description": description,
            "card": card,
            "content": content,
            "status": status
        }

        save_json(PRODUCTS_FILE, products)
        del user_states[user_id]

        if status == "active":
            bot.send_message(
                message.chat.id,
                f"✅ Товар #{product_id} создан и добавлен в каталог."
            )
        else:
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Одобрить", callback_data=f"mod_ok_{product_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"mod_no_{product_id}")
            )

            bot.send_message(
                message.chat.id,
                f"⏳ Товар #{product_id} отправлен на проверку администратору."
            )

            bot.send_message(
                ADMIN_ID,
                f"⚠️ Товар на модерации #{product_id}\n\n"
                f"Продавец: @{message.from_user.username}\n"
                f"Название: {name}\n"
                f"Цена: {price} грн\n"
                f"Описание: {description}\n\n"
                f"Данные товара скрыты от каталога.",
                reply_markup=kb
            )

@bot.callback_query_handler(func=lambda call: call.data.startswith("mod_ok_"))
def mod_ok(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа.")
        return

    product_id = call.data.split("_")[2]
    products = load_json(PRODUCTS_FILE)

    if product_id not in products:
        bot.answer_callback_query(call.id, "Товар не найден.")
        return

    products[product_id]["status"] = "active"
    save_json(PRODUCTS_FILE, products)

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except:
        pass

    bot.send_message(int(products[product_id]["seller_id"]), f"✅ Ваш товар #{product_id} одобрен.")
    bot.send_message(call.message.chat.id, f"✅ Товар #{product_id} одобрен.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("mod_no_"))
def mod_no(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа.")
        return

    product_id = call.data.split("_")[2]
    products = load_json(PRODUCTS_FILE)

    if product_id not in products:
        bot.answer_callback_query(call.id, "Товар не найден.")
        return

    seller_id = products[product_id]["seller_id"]
    del products[product_id]
    save_json(PRODUCTS_FILE, products)

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except:
        pass

    bot.send_message(int(seller_id), f"❌ Ваш товар #{product_id} отклонён.")
    bot.send_message(call.message.chat.id, f"❌ Товар #{product_id} отклонён и удалён.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy(call):
    product_id = call.data.split("_")[1]
    products = load_json(PRODUCTS_FILE)

    if product_id not in products or products[product_id].get("status") != "active":
        bot.send_message(call.message.chat.id, "❌ Товар уже куплен или недоступен.")
        return

    p = products[product_id]

    if str(call.from_user.id) == p["seller_id"]:
        bot.send_message(call.message.chat.id, "❌ Нельзя купить свой товар.")
        return

    products[product_id]["status"] = "reserved"
    save_json(PRODUCTS_FILE, products)

    orders = load_json(ORDERS_FILE)
    order_id = make_id(orders)

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
        f"После оплаты отправьте чек.",
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

    bot.send_message(call.message.chat.id, f"📸 Отправьте скриншот оплаты заказа #{order_id}")
    bot.register_next_step_handler(call.message, get_receipt, order_id)

def get_receipt(message, order_id):
    orders = load_json(ORDERS_FILE)
    products = load_json(PRODUCTS_FILE)

    if order_id not in orders:
        bot.send_message(message.chat.id, "❌ Заказ не найден.")
        return

    order = orders[order_id]

    if order["status"] != "waiting_payment":
        bot.send_message(message.chat.id, "❌ Заказ уже обработан.")
        return

    product = products[order["product_id"]]
    orders[order_id]["status"] = "waiting_seller"
    save_json(ORDERS_FILE, orders)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{order_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{order_id}")
    )

    text = (
        f"🧾 Новый чек #{order_id}\n\n"
        f"📦 Товар: {product['name']}\n"
        f"💸 Цена: {product['price']} грн\n"
        f"Покупатель: @{order.get('buyer_username') or 'без username'}"
    )

    if message.photo:
        bot.send_photo(int(order["seller_id"]), message.photo[-1].file_id, caption=text, reply_markup=kb)
    else:
        bot.send_message(int(order["seller_id"]), text + "\n\n⚠️ Не фото.", reply_markup=kb)

    bot.send_message(message.chat.id, "✅ Чек отправлен продавцу.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve(call):
    order_id = call.data.split("_")[1]
    orders = load_json(ORDERS_FILE)
    products = load_json(PRODUCTS_FILE)

    if order_id not in orders:
        return

    order = orders[order_id]

    if str(call.from_user.id) != order["seller_id"] and call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа.")
        return

    if order["status"] != "waiting_seller":
        bot.answer_callback_query(call.id, "Уже обработано.")
        return

    product = products[order["product_id"]]

    bot.send_message(
        int(order["buyer_id"]),
        f"🎉 Оплата подтверждена!\n\n"
        f"📦 Товар: {product['name']}\n\n"
        f"🔐 Данные товара:\n{product['content']}"
    )

    del products[order["product_id"]]
    orders[order_id]["status"] = "done"

    save_json(PRODUCTS_FILE, products)
    save_json(ORDERS_FILE, orders)

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except:
        pass

    bot.send_message(call.message.chat.id, "✅ Заказ подтверждён. Товар удалён из каталога.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject(call):
    order_id = call.data.split("_")[1]
    orders = load_json(ORDERS_FILE)
    products = load_json(PRODUCTS_FILE)

    if order_id not in orders:
        return

    order = orders[order_id]

    if str(call.from_user.id) != order["seller_id"] and call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа.")
        return

    if order["status"] != "waiting_seller":
        bot.answer_callback_query(call.id, "Уже обработано.")
        return

    if order["product_id"] in products:
        products[order["product_id"]]["status"] = "active"

    orders[order_id]["status"] = "rejected"

    save_json(PRODUCTS_FILE, products)
    save_json(ORDERS_FILE, orders)

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except:
        pass

    bot.send_message(int(order["buyer_id"]), "❌ Заказ отклонён. Товар вернулся в каталог.")
    bot.send_message(call.message.chat.id, "❌ Заказ отклонён.")

@bot.callback_query_handler(func=lambda call: call.data == "my_products")
def my_products(call):
    products = load_json(PRODUCTS_FILE)
    user_id = str(call.from_user.id)

    text = "📦 Ваши товары:\n\n"
    found = False

    for pid, p in products.items():
        if p.get("seller_id") == user_id:
            found = True
            text += f"#{pid} — {p['name']} — {p['price']} грн — {p['status']}\n"

    if not found:
        text = "У вас пока нет товаров."

    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "my_orders")
def my_orders(call):
    orders = load_json(ORDERS_FILE)
    user_id = str(call.from_user.id)

    text = "🧾 Ваши заказы:\n\n"
    found = False

    for oid, o in orders.items():
        if o.get("buyer_id") == user_id:
            found = True
            text += f"#{oid} — {o['status']}\n"

    if not found:
        text = "У вас пока нет заказов."

    bot.send_message(call.message.chat.id, text)

print("Bot started")

threading.Thread(target=run_web).start()
threading.Thread(target=auto_ping, daemon=True).start()

bot.infinity_polling(skip_pending=True)
