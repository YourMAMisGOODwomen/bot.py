import logging
import random
import json
import asyncio
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== НАСТРОЙКИ ==================
TOKEN = "7931022784:AAGbxR3Ny8mRsNmA65NWau4-uT-bBmZ2YQU"
ADMIN_ID = 1403543095

DATA_FILE = "data.json"

TON_TO_USD = 1.7
STAR_OUT = 0.01 * TON_TO_USD
STAR_IN = 0.007 * TON_TO_USD
# ==============================================

logging.basicConfig(level=logging.INFO)

# ---------- Хранилище ----------
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "withdraws": []}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(DB, f, indent=2)

DB = load_data()

def get_user(uid, username):
    uid = str(uid)
    if uid not in DB["users"]:
        DB["users"][uid] = {
            "username": username,
            "balance": 0.0,
            "joined": str(datetime.now())
        }
        save_data()
    return DB["users"][uid]

# ---------- Клавиатуры ----------
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 Слоты", callback_data="slots"),
         InlineKeyboardButton("🎲 Кубик", callback_data="dice")],
        [InlineKeyboardButton("💣 Mines", callback_data="mines")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("➕ Депозит", callback_data="deposit"),
         InlineKeyboardButton("➖ Вывод", callback_data="withdraw")]
    ])

# ---------- Команды ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.username)
    await update.message.reply_text(
        "Добро пожаловать 👋\nВыбери действие:",
        reply_markup=main_kb()
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id, update.effective_user.username)
    await update.callback_query.message.reply_text(
        f"💰 Баланс: **{user['balance']:.2f}$**",
        parse_mode="Markdown"
    )

# ---------- Депозит ----------
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "➕ **Депозит**\n\n"
        "Для пополнения напиши админу:\n"
        "@pashalko_1488\n\n"
        "Укажи:\n"
        "• сумму\n"
        "• свой username\n"
        "• TON или Stars\n"
    )
    await update.callback_query.message.reply_text(text, parse_mode="Markdown")

# ---------- Вывод ----------
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text(
        "➖ Напиши сумму и TON-кошелёк одним сообщением\n\n"
        "Пример:\n`10 UQxxxxxxx`",
        parse_mode="Markdown"
    )
    context.user_data["wait_withdraw"] = True

async def withdraw_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("wait_withdraw"):
        return

    user = get_user(update.effective_user.id, update.effective_user.username)
    try:
        amount, wallet = update.message.text.split()
        amount = float(amount)
    except:
        await update.message.reply_text("❌ Неверный формат")
        return

    if user["balance"] < amount:
        await update.message.reply_text("❌ Недостаточно средств")
        return

    user["balance"] -= amount
    DB["withdraws"].append({
        "user": user["username"],
        "amount": amount,
        "wallet": wallet
    })
    save_data()

    await context.bot.send_message(
        ADMIN_ID,
        f"📤 ВЫВОД\n@{user['username']}\nСумма: {amount}$\nКошелёк: {wallet}"
    )

    await update.message.reply_text("✅ Заявка отправлена")
    context.user_data["wait_withdraw"] = False

# ---------- СЛОТЫ ----------
async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bet = 1.0
    user = get_user(update.effective_user.id, update.effective_user.username)
    if user["balance"] < bet:
        await update.callback_query.message.reply_text("❌ Нет баланса")
        return

    user["balance"] -= bet
    symbols = ["🍋", "🍒", "7️⃣"]
    spin = [random.choice(symbols) for _ in range(3)]

    win = 0
    if spin.count("🍋") == 3:
        win = bet * 1.5
    elif spin.count("🍒") == 3:
        win = bet * 1.7
    elif spin.count("7️⃣") == 3:
        win = bet * 2.2

    user["balance"] += win
    save_data()

    await update.callback_query.message.reply_text(
        f"{' '.join(spin)}\n"
        f"{'🎉 Выигрыш' if win else '😢 Проигрыш'} {win:.2f}$"
    )

# ---------- КУБИК ----------
async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bet = 1.0
    user = get_user(update.effective_user.id, update.effective_user.username)
    if user["balance"] < bet:
        await update.callback_query.message.reply_text("❌ Нет баланса")
        return

    user["balance"] -= bet
    roll = random.randint(1, 6)

    win = bet * 1.5 if roll % 2 == 0 else 0
    user["balance"] += win
    save_data()

    await update.callback_query.message.reply_text(
        f"🎲 Выпало: {roll}\n"
        f"{'✅ Выигрыш' if win else '❌ Проигрыш'} {win:.2f}$"
    )

# ---------- MINES ----------
async def mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bet = 1.0
    user = get_user(update.effective_user.id, update.effective_user.username)
    if user["balance"] < bet:
        await update.callback_query.message.reply_text("❌ Нет баланса")
        return

    user["balance"] -= bet
    mines = random.randint(3, 6)
    chance = max(0.2, 1 - mines * 0.15)

    if random.random() < chance:
        win = bet * 1.3
    else:
        win = 0

    user["balance"] += win
    save_data()

    await update.callback_query.message.reply_text(
        f"💣 Mines: {mines}\n"
        f"{'🎉 Победа' if win else '💥 Мина'} {win:.2f}$"
    )

# ---------- АДМИН ----------
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        username, amount = context.args
        amount = float(amount)
    except:
        await update.message.reply_text("Используй: /add @user 10")
        return

    for u in DB["users"].values():
        if u["username"] == username.replace("@", ""):
            u["balance"] += amount
            save_data()
            await update.message.reply_text("✅ Баланс начислен")
            return

    await update.message.reply_text("❌ Пользователь не найден")

# ---------- CALLBACK ----------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "balance":
        await balance(update, context)
    elif data == "deposit":
        await deposit(update, context)
    elif data == "withdraw":
        await withdraw(update, context)
    elif data == "slots":
        await slots(update, context)
    elif data == "dice":
        await dice(update, context)
    elif data == "mines":
        await mines(update, context)

# ---------- KEEP ALIVE ----------
async def keep_alive():
    while True:
        await asyncio.sleep(60)

# ---------- ЗАПУСК ----------
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_msg))

    asyncio.create_task(keep_alive())
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
