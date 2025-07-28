import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import os

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Ціни зараз", "Змінити маржу"], ["Змінити плече", "Додати монету"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🤖 Бот запущено. Оберіть дію:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Ціни зараз":
        await update.message.reply_text("SOL: $182.31\nBTC: $58200\nETH: $3100")
    elif text == "Змінити маржу":
        await update.message.reply_text("Введіть нову маржу (наприклад 150):")
    elif text == "Змінити плече":
        await update.message.reply_text("Введіть нове плече (наприклад 500):")
    elif text == "Додати монету":
        await update.message.reply_text("Введіть назву монети, яку хочете додати:")
    else:
        await update.message.reply_text("Команду не розпізнано.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущено ✅")
    app.run_polling()