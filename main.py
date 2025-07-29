import os
import logging
import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

# Початкові значення
margin = 100
leverage = {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500}
symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]

# Кнопки
main_menu = ReplyKeyboardMarkup(
    [["Ціни зараз"], ["Змінити маржу", "Змінити плече"]],
    resize_keyboard=True
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Отримати ціну з MEXC API
def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=10)
        data = response.json()
        return float(data["price"])
    except:
        return None

# Генерація торгового сигналу
def generate_signal(symbol, price):
    if not price:
        return None

    sl = round(price * 0.995, 4)
    tp = round(price * 1.05, 4)
    direction = "LONG" if price > sl else "SHORT"

    lev = leverage.get(symbol, 100)
    used_margin = margin

    return f"""📢 Торговий сигнал ({symbol})
Напрям: {direction}
Ціна входу: {price}
Stop Loss: {sl}
Take Profit: {tp}
Маржа: ${used_margin}
Плече: {lev}×"""

# Обробка команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вітаю! 👋 Оберіть опцію:", reply_markup=main_menu)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin
    msg = update.message.text

    if msg == "Ціни зараз":
        message = ""
        for symbol in symbols:
            price = get_price(symbol)
            message += f"{symbol}: {price}\n" if price else f"{symbol}: помилка\n"
        await update.message.reply_text(message)

    elif msg == "Змінити маржу":
        await update.message.reply_text("Введіть нову маржу у $:")

    elif msg == "Змінити плече":
        await update.message.reply_text("Функція зміни плеча ще в розробці.")

    elif msg.isdigit():
        margin = int(msg)
        await update.message.reply_text(f"Маржа змінена на ${margin}")

    else:
        await update.message.reply_text("Невідома команда. Спробуйте ще раз.", reply_markup=main_menu)

# Автоматична перевірка ринку
async def market_check(app):
    while True:
        try:
            for symbol in symbols:
                price = get_price(symbol)
                signal = generate_signal(symbol, price)
                if signal:
                    await app.bot.send_message(chat_id=CHAT_ID, text=signal)
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Помилка перевірки ринку: {e}")
            await asyncio.sleep(60)

# Запуск бота
if __name__ == '__main__':
    async def main():
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        asyncio.create_task(market_check(app))

        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await app.updater.idle()

    asyncio.run(main())
