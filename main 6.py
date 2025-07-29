import logging
import asyncio
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext
)

TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

user_data = {
    "leverage": {"SOL": 300, "BTC": 500, "ETH": 500},
    "margin": {"SOL": 100, "BTC": 100, "ETH": 100},
    "active": True,
    "coins": ["SOL", "BTC", "ETH"]
}

reply_keyboard = [
    ["Запитати сигнали", "Зупинити сигнали"],
    ["Змінити плече", "Змінити маржу"],
    ["Додати монету", "Видалити монету"]
]

markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот запущено!", reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Зупинити сигнали":
        user_data["active"] = False
        await update.message.reply_text("Автоматичні сигнали зупинено.")
    elif text == "Запитати сигнали":
        await send_signal(update, context)
    elif text == "Змінити плече":
        await update.message.reply_text("Введіть нове плече у форматі: SOL 300")
    elif text == "Змінити маржу":
        await update.message.reply_text("Введіть нову маржу у $ у форматі: SOL 150")
    elif text == "Додати монету":
        await update.message.reply_text("Напишіть символ монети, яку хочете додати (наприклад: ARB)")
    elif text == "Видалити монету":
        await update.message.reply_text("Напишіть символ монети, яку хочете видалити (наприклад: SOL)")
    elif text.upper().startswith("SOL") or text.upper().startswith("BTC") or text.upper().startswith("ETH"):
        try:
            coin, value = text.upper().split()
            value = int(value)
            if "марж" in update.message.text.lower():
                user_data["margin"][coin] = value
                await update.message.reply_text(f"Нова маржа для {coin}: ${value}")
            else:
                user_data["leverage"][coin] = value
                await update.message.reply_text(f"Нове плече для {coin}: {value}×")
        except:
            await update.message.reply_text("Невірний формат. Приклад: SOL 300")
    else:
        coin = text.upper()
        if coin in user_data["coins"]:
            user_data["coins"].remove(coin)
            await update.message.reply_text(f"Монету {coin} видалено.")
        else:
            user_data["coins"].append(coin)
            await update.message.reply_text(f"Монету {coin} додано.")

async def send_signal(update: Update, context: CallbackContext):
    for coin in user_data["coins"]:
        direction = "LONG"  # Це просто приклад
        entry = 100  # приклад
        sl = 95
        tp = 150
        leverage = user_data["leverage"].get(coin, 100)
        margin = user_data["margin"].get(coin, 100)
        text = f"Сигнал {direction} по {coin}
Вхід: {entry} USDT
SL: {sl} USDT
TP: {tp} USDT
Маржа: {margin}$
Плече: {leverage}×"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()