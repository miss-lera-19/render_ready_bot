
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
from keep_alive import keep_alive

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

reply_keyboard = [['Змінити маржу', 'Змінити плече'], ['Додати монету', 'Ціни зараз']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущено! ✅", reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Привіт" or text == "/start":
        await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=markup)
    elif text == "Ціни зараз":
        await update.message.reply_text("Ціни завантажуються...")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

keep_alive()
app.run_polling()
