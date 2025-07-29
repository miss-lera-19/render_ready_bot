import asyncio
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
import requests
from keep_alive import keep_alive

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

coins = {
    "SOL": {"symbol": "SOL_USDT", "margin": 100, "leverage": 300},
    "BTC": {"symbol": "BTC_USDT", "margin": 100, "leverage": 500},
    "ETH": {"symbol": "ETH_USDT", "margin": 100, "leverage": 500}
}

auto_signals_enabled = True

button_layout = [
    ["Запитати сигнали", "Зупинити сигнали"],
    ["Змінити маржу", "Змінити плече"],
    ["Додати монету", "Видалити монету"],
    ["Ціни зараз"]
]

def get_price(symbol):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        return float(data["price"])
    except:
        return None

def generate_signal(coin, price):
    direction = "LONG" if price % 2 else "SHORT"
    margin = coins[coin]["margin"]
    leverage = coins[coin]["leverage"]
    entry = round(price, 2)
    sl = round(entry * (0.985 if direction == "LONG" else 1.015), 2)
    tp = round(entry * (1.15 if direction == "LONG" else 0.85), 2)
    return (
        f"📢 Сигнал {direction} по {coin}
"
        f"💰 Вхід: {entry} USDT
"
        f"🛡️ SL: {sl} | 🎯 TP: {tp}
"
        f"💵 Маржа: ${margin} | ⚙️ Плече: {leverage}×"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот запущено! ✅", 
        reply_markup=ReplyKeyboardMarkup(button_layout, resize_keyboard=True)
    )

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📊 Актуальні ціни:
"
    for coin, data in coins.items():
        price = get_price(data["symbol"])
        text += f"{coin}USDT: {price} USDT
" if price else f"{coin}USDT: помилка
"
    await update.message.reply_text(text)

async def ask_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for coin, data in coins.items():
        price = get_price(data["symbol"])
        if price:
            signal = generate_signal(coin, price)
            await context.bot.send_message(chat_id=CHAT_ID, text=signal)

async def stop_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signals_enabled
    auto_signals_enabled = False
    await update.message.reply_text("🚫 Автоматичні сигнали вимкнено.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signals_enabled
    msg = update.message.text.upper()

    if msg.startswith("SOL") or msg.startswith("BTC") or msg.startswith("ETH"):
        try:
            coin, value = msg.split()
            if coin in coins:
                if "МАРЖ" in update.message.reply_to_message.text.upper():
                    coins[coin]["margin"] = float(value)
                    await update.message.reply_text(f"✅ Маржу {coin} оновлено: ${value}")
                elif "ПЛЕЧ" in update.message.reply_to_message.text.upper():
                    coins[coin]["leverage"] = int(value)
                    await update.message.reply_text(f"✅ Плече {coin} оновлено: {value}×")
        except:
            await update.message.reply_text("⚠️ Формат: SOL 100")

    elif msg == "ЗМІНИТИ МАРЖУ":
        await update.message.reply_text("✏️ Введіть нову маржу в $:", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
    elif msg == "ЗМІНИТИ ПЛЕЧЕ":
        await update.message.reply_text("✏️ Введіть нове плече:", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))
    elif msg == "ДОДАТИ МОНЕТУ":
        await update.message.reply_text("✏️ Напишіть у форматі: XYZ_USDT 100 50")
    elif msg == "ВИДАЛИТИ МОНЕТУ":
        await update.message.reply_text("✏️ Напишіть символ монети для видалення (наприклад, SOL)")
    elif "_USDT" in msg and len(msg.split()) == 3:
        try:
            symbol, margin, leverage = msg.split()
            short = symbol.split("_")[0]
            coins[short] = {"symbol": symbol, "margin": float(margin), "leverage": int(leverage)}
            await update.message.reply_text(f"✅ Монету {short} додано.")
        except:
            await update.message.reply_text("⚠️ Формат: XYZ_USDT 100 50")
    elif msg in coins:
        del coins[msg]
        await update.message.reply_text(f"🗑️ Монету {msg} видалено.")

async def auto_signal_loop(app):
    global auto_signals_enabled
    while True:
        if auto_signals_enabled:
            for coin, data in coins.items():
                price = get_price(data["symbol"])
                if price:
                    signal = generate_signal(coin, price)
                    await app.bot.send_message(chat_id=CHAT_ID, text=signal)
        await asyncio.sleep(60)

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Regex("Ціни зараз"), prices))
    app.add_handler(MessageHandler(filters.Regex("Запитати сигнали"), ask_signal))
    app.add_handler(MessageHandler(filters.Regex("Зупинити сигнали"), stop_signal))

    app.job_queue.run_once(lambda ctx: auto_signal_loop(app), 1)

    app.run_polling()