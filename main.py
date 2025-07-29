# main.py
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
import os
from keep_alive import keep_alive
import requests
import logging

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = "681357425"
auto_signals_enabled = True
user_margin = 100
user_leverage = {
    'SOL': 300,
    'BTC': 500,
    'ETH': 500
}
tracked_coins = ['SOL', 'BTC', 'ETH']

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Запитати сигнали', 'Зупинити сигнали'],
                ['Змінити плече', 'Змінити маржу'],
                ['Додати монету', 'Видалити монету']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Бот активний. Обери опцію:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signals_enabled
    text = update.message.text
    if text == 'Зупинити сигнали':
        auto_signals_enabled = False
        await update.message.reply_text("Автоматичні сигнали вимкнено ❌")
    elif text == 'Запитати сигнали':
        await send_signals(context)
    else:
        await update.message.reply_text("Команда не розпізнана.")

def get_price(symbol: str) -> float:
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        return float(res.json()['price'])
    except Exception as e:
        logging.warning(f"Помилка отримання ціни для {symbol}: {e}")
        return -1

async def send_signals(context: CallbackContext):
    for coin in tracked_coins:
        price = get_price(coin)
        if price == -1:
            continue
        leverage = user_leverage.get(coin, 100)
        margin = user_margin
        position_size = round(margin * leverage / price, 2)
        sl = round(price * 0.99, 2)
        tp = round(price * 1.03, 2)
        direction = "LONG" if price % 2 == 0 else "SHORT"
        text = (f"🔔 Сигнал {direction} ({coin})
"
                f"Вхід: {price}$
"
                f"Обʼєм: {position_size} {coin} ({margin}$ x {leverage}×)
"
                f"SL: {sl}$
TP: {tp}$")
        await context.bot.send_message(chat_id=CHAT_ID, text=text)

async def auto_signal_loop(app):
    while True:
        if auto_signals_enabled:
            await send_signals(app.bot)
        await asyncio.sleep(60)

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(send_signals, interval=60, first=5)
    app.run_polling()
