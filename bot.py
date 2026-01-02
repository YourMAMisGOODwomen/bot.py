from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# -------------------- НАСТРОЙКИ --------------------
TOKEN = "7931022784:AAGbxR3Ny8mRsNmA65NWau4-uT-bBmZ2YQU"  # <- вставь сюда токен
ADMIN_ID = 1403543095   # <- твой ID Telegram
ADMIN_USERNAME = "@pashalko_1488"

# Курс
TON_TO_USD = 1.7
STAR_TO_TON_IN = 0.007
STAR_TO_TON_OUT = 0.01

# Ставки
BET = 0.1
COMMISSION = 0.011      # 1.1% комиссия
MIN_WITHDRAW_TON = 0.5
MIN_WITHDRAW_STAR = 50
MIN_DEPOSIT_STAR = 15

# -------------------- ДАННЫЕ --------------------
balances = {}
waiting = {}
temp = {}

# -------------------- ФУНКЦИИ --------------------
def usd(x): return round(x, 5)
def bal(uid): return balances.get(uid, 0.0)
def add(uid, x): balances[uid] = round(bal(uid) + x, 5)

# -------------------- КОМАНДА /START --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    balances.setdefault(uid, 0.0)
    kb = [
        [InlineKeyboardButton("🎰 Слоты", callback_data="slot")],
        [InlineKeyboardButton("🎲 Кубик (ч/н)", callback_data="dice_menu")],
        [InlineKeyboardButton("🎳 Боулинг (<3 / >3)", callback_data="bowl_menu")],
        [InlineKeyboardButton("⚽ Футбол", callback_data="football")],
        [InlineKeyboardButton("🏀 Баскетбол", callback_data="basket")],
        [InlineKeyboardButton("📥 Ввод", callback_data="deposit")],
        [InlineKeyboardButton("📤 Вывод", callback_data="withdraw")],
    ]
    await update.message.reply_text(
        f"💰 Баланс: {bal(uid)} TON\n📥 Ввод: {ADMIN_USERNAME}\n📤 Вывод: {ADMIN_USERNAME}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# -------------------- CALLBACK --------------------
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "deposit":
        waiting[uid] = "deposit"
        await q.message.reply_text("💰 Введи сумму для пополнения (TON или ⭐)\nМинимум ⭐: 15")
        return

    if q.data == "withdraw":
        kb = [
            [InlineKeyboardButton("💎 Вывод TON", callback_data="w_ton")],
            [InlineKeyboardButton("⭐ Вывод звёздами", callback_data="w_star")],
        ]
        await q.message.reply_text("Выбери способ вывода", reply_markup=InlineKeyboardMarkup(kb))
        return

    if q.data in ("w_ton", "w_star"):
        waiting[uid] = q.data
        await q.message.reply_text("✏️ Введи количество для вывода")
        return

    if q.data == "dice_menu":
        kb = [
            [InlineKeyboardButton("Чёт", callback_data="dice_even")],
            [InlineKeyboardButton("Нечёт", callback_data="dice_odd")],
        ]
        await q.message.reply_text("🎲 Выбери", reply_markup=InlineKeyboardMarkup(kb))
        return

    if q.data == "bowl_menu":
        kb = [
            [InlineKeyboardButton("< 3", callback_data="bowl_low")],
            [InlineKeyboardButton("> 3", callback_data="bowl_high")],
        ]
        await q.message.reply_text("🎳 Выбери", reply_markup=InlineKeyboardMarkup(kb))
        return

    # ---------- ПРОВЕРКА БАЛАНСА ----------
    if bal(uid) < BET and q.data not in ("deposit", "withdraw", "dice_menu", "bowl_menu"):
        await q.message.reply_text("❌ Недостаточно баланса")
        return

    # ---------- СЛОТЫ ----------
    if q.data == "slot":
        add(uid, -BET * (1 + COMMISSION))
        msg = await q.message.reply_dice(emoji="🎰")
        v = msg.dice.value
        mult = 0
        if v in (1, 22, 43): mult = 1.5
        elif v in (16, 32, 48): mult = 1.7
        elif v == 64: mult = 2.2
        if mult:
            win = BET * mult
            add(uid, win)
            await q.message.reply_text(f"🎉 Выигрыш x{mult} → +{usd(win)} TON")
        await q.message.reply_text(f"💰 Баланс: {bal(uid)} TON")
        return

    # ---------- КУБИК ----------
    if q.data in ("dice_even", "dice_odd"):
        add(uid, -BET * (1 + COMMISSION))
        msg = await q.message.reply_dice(emoji="🎲")
        v = msg.dice.value
        win = (v % 2 == 0 and q.data == "dice_even") or (v % 2 == 1 and q.data == "dice_odd")
        if win:
            add(uid, BET * 1.5)
            await q.message.reply_text("🎉 Победа x1.5")
        await q.message.reply_text(f"💰 Баланс: {bal(uid)} TON")
        return

    # ---------- БОУЛИНГ ----------
    if q.data in ("bowl_low", "bowl_high"):
        add(uid, -BET * (1 + COMMISSION))
        msg = await q.message.reply_dice(emoji="🎳")
        v = msg.dice.value
        win = (v < 3 and q.data == "bowl_low") or (v > 3 and q.data == "bowl_high")
        if win:
            add(uid, BET * 1.5)
            await q.message.reply_text("🎉 Победа x1.5")
        await q.message.reply_text(f"💰 Баланс: {bal(uid)} TON")
        return

    # ---------- ФУТБОЛ / БАСКЕТБОЛ ----------
    if q.data in ("football", "basket"):
        add(uid, -BET * (1 + COMMISSION))
        emoji = "⚽" if q.data == "football" else "🏀"
        msg = await q.message.reply_dice(emoji=emoji)
        if msg.dice.value >= 4:
            add(uid, BET * 1.3)
            await q.message.reply_text("🎉 Победа x1.3")
        await q.message.reply_text(f"💰 Баланс: {bal(uid)} TON")
        return

# -------------------- TEXT --------------------
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in waiting:
        return
    txt = update.message.text.strip()

    # ---------- ДЕПОЗИТ ----------
    if waiting[uid] == "deposit":
        try:
            amount = float(txt)
            assert amount > 0
        except:
            await update.message.reply_text("❌ Введи число")
            return

        # Если звёзды, проверка минимума
        if amount < MIN_DEPOSIT_STAR:
            ton_amount = amount * STAR_TO_TON_IN
            if ton_amount < MIN_DEPOSIT_STAR * STAR_TO_TON_IN:
                await update.message.reply_text(f"❌ Минимум пополнения ⭐: {MIN_DEPOSIT_STAR}")
                return

        if amount >= MIN_DEPOSIT_STAR:
            # Пополнение звёздами
            ton_amount = amount * STAR_TO_TON_IN
            add(uid, ton_amount)
            await context.bot.send_message(
                ADMIN_ID,
                f"📥 Ввод ⭐\n👤 @{update.effective_user.username}\n⭐ {amount} → {usd(ton_amount)} TON\nпо поводу пополнения на {ADMIN_USERNAME}"
            )
        else:
            # Пополнение TON напрямую
            ton_amount = amount
            add(uid, ton_amount)
            await context.bot.send_message(
                ADMIN_ID,
                f"📥 Ввод TON\n👤 @{update.effective_user.username}\n💎 {usd(ton_amount)} TON"
            )

        waiting.pop(uid)
        await update.message.reply_text(f"✅ Баланс пополнен: {usd(ton_amount)} TON\n💰 Баланс: {bal(uid)} TON")
        return

    # ---------- ВЫВОД ----------
    if waiting[uid] in ("w_ton", "w_star"):
        try:
            amount = float(txt)
            assert amount > 0
        except:
            await update.message.reply_text("❌ Введи число")
            return

        if waiting[uid] == "w_ton" and amount < MIN_WITHDRAW_TON:
            await update.message.reply_text(f"❌ Минимальный вывод: {MIN_WITHDRAW_TON} TON")
            return
        elif waiting[uid] == "w_star" and amount < MIN_WITHDRAW_STAR:
            await update.message.reply_text(f"❌ Минимальный вывод: {MIN_WITHDRAW_STAR} ⭐")
            return

        temp[uid] = amount
        waiting[uid] = "wallet"
        await update.message.reply_text("👛 Введи TON-кошелёк для вывода")
        return

    if waiting[uid] == "wallet":
        wallet = txt
        amount = temp.pop(uid)

        if "w_ton" in waiting:
            ton_amount = amount
            title = f"💎 {ton_amount} TON"
        else:
            ton_amount = amount * STAR_TO_TON_OUT
            title = f"⭐ {amount}"

        if ton_amount > bal(uid):
            await update.message.reply_text("❌ Недостаточно баланса")
            waiting.pop(uid)
            return

        add(uid, -ton_amount)
        await context.bot.send_message(
            ADMIN_ID,
            f"📤 Вывод\n👤 @{update.effective_user.username}\n{title}\n💰 {usd(ton_amount)} TON\n👛 {wallet}"
        )
        waiting.pop(uid)
        await update.message.reply_text("✅ Заявка на вывод отправлена")

# -------------------- RUN --------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()

