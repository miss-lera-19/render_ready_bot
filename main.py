
import asyncio
import logging
import time
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_URL = "https://api.mexc.com/api/v3/ticker/price?symbol="
coins = {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500}
margin = 100
auto_signals = True

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущено ✅")

async def get_price(symbol):
    try:
        res = requests.get(MEXC_API_URL + symbol)
        data = res.json()
        return float(data["price"])
    except Exception:
        return None

def analyze_market(prices):
    if len(prices) < 3:
        return None

    change1 = prices[-1] - prices[-2]
    change2 = prices[-2] - prices[-3]

    if change1 > 0 and change2 > 0:
        return "LONG"
    elif change1 < 0 and change2 < 0:
        return "SHORT"
    else:
        return None

async def send_signal(symbol, direction, context):
    price = await get_price(symbol)
    if price is None:
        return

    leverage = coins[symbol]
    entry = price
    sl = round(entry * (0.99 if direction == "LONG" else 1.01), 4)
    tp = round(entry * (1.05 if direction == "LONG" else 0.95), 4)
    signal = (
        f"💼 Сигнал ({symbol}): {direction}
"
        f"🎯 Вхід: {entry}
"
        f"🛡️ SL: {sl}
"
        f"💰 TP: {tp}
"
        f"⚙️ Плече: {leverage}×
"
        f"📊 Маржа: ${margin}"
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=signal)

async def check_market(context: ContextTypes.DEFAULT_TYPE):
    if not auto_signals:
        return

    for symbol in coins:
        prices = []
        for _ in range(3):
            price = await get_price(symbol)
            if price:
                prices.append(price)
            await asyncio.sleep(20)

        signal = analyze_market(prices)
        if signal:
            await send_signal(symbol, signal, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signals

    text = update.message.text.lower()
    if "запитати" in text:
        for symbol in coins:
            price = await get_price(symbol)
            if price:
                await update.message.reply_text(f"{symbol}: {price}")
    elif "зупинити" in text:
        auto_signals = False
        await update.message.reply_text("⛔ Авто-сигнали вимкнено")
    elif "запустити" in text:
        auto_signals = True
        await update.message.reply_text("✅ Авто-сигнали увімкнено")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_market, interval=60, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
