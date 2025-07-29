import logging
import os
import asyncio
import time
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 🔐 Твої ключі
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

# ⚙️ Стартові параметри
leverage = {
    'SOL': 300,
    'BTC': 500,
    'ETH': 500,
}
margin = 100  # USD
symbols = ['SOLUSDT', 'BTCUSDT', 'ETHUSDT']

# 🔧 Логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# 📊 Отримати ціну монети
def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return float(response.json()['price'])
    except Exception:
        return None

# 📈 Генерація сигналу (імпульсний LONG або SHORT)
def generate_signal(symbol, price):
    # Проста логіка: імпульс вверх або вниз
    if symbol == 'SOLUSDT' and price < 182:
        return 'LONG'
    elif symbol == 'SOLUSDT' and price > 188:
        return 'SHORT'
    elif symbol == 'BTCUSDT' and price < 116000:
        return 'LONG'
    elif symbol == 'BTCUSDT' and price > 119000:
        return 'SHORT'
    elif symbol == 'ETHUSDT' and price < 3720:
        return 'LONG'
    elif symbol == 'ETHUSDT' and price > 3900:
        return 'SHORT'
    return None

# 📤 Надсилання сигналу
async def send_signal(app, symbol, direction, price):
    entry = price
    lev = leverage[symbol[:3]]
    used_margin = margin
    sl = round(entry * (0.985 if direction == 'LONG' else 1.015), 2)
    tp = round(entry * (1.1 if direction == 'LONG' else 0.9), 2)

    text = (
        f"📢 РЕАЛЬНИЙ СИГНАЛ\n"
        f"Монета: {symbol}\n"
        f"Напрям: {direction}\n"
        f"Ціна входу: {entry} USDT\n"
        f"Кредитне плече: {lev}×\n"
        f"Маржа: {used_margin}$\n"
        f"Stop Loss: {sl} USDT\n"
        f"Take Profit: {tp} USDT"
    )
    await app.bot.send_message(chat_id=CHAT_ID, text=text)

# 🔁 Цикл перевірки
async def check_market(app):
    while True:
        for symbol in symbols:
            price = get_price(symbol)
            if price:
                signal = generate_signal(symbol, price)
                if signal:
                    await send_signal(app, symbol, signal, price)
        await asyncio.sleep(60)  # кожну хвилину

# ✅ /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Змінити маржу', 'Змінити плече'], ['Додати монету', 'Ціни зараз']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🤖 Бот запущено! ✅", reply_markup=reply_markup)

# 🧮 Ціни зараз
async def prices_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📊 Актуальні ціни:\n"
    for symbol in symbols:
        price = get_price(symbol)
        if price:
            msg += f"{symbol}: {price:.2f} USDT\n"
    await update.message.reply_text(msg)

# 🔘 Кнопки
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Ціни зараз":
        await prices_now(update, context)
    elif text == "Змінити маржу":
        await update.message.reply_text("✏️ Введи нову маржу (наприклад, 150):")
    elif text == "Змінити плече":
        await update.message.reply_text("✏️ Введи нове плече (наприклад, SOL 400):")
    elif text == "Додати монету":
        await update.message.reply_text("🔹 Напиши монету у форматі: MONETAPAIR, наприклад: XRPUSDT")
    elif text.upper().endswith("USDT"):
        new_symbol = text.upper()
        if new_symbol not in symbols:
            symbols.append(new_symbol)
            leverage[new_symbol[:3]] = 300
            await update.message.reply_text(f"✅ Монета {new_symbol} додана!")
        else:
            await update.message.reply_text(f"⚠️ Монета {new_symbol} вже є.")
    elif text.isdigit():
        global margin
        margin = int(text)
        await update.message.reply_text(f"✅ Маржа оновлена: {margin}$")
    elif any(token in text for token in ['SOL', 'BTC', 'ETH']):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            coin = parts[0].upper()
            lev = int(parts[1])
            leverage[coin] = lev
            await update.message.reply_text(f"✅ Плече оновлено: {coin} — {lev}×")
    else:
        await update.message.reply_text("❓ Невідома команда. Використай кнопки нижче.")

# 🚀 Запуск
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    asyncio.get_event_loop().create_task(check_market(app))
    app.run_polling()
