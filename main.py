
import asyncio
import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import aiohttp
from keep_alive import keep_alive

TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = "681357425"

user_margin = 100
user_leverage = {
    "SOL": 300,
    "PEPE": 300,
    "BTC": 500,
    "ETH": 500
}
watchlist = ["SOL_USDT", "PEPE_USDT", "BTC_USDT", "ETH_USDT"]

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Ціни зараз", callback_data="prices")],
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("Додати монету", callback_data="add_coin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "prices":
        await query.edit_message_text("Ціни завантажуються...")
        prices = await get_prices()
        msg = "
".join([f"{symbol}: {price} USDT" for symbol, price in prices.items()])
        await context.bot.send_message(chat_id=CHAT_ID, text=msg)

async def get_prices():
    url = "https://api.mexc.com/api/v3/ticker/price"
    result = {}
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            for item in data:
                symbol = item.get("symbol")
                if symbol in [s.replace("_", "") for s in watchlist]:
                    result[symbol] = float(item["price"])
    return result

def detect_signal(symbol, price):
    # Умовна стратегія "мільйонера"
    if symbol == "SOL_USDT" and price < 180:
        return "LONG"
    if symbol == "BTC_USDT" and price > 62000:
        return "SHORT"
    return None

async def market_check(context: ContextTypes.DEFAULT_TYPE):
    prices = await get_prices()
    for full_symbol, price in prices.items():
        symbol = full_symbol.replace("USDT", "")
        signal = detect_signal(full_symbol, price)
        if signal:
            margin = user_margin
            leverage = user_leverage.get(symbol, 300)
            sl = round(price * (0.99 if signal == "LONG" else 1.01), 3)
            tp = round(price * (1.05 if signal == "LONG" else 0.95), 3)
            msg = f"📈 Сигнал: {signal} по {symbol}
"                   f"Ціна входу: {price} USDT
"                   f"SL: {sl}
TP: {tp}
"                   f"Маржа: ${margin}
Плече: {leverage}×"
            await context.bot.send_message(chat_id=CHAT_ID, text=msg)

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    app.add_handler(CallbackQueryHandler(button))
    app.job_queue.run_repeating(market_check, interval=30, first=10)
    app.run_polling()
