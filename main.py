import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import asyncio

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

margin = 100
leverage = {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500}
symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]

main_menu = ReplyKeyboardMarkup(
    [["Ціни зараз"], ["Змінити маржу", "Змінити плече"]],
    resize_keyboard=True
)

logging.basicConfig(level=logging.INFO)

# --- Отримання останніх двох свічок
def get_candles(symbol):
    url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=2"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        return data
    except Exception as e:
        return None

# --- Аналіз ринку
def analyze_market(symbol):
    candles = get_candles(symbol)
    if not candles or len(candles) < 2:
        return None

    prev = candles[0]
    last = candles[1]

    open_price = float(last[1])
    close_price = float(last[4])
    volume = float(last[5])
    prev_volume = float(prev[5])

    signal_type = None
    if close_price > open_price and volume > prev_volume:
        signal_type = "LONG"
    elif close_price < open_price and volume > prev_volume:
        signal_type = "SHORT"
    else:
        return None

    entry = close_price
    sl = round(entry * (0.99 if signal_type == "LONG" else 1.01), 4)
    tp = round(entry * (1.05 if signal_type == "LONG" else 0.95), 4)

    return {
        "symbol": symbol,
        "type": signal_type,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "leverage": leverage[symbol],
        "margin": margin
    }

# --- Надсилання сигналу
async def send_signal(context: ContextTypes.DEFAULT_TYPE):
    for symbol in symbols:
        signal = analyze_market(symbol)
        if signal:
            text = (
                f"📈 <b>{signal['symbol']}</b> | <b>{signal['type']}</b> сигнал\n"
                f"💵 Вхід: <code>{signal['entry']}</code>\n"
                f"🛡 SL: <code>{signal['sl']}</code>\n"
                f"🎯 TP: <code>{signal['tp']}</code>\n"
                f"💰 Маржа: ${signal['margin']}\n"
                f"⚙ Плече: {signal['leverage']}×"
            )
            await context.bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

# --- Команди
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вітаю! Бот запущено ✅", reply_markup=main_menu)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin
    text = update.message.text
    if text == "Ціни зараз":
        msg = ""
        for sym in symbols:
            try:
                res = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={sym}", timeout=5).json()
                price = res.get("price", "–")
                msg += f"{sym}: {price}\n"
            except:
                msg += f"{sym}: помилка\n"
        await update.message.reply_text(msg)
    elif text == "Змінити маржу":
        await update.message.reply_text("Введіть нову маржу (наприклад, 150):")
        context.user_data["changing_margin"] = True
    elif text == "Змінити плече":
        await update.message.reply_text("Функція зміни плеча скоро буде оновлена.")
    elif context.user_data.get("changing_margin"):
        try:
            margin = int(text)
            context.user_data["changing_margin"] = False
            await update.message.reply_text(f"Маржу змінено на ${margin}")
        except:
            await update.message.reply_text("Введіть коректне число.")

# --- Запуск
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, message_handler))

    job_queue = app.job_queue
    job_queue.run_repeating(send_signal, interval=60, first=10)

    print("Бот запущено ✅")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
