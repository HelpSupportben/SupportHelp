import telebot
import json
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8906467783:AAFgh0Y6Yqnw8cNynkPDKnCXdR9yQMQy8BY"
ADMIN_ID = 7837011810

bot = telebot.TeleBot(TOKEN)

PRODUCTS_FILE = "products.json"
ORDERS_FILE = "orders.json"

user_states = {}

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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
        "Здесь пользователи могут создавать и покупать цифровые товары.",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "catalog")
def catalog(call):
    products = load_json(PRODUCTS_FILE)

    if not products:
        bot.send_message(call.message.chat.id, "🛒 Каталог пуст.")
        return

    kb = InlineKeyboardMarkup()
    for product_id, p in products.items():
        kb.add(InlineKeyboardButton(
            f"{p['name']} — {p['price']} грн",
            callback_data=f"view_{product_id}"
        ))

    bot.send_message(call.message.chat.id, "🛒 Каталог товаров:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def view_product(call):
    product_id = call.data.split("_")[1]
    products = load_json(PRODUCTS_FILE)

    if product_id not in products:
        bot.send_message(call.message.chat.id, "❌ Товар не найден.")
        return

    p = products[product_id]

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Купить", callback_data=f"buy_{product_id}"))

    bot.send_message(
        call.message.chat.id,
        f"📦 Товар #{product_id}\n\n"
        f"Название: {p['name']}\n"
        f"Цена: {p['price']} грн\n"
        f"Описание: {p['description']}\n\n"
        f"Продавец: @{p.get('seller_username', 'нет username')}",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "create_product")
def create_product(call):
    user_states[call.from_user.id] = {
        "step": "name",
        "data": {}
    }

    bot.send_message(call.message.chat.id, "➕ Создание товара\n\nВведите название товара:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def product_steps(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    step = state["step"]

    if step == "name":
        state["data"]["name"] = message.text
        state["step"] = "price"
        bot.send_message(message.chat.id, "💸 Введите цену товара в грн:")
        return

    if step == "price":
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ Цена должна быть числом. Например: 100")
            return

        state["data"]["price"] = int(message.text)
        state["step"] = "description"
        bot.send_message(message.chat.id, "📝 Введите описание товара:")
        return

    if step == "description":
        state["data"]["description"] = message.text
        state["step"] = "card"
        bot.send_message(message.chat.id, "💳 Введите номер карты, куда покупатель будет оплачивать:")
        return

    if step == "card":
        state["data"]["card"] = message.text
        state["step"] = "content"
        bot.send_message(
            message.chat.id,
            "🔐 Введите данные товара, которые получит покупатель после оплаты:\n\n"
            "Например: логин, пароль, промокод, ссылка и т.д."
        )
        return

    if step == "content":
        state["data"]["content"] = message.text

        products = load_json(PRODUCTS_FILE)
        product_id = str(random.randint(1000, 9999))

        while product_id in products:
            product_id = str(random.randint(1000, 9999))

        products[product_id] = {
            "seller_id": str(user_id),
            "seller_username": message.from_user.username,
            "name": state["data"]["name"],
            "price": state["data"]["price"],
            "description": state["data"]["description"],
            "card": state["data"]["card"],
            "content": state["data"]["content"]
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

    if product_id not in products:
        bot.send_message(call.message.chat.id, "❌ Товар не найден.")
        return

    p = products[product_id]
    order_id = str(random.randint(1000, 9999))

    orders = load_json(ORDERS_FILE)
    orders[order_id] = {
        "buyer_id": str(call.from_user.id),
        "buyer_username": call.from_user.username,
        "seller_id": p["seller_id"],
        "product_id": product_id,
        "status": "Ожидает оплату"
    }

    save_json(ORDERS_FILE, orders)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📸 Я оплатил", callback_data=f"paid_{order_id}"))

    bot.send_message(
        call.message.chat.id,
        f"✅ Заказ #{order_id} создан!\n\n"
        f"📦 Товар: {p['name']}\n"
        f"💸 Цена: {p['price']} грн\n\n"
        f"💳 Оплатите на карту продавца:\n{p['card']}\n\n"
        f"После оплаты нажмите кнопку и отправьте скриншот чека.",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def paid(call):
    order_id = call.data.split("_")[1]

    bot.send_message(
        call.message.chat.id,
        f"📸 Отправьте скриншот оплаты заказа #{order_id}"
    )

    bot.register_next_step_handler(call.message, get_receipt, order_id)

def get_receipt(message, order_id):
    orders = load_json(ORDERS_FILE)
    products = load_json(PRODUCTS_FILE)

    if order_id not in orders:
        bot.send_message(message.chat.id, "❌ Заказ не найден.")
        return

    order = orders[order_id]
    product = products[order["product_id"]]

    orders[order_id]["status"] = "Ожидает проверку продавца"
    save_json(ORDERS_FILE, orders)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{order_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{order_id}")
    )

    text = (
        f"🧾 Новый чек по заказу #{order_id}\n\n"
        f"📦 Товар: {product['name']}\n"
        f"💸 Цена: {product['price']} грн\n"
        f"👤 Покупатель: @{order.get('buyer_username')}\n"
        f"🆔 ID покупателя: {order['buyer_id']}"
    )

    seller_id = int(order["seller_id"])

    if message.photo:
        bot.send_photo(
            seller_id,
            message.photo[-1].file_id,
            caption=text,
            reply_markup=kb
        )
    else:
        bot.send_message(
            seller_id,
            text + "\n\n⚠️ Покупатель отправил не фото.",
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
        bot.send_message(call.message.chat.id, "❌ Заказ не найден.")
        return

    order = orders[order_id]
    product = products[order["product_id"]]

    if str(call.from_user.id) != order["seller_id"] and call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Вы не продавец этого товара.")
        return

    orders[order_id]["status"] = "Выдан"
    save_json(ORDERS_FILE, orders)

    bot.send_message(
        int(order["buyer_id"]),
        f"🎉 Оплата подтверждена!\n\n"
        f"📦 Товар: {product['name']}\n\n"
        f"🔐 Данные товара:\n{product['content']}"
    )

    bot.send_message(
        call.message.chat.id,
        f"✅ Заказ #{order_id} подтверждён. Товар выдан покупателю."
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject_order(call):
    order_id = call.data.split("_")[1]
    orders = load_json(ORDERS_FILE)

    if order_id not in orders:
        bot.send_message(call.message.chat.id, "❌ Заказ не найден.")
        return

    order = orders[order_id]

    if str(call.from_user.id) != order["seller_id"] and call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Вы не продавец этого товара.")
        return

    orders[order_id]["status"] = "Отклонён"
    save_json(ORDERS_FILE, orders)

    bot.send_message(
        int(order["buyer_id"]),
        f"❌ Заказ #{order_id} отклонён продавцом.\n\n"
        f"Проверьте оплату или напишите продавцу."
    )

    bot.send_message(
        call.message.chat.id,
        f"❌ Заказ #{order_id} отклонён."
    )

@bot.callback_query_handler(func=lambda call: call.data == "my_products")
def my_products(call):
    products = load_json(PRODUCTS_FILE)
    user_id = str(call.from_user.id)

    text = "📦 Ваши товары:\n\n"
    found = False

    for product_id, p in products.items():
        if p["seller_id"] == user_id:
            found = True
            text += f"#{product_id} — {p['name']} — {p['price']} грн\n"

    if not found:
        text = "У вас пока нет товаров."

    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "my_orders")
def my_orders(call):
    orders = load_json(ORDERS_FILE)
    user_id = str(call.from_user.id)

    text = "🧾 Ваши заказы:\n\n"
    found = False

    for order_id, order in orders.items():
        if order["buyer_id"] == user_id:
            found = True
            text += f"#{order_id} — {order['status']}\n"

    if not found:
        text = "У вас пока нет заказов."

    bot.send_message(call.message.chat.id, text)

print("Bot started")
bot.infinity_polling()
