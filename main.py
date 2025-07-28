import asyncio
import logging
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import requests
from keep_alive import keep_alive

# Константи
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

coins = {
    "SOLUSDT": {"leverage": 300},
    "BTCUSDT": {"leverage": 500},
    "ETHUSDT": {"leverage": 500}
}

user_margin = 100

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("Додати монету", callback_data="add_coin")],
        [InlineKeyboardButton("Видалити монету", callback_data="remove_coin")],
        [InlineKeyboardButton("Ціни зараз", callback_data="prices_now")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 Бот запущено! ✅", reply_markup=reply_markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_margin
    query = update.callback_query
    await query.answer()
    if query.data == "change_margin":
        await query.edit_message_text("Введи нову маржу в $:")
        context.user_data["awaiting_margin"] = True
    elif query.data == "change_leverage":
        await query.edit_message_text("Введи монету та нове плече (наприклад: SOLUSDT 300):")
        context.user_data["awaiting_leverage"] = True
    elif query.data == "add_coin":
        await query.edit_message_text("Введи монету для додавання (наприклад: XRPUSDT):")
        context.user_data["awaiting_add_coin"] = True
    elif query.data == "remove_coin":
        await query.edit_message_text("Введи монету для видалення (наприклад: BTCUSDT):")
        context.user_data["awaiting_remove_coin"] = True
    elif query.data == "prices_now":
        await send_prices(context.bot)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_margin
    msg = update.message.text.upper()
    if context.user_data.get("awaiting_margin"):
        try:
            user_margin = float(msg)
            await update.message.reply_text(f"Маржу змінено на ${user_margin}")
        except:
            await update.message.reply_text("Помилка. Введи число.")
        context.user_data["awaiting_margin"] = False
    elif context.user_data.get("awaiting_leverage"):
        parts = msg.split()
        if len(parts) == 2 and parts[0] in coins:
            try:
                coins[parts[0]]["leverage"] = int(parts[1])
                await update.message.reply_text(f"Плече для {parts[0]} змінено на {parts[1]}×")
            except:
                await update.message.reply_text("Помилка. Формат: SOLUSDT 300")
        else:
            await update.message.reply_text("Монета не знайдена або неправильний формат.")
        context.user_data["awaiting_leverage"] = False
    elif context.user_data.get("awaiting_add_coin"):
        coins[msg] = {"leverage": 100}
        await update.message.reply_text(f"Монету {msg} додано.")
        context.user_data["awaiting_add_coin"] = False
    elif context.user_data.get("awaiting_remove_coin"):
        if msg in coins:
            del coins[msg]
            await update.message.reply_text(f"Монету {msg} видалено.")
        else:
            await update.message.reply_text("Монета не знайдена.")
        context.user_data["awaiting_remove_coin"] = False

async def send_prices(bot):
    text = "📊 Актуальні ціни:
"
    for symbol in coins:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
        try:
            price = float(requests.get(url).json()["price"])
            text += f"{symbol}: {price} USDT
"
        except:
            text += f"{symbol}: ❌
"
    await bot.send_message(chat_id=CHAT_ID, text=text)

async def strategy_loop(app):
    while True:
        for symbol in coins:
            try:
                url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=2"
                response = requests.get(url).json()
                last = response[-1]
                prev = response[-2]
                last_close = float(last[4])
                prev_close = float(prev[4])
                volume = float(last[5])

                if last_close > prev_close and volume > 0:
                    entry = last_close
                    sl = round(entry * 0.995, 2)
                    tp = round(entry * 1.02, 2)
                    leverage = coins[symbol]["leverage"]
                    text = (
                        f"🚀 LONG сигнал по {symbol}
"
                        f"Вхід: {entry}
"
                        f"SL: {sl}
"
                        f"TP: {tp}
"
                        f"Маржа: {user_margin}$
"
                        f"Плече: {leverage}×"
                    )
                    await app.bot.send_message(chat_id=CHAT_ID, text=text)
                elif last_close < prev_close and volume > 0:
                    entry = last_close
                    sl = round(entry * 1.005, 2)
                    tp = round(entry * 0.98, 2)
                    leverage = coins[symbol]["leverage"]
                    text = (
                        f"📉 SHORT сигнал по {symbol}
"
                        f"Вхід: {entry}
"
                        f"SL: {sl}
"
                        f"TP: {tp}
"
                        f"Маржа: {user_margin}$
"
                        f"Плече: {leverage}×"
                    )
                    await app.bot.send_message(chat_id=CHAT_ID, text=text)
            except:
                continue
        await asyncio.sleep(60)

def main():
    keep_alive()
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_once(lambda ctx: asyncio.create_task(strategy_loop(app)), 1)
    app.run_polling()

if __name__ == "__main__":
    main()
