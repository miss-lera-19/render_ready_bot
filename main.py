import logging
import asyncio
import os
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

coins = {
    "SOLUSDT": {"leverage": 300},
    "BTCUSDT": {"leverage": 500},
    "ETHUSDT": {"leverage": 500}
}
margin = 100

reply_keyboard = [
    ["Змінити маржу", "Змінити плече"],
    ["Додати монету", "Ціни зараз"]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот запущено! ✅", reply_markup=markup)

async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📊 Актуальні ціни:\n"
    for symbol in coins:
        try:
            response = requests.get(
                f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
            )
            price = float(response.json()["price"])
            msg += f"{symbol}: {price} USDT\n"
        except Exception:
            msg += f"{symbol}: ❌ Помилка отримання\n"
    await update.message.reply_text(msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin

    text = update.message.text.strip()

    if text == "Ціни зараз":
        await show_prices(update, context)
    elif text == "Змінити маржу":
        await update.message.reply_text("Введи нову маржу $:")
        context.user_data["awaiting_margin"] = True
    elif text == "Змінити плече":
        await update.message.reply_text("Напиши монету і плече (наприклад: SOLUSDT 200):")
        context.user_data["awaiting_leverage"] = True
    elif text == "Додати монету":
        await update.message.reply_text("Введи назву монети (наприклад: XRPUSDT):")
        context.user_data["awaiting_new_coin"] = True
    elif context.user_data.get("awaiting_margin"):
        try:
            margin = int(text)
            await update.message.reply_text(f"Нова маржа встановлена: ${margin}")
        except:
            await update.message.reply_text("Помилка! Введи число.")
        context.user_data["awaiting_margin"] = False
    elif context.user_data.get("awaiting_leverage"):
        try:
            parts = text.upper().split()
            if len(parts) == 2 and parts[0] in coins:
                coins[parts[0]]["leverage"] = int(parts[1])
                await update.message.reply_text(f"Плече для {parts[0]} змінено на {parts[1]}×")
            else:
                await update.message.reply_text("Неправильний формат або монета не знайдена.")
        except:
            await update.message.reply_text("Помилка! Введи, наприклад: SOLUSDT 200")
        context.user_data["awaiting_leverage"] = False
    elif context.user_data.get("awaiting_new_coin"):
        symbol = text.upper()
        try:
            r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}")
            if "price" in r.json():
                coins[symbol] = {"leverage": 100}
                await update.message.reply_text(f"Монета {symbol} додана!")
            else:
                await update.message.reply_text("Монета не знайдена.")
        except:
            await update.message.reply_text("Помилка при додаванні монети.")
        context.user_data["awaiting_new_coin"] = False
    else:
        await update.message.reply_text("Вибери дію з меню 👇", reply_markup=markup)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Бот працює...")
    app.run_polling()

if __name__ == "__main__":
    main()
