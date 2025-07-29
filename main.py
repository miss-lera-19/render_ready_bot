import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

# Початкові значення
margin = 100
leverage = {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500}
symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]

# Кнопки
main_menu = ReplyKeyboardMarkup(
    [["Ціни зараз"], ["Змінити маржу", "Змінити плече"], ["Додати монету", "Видалити монету"]],
    resize_keyboard=True
)

# Логування
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот запущено! ✅", reply_markup=main_menu)

async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📊 Актуальні ціни:\n"
    for symbol in symbols:
        try:
            r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}")
            price = float(r.json()["price"])
            text += f"{symbol}: {price} USDT\n"
        except:
            text += f"{symbol}: помилка отримання ціни\n"
    await update.message.reply_text(text)

async def change_margin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи нову маржу у $ (наприклад: 150):")
    context.user_data["awaiting_margin"] = True

async def change_leverage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи монету та нове плече (наприклад: SOLUSDT 400):")
    context.user_data["awaiting_leverage"] = True

async def add_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи монету, яку хочеш додати (наприклад: DOGEUSDT):")
    context.user_data["awaiting_add_symbol"] = True

async def remove_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи монету, яку хочеш видалити (наприклад: BTCUSDT):")
    context.user_data["awaiting_remove_symbol"] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin
    text = update.message.text.strip().upper()

    if context.user_data.get("awaiting_margin"):
        if text.isdigit():
            margin = int(text)
            await update.message.reply_text(f"✅ Маржу змінено на {margin}$")
        else:
            await update.message.reply_text("❌ Невірне значення. Введи число.")
        context.user_data["awaiting_margin"] = False

    elif context.user_data.get("awaiting_leverage"):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            symbol, lev = parts[0], int(parts[1])
            leverage[symbol] = lev
            await update.message.reply_text(f"✅ Плече для {symbol} змінено на {lev}×")
        else:
            await update.message.reply_text("❌ Формат невірний. Приклад: SOLUSDT 400")
        context.user_data["awaiting_leverage"] = False

    elif context.user_data.get("awaiting_add_symbol"):
        if text not in symbols:
            symbols.append(text)
            await update.message.reply_text(f"✅ Монету {text} додано.")
        else:
            await update.message.reply_text("❗ Така монета вже є.")
        context.user_data["awaiting_add_symbol"] = False

    elif context.user_data.get("awaiting_remove_symbol"):
        if text in symbols:
            symbols.remove(text)
            await update.message.reply_text(f"🗑 Монету {text} видалено.")
        else:
            await update.message.reply_text("❌ Такої монети немає в списку.")
        context.user_data["awaiting_remove_symbol"] = False

    elif text == "ЦІНИ ЗАРАЗ":
        await show_prices(update, context)
    elif text == "ЗМІНИТИ МАРЖУ":
        await change_margin(update, context)
    elif text == "ЗМІНИТИ ПЛЕЧЕ":
        await change_leverage(update, context)
    elif text == "ДОДАТИ МОНЕТУ":
        await add_symbol(update, context)
    elif text == "ВИДАЛИТИ МОНЕТУ":
        await remove_symbol(update, context)
    else:
        await update.message.reply_text("❔ Команду не розпізнано. Вибери з меню.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    print("✅ Бот запущено!")
    app.run_polling()
