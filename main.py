
import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from flask import Flask, request

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
WEBHOOK_URL = "https://render-ready-bot.onrender.com"

margin = 100
leverage = {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500}
symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

main_menu = ReplyKeyboardMarkup(
    [["Ціни зараз"], ["Змінити маржу", "Змінити плече"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я бот для торгових сигналів 📈", reply_markup=main_menu)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin
    text = update.message.text

    if text == "Ціни зараз":
        prices = []
        for symbol in symbols:
            try:
                response = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}")
                price = float(response.json().get("price", 0))
                prices.append(f"{symbol}: {price}")
            except:
                prices.append(f"{symbol}: помилка отримання")
        await update.message.reply_text("\n".join(prices))

    elif text == "Змінити маржу":
        margin += 50
        await update.message.reply_text(f"Нова маржа: {margin}$")

    elif text == "Змінити плече":
        for symbol in leverage:
            leverage[symbol] += 100
        await update.message.reply_text(f"Нове плече: {leverage}")

async def signal_strategy():
    messages = []
    for symbol in symbols:
        try:
            resp = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}")
            price = float(resp.json().get("price", 0))
            direction = "LONG" if price % 2 > 1 else "SHORT"
            sl = round(price * 0.99, 2)
            tp = round(price * 1.03, 2)
            msg = f"🔥 Сигнал {direction} по {symbol}\nВхід: {price}\nSL: {sl}\nTP: {tp}\nМаржа: {margin}$\nПлече: {leverage[symbol]}×"
            messages.append(msg)
        except:
            messages.append(f"Помилка отримання ціни для {symbol}")
    return messages

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "ok"

@app.route("/")
def index():
    return "Бот працює ✅"

async def polling_loop():
    while True:
        try:
            messages = await signal_strategy()
            for msg in messages:
                await application.bot.send_message(chat_id=CHAT_ID, text=msg)
        except Exception as e:
            print("Помилка:", e)
        await asyncio.sleep(30)

if __name__ == "__main__":
    import asyncio
    from threading import Thread

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def run():
        await application.bot.delete_webhook()
        await application.bot.set_webhook(WEBHOOK_URL + f"/{BOT_TOKEN}")
        await asyncio.gather(application.initialize(), application.start(), polling_loop())

    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))).start()
    asyncio.run(run())
