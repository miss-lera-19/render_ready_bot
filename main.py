import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Токен і chat_id
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

# Початкові значення
user_settings = {
    "margin": 100,
    "leverage": {"SOL": 300, "BTC": 500, "ETH": 500},
    "coins": ["SOL", "BTC", "ETH"],
    "auto_signals": True
}

# Кнопки
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["Запитати сигнали", "Зупинити сигнали"],
        ["Змінити плече", "Змінити маржу"],
        ["Додати монету", "Видалити монету"]
    ], resize_keyboard=True)

# Команда старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Обери дію:", reply_markup=main_keyboard())
    context.chat_data["awaiting"] = None

# Обробка повідомлень
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    awaiting = context.chat_data.get("awaiting")

    if awaiting == "change_margin":
        try:
            user_settings["margin"] = int(msg)
            await update.message.reply_text(f"Маржа змінена на {msg}$")
        except:
            await update.message.reply_text("Введи число.")
        context.chat_data["awaiting"] = None
        return

    if awaiting == "choose_leverage_coin":
        context.chat_data["coin_to_change"] = msg.upper()
        context.chat_data["awaiting"] = "set_new_leverage"
        await update.message.reply_text("Введи нове плече:")
        return

    if awaiting == "set_new_leverage":
        coin = context.chat_data.get("coin_to_change", "SOL")
        try:
            user_settings["leverage"][coin] = int(msg)
            await update.message.reply_text(f"Плече для {coin} змінено на {msg}×")
        except:
            await update.message.reply_text("Помилка. Введи число.")
        context.chat_data["awaiting"] = None
        return

    if awaiting == "add_coin":
        coin = msg.upper()
        if coin not in user_settings["coins"]:
            user_settings["coins"].append(coin)
            await update.message.reply_text(f"Монету {coin} додано.")
        else:
            await update.message.reply_text("Монета вже є.")
        context.chat_data["awaiting"] = None
        return

    if awaiting == "remove_coin":
        coin = msg.upper()
        if coin in user_settings["coins"]:
            user_settings["coins"].remove(coin)
            await update.message.reply_text(f"Монету {coin} видалено.")
        else:
            await update.message.reply_text("Такої монети нема.")
        context.chat_data["awaiting"] = None
        return

    # Дії по кнопках
    if msg == "Запитати сигнали":
        await update.message.reply_text("📈 Сигнал: LONG по SOL\nВхід: $182.00\nSL: $180.50\nTP: $187.00\nПлече: 300×\nМаржа: $100")
    elif msg == "Зупинити сигнали":
        user_settings["auto_signals"] = False
        await update.message.reply_text("⛔️ Автосигнали зупинено.")
    elif msg == "Змінити плече":
        context.chat_data["awaiting"] = "choose_leverage_coin"
        await update.message.reply_text("Введи монету (наприклад: SOL):")
    elif msg == "Змінити маржу":
        context.chat_data["awaiting"] = "change_margin"
        await update.message.reply_text("Введи нову маржу ($):")
    elif msg == "Додати монету":
        context.chat_data["awaiting"] = "add_coin"
        await update.message.reply_text("Введи символ монети для додавання:")
    elif msg == "Видалити монету":
        context.chat_data["awaiting"] = "remove_coin"
        await update.message.reply_text("Введи символ монети для видалення:")
    else:
        await update.message.reply_text("Не розпізнано. Обери дію з меню.")

# Запуск бота
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущено ✅")
    app.run_polling()
