import asyncio
import logging
import os
import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from keep_alive import keep_alive

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

user_settings = {
    "margin": 100,
    "leverage": {
        "SOL": 300,
        "BTC": 500,
        "ETH": 500
    }
}

coins = ["SOL", "BTC", "ETH"]

async def get_price(symbol: str) -> float:
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return float(data["price"])
    except Exception:
        return 0.0

async def send_signal(context: ContextTypes.DEFAULT_TYPE):
    for coin in coins:
        price = await get_price(coin)
        if price == 0:
            continue

        direction = "LONG" if int(price) % 2 == 0 else "SHORT"
        entry = round(price, 4)
        sl = round(entry * (0.99 if direction == "LONG" else 1.01), 4)
        tp = round(entry * (1.05 if direction == "LONG" else 0.95), 4)
        leverage = user_settings["leverage"][coin]
        margin = user_settings["margin"]

        message = (
            f"📢 Торговий сигнал ({coin}/USDT)\n"
            f"Напрям: {direction}\n"
            f"Вхід: {entry}\n"
            f"SL: {sl}\n"
            f"TP: {tp}\n"
            f"Маржа: {margin}$\n"
            f"Плече: {leverage}×"
        )
        await context.bot.send_message(chat_id=CHAT_ID, text=message)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Ціни зараз", callback_data="prices")],
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 Бот запущено", reply_markup=reply_markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "prices":
        text = "📊 Актуальні ціни:\n"
        for coin in coins:
            price = await get_price(coin)
            text += f"{coin}/USDT: {price}\n"
        await query.edit_message_text(text=text)

def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    job_queue = app.job_queue
    job_queue.run_repeating(send_signal, interval=60, first=5)

    keep_alive()
    app.run_polling()

if __name__ == "__main__":
    main()
