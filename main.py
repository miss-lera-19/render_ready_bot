import os
import logging
import asyncio
import time
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, JobQueue

# === БАЗОВІ ДАНІ ===
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

STARTING_MARGIN = 100
LEVERAGE = {
    "SOL": 300,
    "BTC": 500,
    "ETH": 500
}

user_margin = STARTING_MARGIN
user_leverage = LEVERAGE.copy()
active_coins = ["SOL", "BTC", "ETH"]

# === ЛОГУВАННЯ ===
logging.basicConfig(level=logging.INFO)

# === API MEXC ===
def get_price(symbol: str):
    try:
        response = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT")
        price = float(response.json()["price"])
        return price
    except Exception:
        return None

# === СТРАТЕГІЯ ===
def generate_signal(symbol: str, price: float):
    impulse_up = price % 10 < 5  # спрощений тригер
    direction = "LONG" if impulse_up else "SHORT"

    entry_price = price
    sl = round(price * (0.995 if direction == "LONG" else 1.005), 2)
    tp = round(price * (1.05 if direction == "LONG" else 0.95), 2)

    margin = user_margin
    leverage = user_leverage.get(symbol, 100)
    volume = round(margin * leverage / price, 4)

    signal = f"""
📢 <b>{symbol}/USDT</b> — <b>{direction}</b> сигнал

🔹 Вхід: <b>{entry_price}</b>
🔻 SL: <b>{sl}</b>
🔺 TP: <b>{tp}</b>
💰 Маржа: <b>{margin}$</b>
📈 Плече: <b>{leverage}×</b>
📊 Обʼєм: <b>{volume} {symbol}</b>
"""
    return signal

# === ПЕРЕВІРКА РИНКУ ===
async def check_market(app):
    while True:
        for symbol in active_coins:
            price = get_price(symbol)
            if price:
                signal = generate_signal(symbol, price)
                await app.bot.send_message(chat_id=CHAT_ID, text=signal, parse_mode="HTML")
        await asyncio.sleep(60)

# === КНОПКИ ===
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("💥 Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("➕ Додати монету", callback_data="add_coin")],
        [InlineKeyboardButton("➖ Видалити монету", callback_data="remove_coin")],
        [InlineKeyboardButton("💰 Ціни зараз", callback_data="show_prices")]
    ])

# === ОБРОБКА КОМАНД ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я трейдинг-бот ✅", reply_markup=main_keyboard())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "привіт" in text:
        await update.message.reply_text("Привіт! Обирай опцію нижче 👇", reply_markup=main_keyboard())

# === КНОПКИ CALLBACK ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_margin
    query = update.callback_query
    await query.answer()

    if query.data == "change_margin":
        user_margin = 200 if user_margin == 100 else 100
        await query.edit_message_text(f"🔄 Маржа змінена на: {user_margin}$", reply_markup=main_keyboard())

    elif query.data == "change_leverage":
        for k in user_leverage:
            user_leverage[k] = 500 if user_leverage[k] == 300 else 300
        await query.edit_message_text("🔄 Плече оновлено.", reply_markup=main_keyboard())

    elif query.data == "add_coin":
        if "BNB" not in active_coins:
            active_coins.append("BNB")
            await query.edit_message_text("✅ Монета BNB додана!", reply_markup=main_keyboard())
        else:
            await query.edit_message_text("⚠️ BNB вже є в списку.", reply_markup=main_keyboard())

    elif query.data == "remove_coin":
        if "BNB" in active_coins:
            active_coins.remove("BNB")
            await query.edit_message_text("❌ BNB видалено.", reply_markup=main_keyboard())
        else:
            await query.edit_message_text("⚠️ BNB немає в списку.", reply_markup=main_keyboard())

    elif query.data == "show_prices":
        prices = []
        for symbol in active_coins:
            price = get_price(symbol)
            if price:
                prices.append(f"{symbol}/USDT: <b>{price}</b>")
        await query.edit_message_text("\n".join(prices), parse_mode="HTML", reply_markup=main_keyboard())

# === СТАРТ БОТА ===
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    job_queue = JobQueue()
    job_queue.set_application(app)
    job_queue.start()

    app.create_task(check_market(app))

    print("✅ Бот запущено")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
