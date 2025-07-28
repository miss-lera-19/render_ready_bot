import os
import asyncio
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# 🔐 Константи
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

# 📈 Параметри
user_margin = 100
user_leverage = {
    'SOL': 300,
    'PEPE': 300,
    'BTC': 500,
    'ETH': 500
}
coins = ['SOL', 'PEPE', 'BTC', 'ETH']

logging.basicConfig(level=logging.INFO)

# 📊 Отримання ціни з MEXC API
def get_price(symbol):
    try:
        response = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT")
        data = response.json()
        return float(data['price'])
    except Exception as e:
        logging.error(f"❌ Помилка отримання ціни для {symbol}: {e}")
        return None

# 🤖 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Ціни зараз"], ["Змінити маржу", "Змінити плече"], ["Додати монету"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=reply_markup)

# 📲 Обробка повідомлень
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_margin
    text = update.message.text

    if text == "Ціни зараз":
        await update.message.reply_text("Ціни завантажуються...")
        for coin in coins:
            price = get_price(coin)
            if price:
                await update.message.reply_text(f"{coin}/USDT: ${price}")
            else:
                await update.message.reply_text(f"Не вдалося отримати ціну для {coin}")
    elif text == "Змінити маржу":
        await update.message.reply_text("Введи нову маржу у $:")
        context.user_data["change_margin"] = True
    elif context.user_data.get("change_margin"):
        try:
            user_margin = float(text)
            await update.message.reply_text(f"Маржу оновлено: ${user_margin}")
        except:
            await update.message.reply_text("Невірний формат числа.")
        context.user_data["change_margin"] = False
    elif text == "Змінити плече":
        await update.message.reply_text("Напиши монету і нове плече, напр: SOL 300")
        context.user_data["change_leverage"] = True
    elif context.user_data.get("change_leverage"):
        try:
            parts = text.split()
            coin, lev = parts[0].upper(), int(parts[1])
            if coin in user_leverage:
                user_leverage[coin] = lev
                await update.message.reply_text(f"Плече для {coin} оновлено: {lev}×")
            else:
                await update.message.reply_text("Монету не знайдено.")
        except:
            await update.message.reply_text("Формат: BTC 500")
        context.user_data["change_leverage"] = False
    elif text == "Додати монету":
        await update.message.reply_text("Напиши нову монету (тільки символ, напр: XRP)")
        context.user_data["add_coin"] = True
    elif context.user_data.get("add_coin"):
        new_coin = text.upper()
        if new_coin not in coins:
            coins.append(new_coin)
            user_leverage[new_coin] = 100
            await update.message.reply_text(f"Монету {new_coin} додано!")
        else:
            await update.message.reply_text("Ця монета вже є.")
        context.user_data["add_coin"] = False
    elif text.lower() in ["привіт", "hi", "hello"]:
        await start(update, context)

# 📉 Формування торгових сигналів
async def check_market(context: ContextTypes.DEFAULT_TYPE):
    for coin in coins:
        price = get_price(coin)
        if not price:
            continue

        # Стратегія на основі імпульсу: симуляція сигналу
        signal_type = "LONG" if int(price * 100) % 2 == 0 else "SHORT"
        entry_price = round(price, 4)
        sl = round(entry_price * (0.98 if signal_type == "LONG" else 1.02), 4)
        tp = round(entry_price * (1.05 if signal_type == "LONG" else 0.95), 4)
        lev = user_leverage.get(coin, 100)

        signal = (
            f"📊 {coin}/USDT {signal_type} сигнал\n"
            f"💰 Вхід: {entry_price}\n"
            f"🛡️ SL: {sl}\n"
            f"🎯 TP: {tp}\n"
            f"💵 Маржа: ${user_margin} | Плече: {lev}×"
        )
        await context.bot.send_message(chat_id=CHAT_ID, text=signal)

# 🟢 Запуск бота
if __name__ == "__main__":
    async def main():
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        job = app.job_queue
        job.run_repeating(check_market, interval=30, first=10)  # Що 30 секунд

        print("✅ Бот працює...")
        await app.run_polling()

    asyncio.run(main())
