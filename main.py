import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp
from datetime import datetime

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

coins = {
    "SOL": {"leverage": 300},
    "BTC": {"leverage": 500},
    "ETH": {"leverage": 500}
}
margin = 100

logging.basicConfig(level=logging.INFO)

async def get_price(symbol: str) -> float:
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return float(data["price"])
    except Exception:
        return None

def calculate_trade(price, leverage):
    entry = price
    sl = round(entry * 0.99, 2)
    tp = round(entry * 1.015, 2)
    return entry, sl, tp

async def send_signal(application, symbol, signal_type):
    price = await get_price(symbol)
    if price is None:
        return
    leverage = coins[symbol]["leverage"]
    entry, sl, tp = calculate_trade(price, leverage)
    msg = (
        f"📢 <b>{signal_type} сигнал: {symbol}/USDT</b>
"
        f"Ціна входу: <b>{entry}</b>
"
        f"SL: <b>{sl}</b>
"
        f"TP: <b>{tp}</b>
"
        f"Плече: <b>{leverage}×</b>
"
        f"Маржа: <b>${margin}</b>
"
    )
    await application.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="HTML")

async def analyze(application):
    while True:
        for symbol in coins.keys():
            price = await get_price(symbol)
            if price:
                now = datetime.utcnow().second
                signal_type = "LONG" if now % 2 == 0 else "SHORT"
                await send_signal(application, symbol, signal_type)
        await asyncio.sleep(60)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Ціни зараз", callback_data="prices")],
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Вітаю! Обери дію:", reply_markup=reply_markup)

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "prices":
        msg = ""
        for symbol in coins:
            price = await get_price(symbol)
            if price:
                msg += f"{symbol}/USDT: <b>{price}</b>
"
        await query.edit_message_text(text=msg, parse_mode="HTML")
    elif query.data == "change_margin":
        global margin
        margin = 150 if margin == 100 else 100
        await query.edit_message_text(f"Нова маржа: ${margin}")
    elif query.data == "change_leverage":
        coins["SOL"]["leverage"] = 100 if coins["SOL"]["leverage"] == 300 else 300
        await query.edit_message_text(f"Нове плече для SOL: {coins['SOL']['leverage']}×")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    asyncio.create_task(analyze(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
