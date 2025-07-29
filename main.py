import os
import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
)
import aiohttp

# Конфігурація токена і chat_id
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

# Початкові значення
user_margin = {"SOL": 100, "BTC": 100, "ETH": 100}
user_leverage = {"SOL": 300, "BTC": 500, "ETH": 500}
monitored_coins = ["SOL", "BTC", "ETH"]
auto_signals_enabled = True

keyboard = ReplyKeyboardMarkup(
    [
        ["Запитати сигнали", "Зупинити сигнали"],
        ["Змінити маржу", "Змінити плече"],
        ["Додати монету", "Видалити монету"],
        ["Ціни зараз"]
    ],
    resize_keyboard=True
)

logging.basicConfig(level=logging.INFO)

async def get_price(symbol: str):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                data = await response.json()
                return float(data["price"])
    except:
        return None

def calculate_signal(price, margin, leverage, direction):
    entry = round(price, 2)
    tp = round(entry * (1.4 if direction == "LONG" else 0.6), 2)
    sl = round(entry * (0.97 if direction == "LONG" else 1.03), 2)
    profit = round((margin * leverage * abs(tp - entry)) / entry, 2)
    return entry, sl, tp, profit

async def generate_signals(context: ContextTypes.DEFAULT_TYPE):
    global auto_signals_enabled
    if not auto_signals_enabled:
        return

    for coin in monitored_coins:
        symbol = coin + "USDT"
        price = await get_price(symbol)
        if price:
            direction = "LONG" if price % 2 < 1 else "SHORT"
            entry, sl, tp, profit = calculate_signal(price, user_margin[coin], user_leverage[coin], direction)
            text = (
                f"Сигнал {direction} по {coin}\n"
                f"Вхід: {entry} USDT\n"
                f"SL: {sl}\n"
                f"TP: {tp}\n"
                f"Маржа: ${user_margin[coin]}\n"
                f"Плече: {user_leverage[coin]}×\n"
                f"Очікуваний прибуток: ${profit}"
            )
            await context.bot.send_message(chat_id=CHAT_ID, text=text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущено", reply_markup=keyboard)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signals_enabled

    text = update.message.text.upper()

    if text == "ЦІНИ ЗАРАЗ":
        response = ""
        for coin in monitored_coins:
            price = await get_price(coin + "USDT")
            if price:
                response += f"{coin}USDT: {price} USDT\n"
        await update.message.reply_text(response or "Помилка отримання цін.")
    
    elif text == "ЗАПИТАТИ СИГНАЛИ":
        await generate_signals(context)

    elif text == "ЗУПИНИТИ СИГНАЛИ":
        auto_signals_enabled = False
        await update.message.reply_text("Автосигнали зупинено.")

    elif text == "ЗМІНИТИ МАРЖУ":
        await update.message.reply_text("Введіть нову маржу в $:\nНаприклад: SOL 200")

    elif text == "ЗМІНИТИ ПЛЕЧЕ":
        await update.message.reply_text("Введіть нове плече:\nНаприклад: BTC 400")

    elif text == "ДОДАТИ МОНЕТУ":
        await update.message.reply_text("Введіть монету для додавання:\nНаприклад: LTC")

    elif text == "ВИДАЛИТИ МОНЕТУ":
        await update.message.reply_text("Введіть монету для видалення:\nНаприклад: BTC")

    else:
        parts = text.split()
        if len(parts) == 2:
            coin, value = parts[0], parts[1]
            if coin in monitored_coins:
                if update.message.text.lower().startswith("змінити маржу") or value.isdigit():
                    user_margin[coin] = int(value)
                    await update.message.reply_text(f"Маржу для {coin} змінено на ${value}")
                elif update.message.text.lower().startswith("змінити плече"):
                    user_leverage[coin] = int(value)
                    await update.message.reply_text(f"Плече для {coin} змінено на {value}×")
            else:
                if value.isdigit():
                    monitored_coins.append(coin)
                    await update.message.reply_text(f"Монету {coin} додано.")
                elif coin in monitored_coins:
                    monitored_coins.remove(coin)
                    await update.message.reply_text(f"Монету {coin} видалено.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    job_queue = app.job_queue
    job_queue.run_repeating(generate_signals, interval=60, first=5)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
