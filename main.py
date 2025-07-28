import os
import asyncio
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# 🔐 Константи
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

# 📊 Монети та маржа
moneta_list = ["SOL", "PEPE", "BTC", "ETH"]
marzha = 100
pleche = {
    "SOL": 300,
    "PEPE": 300,
    "BTC": 500,
    "ETH": 500,
}

# 📋 Логування
logging.basicConfig(level=logging.INFO)

# 📉 Отримання ціни з MEXC
def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
        response = requests.get(url)
        data = response.json()
        return float(data["price"])
    except Exception as e:
        print(f"Помилка отримання ціни {symbol}: {e}")
        return None

# 🧠 Генерація сигналу
def generate_signal(symbol, price):
    if not price:
        return None

    entry = price
    direction = "LONG" if int(str(price)[-1]) % 2 == 0 else "SHORT"
    sl = round(entry * (0.995 if direction == "LONG" else 1.005), 5)
    tp = round(entry * (1.05 if direction == "LONG" else 0.95), 5)
    return (
        f"🚀 Сигнал {direction} по {symbol}\n\n"
        f"💰 Вхід: {entry}\n"
        f"🛡️ SL: {sl}\n"
        f"🎯 TP: {tp}\n"
        f"💵 Маржа: ${marzha}\n"
        f"📈 Плече: {pleche[symbol]}×"
    )

# 🔁 Регулярна перевірка
async def check_market(app: ApplicationBuilder):
    while True:
        for coin in moneta_list:
            price = get_price(coin)
            signal = generate_signal(coin, price)
            if signal:
                await app.bot.send_message(chat_id=CHAT_ID, text=signal)
        await asyncio.sleep(30)

# 🧾 Команди
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Ціни зараз"], ["Змінити маржу", "Змінити плече"], ["Додати монету"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=reply_markup)

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📊 Поточні ціни:\n"
    for coin in moneta_list:
        price = get_price(coin)
        msg += f"{coin}: {price if price else 'н/д'}\n"
    await update.message.reply_text(msg)

# ✏️ Обробка повідомлень
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "привіт" in text:
        await start(update, context)
    elif "ціни" in text:
        await prices(update, context)
    else:
        await update.message.reply_text("Команда не розпізнана. Обери дію з меню ⬇️")

# 🚀 Запуск
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ✅ Запускаємо перевірку ринку
    asyncio.create_task(check_market(app))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
