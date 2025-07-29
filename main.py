import logging
import os
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

user_settings = {
    "SOL": {"margin": 100, "leverage": 300},
    "BTC": {"margin": 100, "leverage": 500},
    "ETH": {"margin": 100, "leverage": 500}
}

logging.basicConfig(level=logging.INFO)

async def get_price(symbol: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}") as response:
                data = await response.json()
                return float(data["price"])
    except Exception as e:
        logging.error(f"Error fetching price for {symbol}: {e}")
        return None

def generate_signal(symbol: str, price: float, direction: str):
    margin = user_settings[symbol]["margin"]
    leverage = user_settings[symbol]["leverage"]
    sl = round(price * (0.996 if direction == "LONG" else 1.004), 4)
    tp = round(price * (1.05 if direction == "LONG" else 0.95), 4)
    return (
        f"📢 Торговий сигнал ({symbol}USDT)\n"
        f"Напрям: {direction}\n"
        f"Ціна входу: {price}\n"
        f"Stop Loss: {sl}\n"
        f"Take Profit: {tp}\n"
        f"Маржа: ${margin}\n"
        f"Плече: {leverage}×"
    )

async def send_prices(context: ContextTypes.DEFAULT_TYPE):
    sol = await get_price("SOLUSDT")
    btc = await get_price("BTCUSDT")
    eth = await get_price("ETHUSDT")
    if sol and btc and eth:
        text = (
            f"📊 Актуальні ціни:\n"
            f"SOLUSDT: {sol} USDT\n"
            f"BTCUSDT: {btc} USDT\n"
            f"ETHUSDT: {eth} USDT"
        )
        await context.bot.send_message(chat_id=CHAT_ID, text=text)

async def check_market(context: ContextTypes.DEFAULT_TYPE):
    for symbol in ["SOL", "BTC", "ETH"]:
        full_symbol = f"{symbol}USDT"
        price = await get_price(full_symbol)
        if not price:
            continue
        direction = "LONG" if int(datetime.utcnow().second) % 2 == 0 else "SHORT"
        signal = generate_signal(symbol, price, direction)
        await context.bot.send_message(chat_id=CHAT_ID, text=signal)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Ціни зараз", callback_data='prices')],
        [InlineKeyboardButton("Змінити маржу", callback_data='margin')],
        [InlineKeyboardButton("Змінити плече", callback_data='leverage')],
        [InlineKeyboardButton("Додати монету", callback_data='add_coin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Вітаю! Оберіть опцію:", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "prices":
        await send_prices(context)
    elif query.data == "margin":
        await query.edit_message_text("✏️ Введіть нову маржу в $:")
    elif query.data == "leverage":
        await query.edit_message_text("✏️ Напишіть у форматі: SOL 200")

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.job_queue.run_repeating(check_market, interval=60)
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
