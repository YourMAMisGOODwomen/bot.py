import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ====== НАСТРОЙКИ ======
TOKEN = "7931022784:AAGbxR3Ny8mRsNmA65NWau4-uT-bBmZ2YQU"
ADMIN_ID = 1403543095

BET_BUTTONS = [0.1, 0.2, 0.5]

# RTP: в тексте "до 89%", фактически ~60-65%
SOFT_MODE_CHANCE = 0.22  # шанс мягкого режима
SOFT_SAFE_CLICKS = 2    # только при 3 минах

# ======================

balances = {}
user_state = {}
mines_games = {}

def bal(uid):
    return round(balances.get(uid, 0.0), 2)

def add(uid, x):
    balances[uid] = round(bal(uid) + x, 2)

def sub(uid, x):
    balances[uid] = round(bal(uid) - x, 2)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    balances.setdefault(uid, 0.0)

    kb = [
        [InlineKeyboardButton("🎰 Слоты", callback_data="slots")],
        [InlineKeyboardButton("🎲 Кубик", callback_data="dice")],
        [InlineKeyboardButton("💣 Mines", callback_data="mines")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")]
    ]
    await update.message.reply_text(
        f"Добро пожаловать!\n🎯 RTP до 89%\n\n💰 Баланс: {bal(uid)} $",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------- CALLBACK ----------
async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    # ===== БАЛАНС =====
    if q.data == "balance":
        await q.message.reply_text(f"💰 Твой баланс: {bal(uid)} $")
        return

    # ===== СЛОТЫ =====
    if q.data == "slots":
        bet = 0.5
        if bal(uid) < bet:
            await q.message.reply_text("❌ Недостаточно средств")
            return
        sub(uid, bet)
        res = random.choice(["🍋", "🍓", "777", "❌"])
        mult = {"🍋": 1.5, "🍓": 1.7, "777": 2.2}
        if res in mult:
            win = round(bet * mult[res], 2)
            add(uid, win)
            await q.message.reply_text(f"🎰 {res}\n🎉 +{win}$")
        else:
            await q.message.reply_text("🎰 ❌ Проигрыш")
        return

    # ===== КУБИК =====
    if q.data == "dice":
        kb = [[
            InlineKeyboardButton("Чёт", callback_data="dice_even"),
            InlineKeyboardButton("Нечёт", callback_data="dice_odd")
        ]]
        user_state[uid] = {"bet": 0.5}
        await q.message.reply_text("🎲 Ставка 0.5$ — выбери:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if q.data.startswith("dice_"):
        bet = user_state.get(uid, {}).get("bet", 0.5)
        if bal(uid) < bet:
            await q.message.reply_text("❌ Недостаточно средств")
            return
        sub(uid, bet)
        roll = random.randint(1, 6)
        even = roll % 2 == 0
        win = (q.data == "dice_even" and even) or (q.data == "dice_odd" and not even)
        if win:
            prize = round(bet * 1.5, 2)
            add(uid, prize)
            await q.message.reply_text(f"🎲 Выпало {roll}\n🎉 +{prize}$")
        else:
            await q.message.reply_text(f"🎲 Выпало {roll}\n❌ Проигрыш")
        return

    # ===== MINES =====
    if q.data == "mines":
        kb = [
            [InlineKeyboardButton("🟦 5x5", callback_data="m_field_5")],
            [InlineKeyboardButton("🟥 10x10", callback_data="m_field_10")]
        ]
        await q.message.reply_text("💣 Выбери поле:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if q.data.startswith("m_field_"):
        size = int(q.data.split("_")[-1])
        mines_games[uid] = {"size": size}
        if size == 5:
            options = [3, 5, 7]
        else:
            options = [3, 5, 10, 15]
        kb = [[InlineKeyboardButton(f"{m} мин", callback_data=f"m_mines_{m}")] for m in options]
        await q.message.reply_text("💣 Выбери количество мин:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if q.data.startswith("m_mines_"):
        mines = int(q.data.split("_")[-1])
        mines_games[uid]["mines"] = mines
        kb = [[InlineKeyboardButton(f"{b}$", callback_data=f"m_bet_{b}")] for b in BET_BUTTONS]
        await q.message.reply_text("💰 Выбери ставку:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if q.data.startswith("m_bet_"):
        bet = float(q.data.split("_")[-1])
        if bal(uid) < bet:
            await q.message.reply_text("❌ Недостаточно средств")
            return

        game = mines_games[uid]
        size = game["size"]
        mines = game["mines"]
        total_cells = size * size

        # Генерация мин
        cells = list(range(total_cells))
        mine_positions = set(random.sample(cells, mines))

        # Мягкий режим ТОЛЬКО при 3 минах
        soft = (mines == 3 and random.random() < SOFT_MODE_CHANCE)

        mines_games[uid].update({
            "bet": bet,
            "opened": set(),
            "mine_positions": mine_positions,
            "soft": soft,
            "soft_left": SOFT_SAFE_CLICKS if soft else 0,
            "active": True
        })

        sub(uid, bet)
        await render_field(q.message, uid)
        return

    if q.data.startswith("m_cell_"):
        idx = int(q.data.split("_")[-1])
        game = mines_games.get(uid)
        if not game or not game.get("active"):
            return

        if idx in game["opened"]:
            return

        # мягкий режим
        if game["soft_left"] > 0:
            game["soft_left"] -= 1
            safe = True
        else:
            safe = idx not in game["mine_positions"]

        game["opened"].add(idx)

        if not safe:
            game["active"] = False
            await q.message.reply_text("💥 МИНА! Проигрыш.")
            return

        await render_field(q.message, uid)
        return

    if q.data == "m_cashout":
        game = mines_games.get(uid)
        if not game or not game.get("active"):
            return
        opened = len(game["opened"])
        # простая шкала множителей
        mult = 1 + opened * 0.25
        win = round(game["bet"] * mult, 2)
        add(uid, win)
        game["active"] = False
        await q.message.reply_text(f"💰 Забрал: {win}$ (x{round(mult,2)})")
        return

# ---------- RENDER MINES ----------
async def render_field(msg, uid):
    game = mines_games[uid]
    size = game["size"]
    kb = []
    for r in range(size):
        row = []
        for c in range(size):
            i = r * size + c
            if i in game["opened"]:
                row.append(InlineKeyboardButton("💎", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton("⬜", callback_data=f"m_cell_{i}"))
        kb.append(row)
    kb.append([InlineKeyboardButton("💰 Забрать", callback_data="m_cashout")])
    await msg.reply_text("💣 Mines:", reply_markup=InlineKeyboardMarkup(kb))

# ---------- ADMIN ----------
async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        uid = int(context.args[0])
        amount = float(context.args[1])
    except:
        await update.message.reply_text("Используй: /add user_id сумма")
        return
    add(uid, amount)
    await update.message.reply_text(f"✅ Начислено {amount}$ пользователю {uid}")

# ---------- RUN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT, lambda *_: None))
    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
