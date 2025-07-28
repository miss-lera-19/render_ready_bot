import logging
import requests
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask
from threading import Thread

# 🔐 Токен і чат
BOT_TOKEN = '8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34'
CHAT_ID = '681357425'

# ⚙️ Початкові параметри
user_settings = {
    "margin": 100,
    "leverage": {
        "SOL": 300,
        "BTC": 500,
        "ETH": 500
    },
    "symbols": ["SOLUSDT", "BTCUSDT", "ETHUSDT"]
}

# 🌐 Отримання ціни та обʼєму з MEXC
def get_price_and_volume(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=20"
        response = requests.get(url, timeout=10)
        data = response.json()
        if isinstance(data, list):
            prices = [float(c[4]) for c in data]
            volumes = [float(c[5]) for c in data]
            return prices, volumes
        else:
            return None, None
    except:
        return None, None

# 📊 Аналіз і сигнал
def analyze_and_create_signal(symbol):
    prices, volumes = get_price_and_volume(symbol)
    if not prices or not volumes:
        return None

    last_price = prices[-1]
    avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
    last_volume = volumes[-1]
    direction = "LONG" if prices[-1] > prices[-2] else "SHORT"
    impulse = abs(prices[-1] - prices[-2]) > 0.001 * prices[-2]

    if last_volume >= avg_volume and impulse:
        leverage = user_settings['leverage'].get(symbol.replace("USDT", ""), 100)
        margin = user_settings['margin']
        entry_price = round(last_price, 4)
        sl = round(entry_price * (0.98 if direction == "LONG" else 1.02), 4)
        tp = round(entry_price * (1.05 if direction == "LONG" else 0.95), 4)

        return (
            f"⚡️ Новий сигнал: {direction}\n"
            f"Монета: {symbol}\n"
            f"Вхід: {entry_price} USDT\n"
            f"Stop Loss: {sl} USDT\n"
            f"Take Profit: {tp} USDT\n"
            f"Маржа: ${margin}\n"
            f"Плече: {leverage}×\n"
            f"⏱ 1-хв інтервал | Обʼєм підтверджено"
        )
    return None

# 🔁 Цикл перевірки ринку
async def check_market(app):
    while True:
        for symbol in user_settings["symbols"]:
            signal = analyze_and_create_signal(symbol)
            if signal:
                await app.bot.send_message(chat_id=CHAT_ID, text=signal)
        await asyncio.sleep(60)

# 📦 Команди
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Змінити маржу", callback_data='change_margin')],
        [InlineKeyboardButton("Змінити плече", callback_data='change_leverage')],
        [InlineKeyboardButton("Ціни зараз", callback_data='get_prices')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 Бот запущено! ✅", reply_markup=reply_markup)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "привіт" in text or "/start" in text:
        await start(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'get_prices':
        prices_text = ""
        for symbol in user_settings["symbols"]:
            prices, _ = get_price_and_volume(symbol)
            if prices:
                prices_text += f"{symbol}: {prices[-1]} USDT\n"
        await query.edit_message_text(f"📊 Актуальні ціни:\n{prices_text}")

    elif query.data == 'change_margin':
        await query.edit_message_text("✏️ Введіть нову маржу в $:")
        context.user_data["awaiting_margin"] = True

    elif query.data == 'change_leverage':
        await query.edit_message_text("✏️ Напишіть у форматі: SOL 200")

# 🧠 Обробка тексту
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if context.user_data.get("awaiting_margin"):
        try:
            margin = int(text)
            user_settings["margin"] = margin
            await update.message.reply_text(f"✅ Нова маржа: ${margin}")
        except:
            await update.message.reply_text("⚠️ Введіть ціле число.")
        context.user_data["awaiting_margin"] = False

    elif len(text.split()) == 2:
        coin, lev = text.split()
        if coin.upper() in user_settings["leverage"]:
            try:
                lev = int(lev)
                user_settings["leverage"][coin.upper()] = lev
                await update.message.reply_text(f"✅ Плече для {coin.upper()} змінено на {lev}×")
            except:
                await update.message.reply_text("⚠️ Введіть ціле число після монети.")

# 🌐 Flask для Render
app_flask = Flask(__name__)
@app_flask.route('/')
def index():
    return "Бот працює ✅"

def run_flask():
    app_flask.run(host='0.0.0.0', port=10000)

# ▶️ Запуск
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    tg_app = ApplicationBuilder().token(BOT_TOKEN).build()

    tg_app.add_handler(CommandHandler('start', start))
    tg_app.add_handler(CallbackQueryHandler(button_handler))
    tg_app.add_handler(MessageHandler(filters.TEXT, message_handler))
    tg_app.add_handler(MessageHandler(filters.TEXT, text_handler))

    Thread(target=run_flask).start()
    tg_app.run_polling()
    asyncio.run(check_market(tg_app))
