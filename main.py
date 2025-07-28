import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from keep_alive import keep_alive
import aiohttp
import asyncio

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = "681357425"
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

user_margin = 100
user_leverage = {"SOL": 300, "PEPE": 300, "BTC": 500, "ETH": 500}
tracked_symbols = ["SOL_USDT", "PEPE_USDT", "BTC_USDT", "ETH_USDT"]

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Ціни зараз"], ["Змінити маржу", "Змінити плече"], ["Додати монету"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=reply_markup)

async def get_price(symbol):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                data = await r.json()
                return float(data["price"])
    except Exception:
        return None

def calculate_sl_tp(entry, direction, leverage):
    sl_percent = 0.005  # 0.5%
    tp_percent = 0.04   # 4%
    if direction == "LONG":
        return round(entry * (1 - sl_percent), 4), round(entry * (1 + tp_percent), 4)
    else:
        return round(entry * (1 + sl_percent), 4), round(entry * (1 - tp_percent), 4)

async def check_market(context: ContextTypes.DEFAULT_TYPE):
    for symbol in tracked_symbols:
        base = symbol.split("_")[0]
        price = await get_price(symbol.replace("_", ""))
        if price is None:
            return
        direction = "LONG" if int(price * 1000) % 2 == 0 else "SHORT"
        sl, tp = calculate_sl_tp(price, direction, user_leverage.get(base, 300))
        msg = (
            f"💰 <b>Сигнал {direction} по {base}</b>\n\n"
            f"🔹 Вхід: <code>{price}</code>\n"
            f"🛡️ SL: <code>{sl}</code>\n"
            f"🎯 TP: <code>{tp}</code>\n"
            f"⚙️ Плече: <b>{user_leverage.get(base, 300)}×</b>\n"
            f"💼 Маржа: <b>{user_margin}$</b>\n"
        )
        await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_margin
    text = update.message.text.strip().lower()
    if "ціни" in text:
        await update.message.reply_text("Ціни завантажуються...")
        for symbol in tracked_symbols:
            price = await get_price(symbol.replace("_", ""))
            if price:
                await update.message.reply_text(f"{symbol.replace('_', '/')} → {price}")
    elif "маржу" in text:
        await update.message.reply_text("Введи нову маржу:")
        context.user_data["awaiting_margin"] = True
    elif "плече" in text:
        await update.message.reply_text("Функція зміни плеча у розробці.")
    elif context.user_data.get("awaiting_margin"):
        try:
            new_margin = int(text)
            user_margin = new_margin
            context.user_data["awaiting_margin"] = False
            await update.message.reply_text(f"Маржу змінено на {new_margin}$ ✅")
        except ValueError:
            await update.message.reply_text("Будь ласка, введи число.")
    else:
        await start(update, context)

async def main():
    keep_alive()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    application.job_queue.run_repeating(check_market, interval=30, first=5)
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
