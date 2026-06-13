import telebot
import json
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "ВСТАВЬ_ТОКЕН_БОТА"
ADMIN_ID = 7837011810

CARD_TEXT = "Оплата на карту: 0000 0000 0000 0000\nПосле оплаты отправьте скриншот чека."

bot = telebot.TeleBot(TOKEN)

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.message_handler(commands=["start"])
def start(message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛒 Каталог товаров", callback_data="catalog"))
    kb.add(InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"))
    kb.add(InlineKeyboardButton("🛠 Поддержка", url="https://t.me/your_username"))

    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в Digital Shop!\n\n"
        "Здесь можно купить цифровые товары.",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "catalog")
def catalog(call):
    products = load_json("products.json")

    kb = InlineKeyboardMarkup()
    for product_id, p in products.items():
        kb.add(InlineKeyboardButton(
            f"{p['name']} — {p['price']} грн",
            callback_data=f"product_{product_id}"
        ))

    bot.edit_message_text(
        "🛒 Каталог товаров:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
def product_info(call):
    product_id = call.data.split("_")[1]
    products = load_json("products.json")
    p = products[product_id]

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Купить", callback_data=f"buy_{product_id}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="catalog"))

    bot.edit_message_text(
        f"📦 {p['name']}\n\n"
        f"💸 Цена: {p['price']} грн\n"
        f"📝 {p['description']}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_product(call):
    product_id = call.data.split("_")[1]
    products = load_json("products.json")
    p = products[product_id]

    order_id = str(random.randint(1000, 9999))
    orders = load_json("orders.json")

    orders[order_id] = {
        "user_id": str(call.from_user.id),
        "username": call.from_user.username,
        "product_id": product_id,
        "status": "Ожидает оплату"
    }

    save_json("orders.json", orders)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📸 Я оплатил", callback_data=f"paid_{order_id}"))

    bot.edit_message_text(
        f"✅ Заказ #{order_id} создан!\n\n"
        f"📦 Товар: {p['name']}\n"
        f"💸 Цена: {p['price']} грн\n\n"
        f"{CARD_TEXT}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def paid(call):
    order_id = call.data.split("_")[1]
    bot.send_message(call.message.chat.id, f"📸 Отправьте скриншот оплаты заказа #{order_id}")
    bot.register_next_step_handler(call.message, get_receipt, order_id)

def get_receipt(message, order_id):
    orders = load_json("orders.json")
    products = load_json("products.json")

    order = orders[order_id]
    product = products[order["product_id"]]

    orders[order_id]["status"] = "Ожидает проверку"
    save_json("orders.json", orders)

    bot.send_message(message.chat.id, f"✅ Чек отправлен!\n🧾 Заказ #{order_id} ожидает проверки.")

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{order_id}"),
        InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{order_id}")
    )

    text = (
        f"🧾 Новый заказ #{order_id}\n\n"
        f"👤 Покупатель: @{order['username']}\n"
        f"🆔 ID: {order['user_id']}\n"
        f"📦 Товар: {product['name']}\n"
        f"💸 Цена: {product['price']} грн"
    )

    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=text, reply_markup=kb)
    else:
        bot.send_message(ADMIN_ID, text + "\n\n⚠️ Пользователь отправил не фото.", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve(call):
    order_id = call.data.split("_")[1]
    orders = load_json("orders.json")
    products = load_json("products.json")

    order = orders[order_id]
    product = products[order["product_id"]]

    orders[order_id]["status"] = "Выдан"
    save_json("orders.json", orders)

    bot.send_message(
        int(order["user_id"]),
        f"🎉 Оплата подтверждена!\n\n"
        f"📦 Товар: {product['name']}\n\n"
        f"🔐 Ваш товар:\n{product['content']}"
    )

    bot.answer_callback_query(call.id, "Заказ одобрен")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject(call):
    order_id = call.data.split("_")[1]
    orders = load_json("orders.json")

    order = orders[order_id]
    orders[order_id]["status"] = "Отклонён"
    save_json("orders.json", orders)

    bot.send_message(
        int(order["user_id"]),
        f"❌ Заказ #{order_id} отклонён.\n\n"
        f"Проверьте оплату или напишите в поддержку."
    )

    bot.answer_callback_query(call.id, "Заказ отклонён")

@bot.callback_query_handler(func=lambda call: call.data == "my_orders")
def my_orders(call):
    orders = load_json("orders.json")
    user_id = str(call.from_user.id)

    text = "📦 Ваши заказы:\n\n"
    found = False

    for order_id, order in orders.items():
        if order["user_id"] == user_id:
            found = True
            text += f"🧾 #{order_id} — {order['status']}\n"

    if not found:
        text = "У вас пока нет заказов."

    bot.send_message(call.message.chat.id, text)

print("Bot started")
bot.infinity_polling()
