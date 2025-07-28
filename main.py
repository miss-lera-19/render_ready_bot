import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from keep_alive import keep_alive

# === API ключі ===
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

# === Логування ===
logging.basicConfig(level=logging.INFO)

# === Глобальні змінні ===
user_margin = 100
leverage = {
    "SOL": 300,
    "PEPE": 300,
    "BTC": 500,
    "ETH": 500,
}
coins = ["SOL", "PEPE", "BTC", "ETH"]

# === Отримати ціну з MEXC ===
def get_price(symbol):
    try:
        response = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT", timeout=5)
        return float(response.json()["price"])
    except Exception:
        return None

# === Сигнал LONG/SHORT ===
async def generate_signal(ctx: ContextTypes.DEFAULT_TYPE):
    messages = []
    for coin in coins:
        price = get_price(coin)
        if not price:
            continue

        lev = leverage[coin]
        entry_price = round(price, 5)
        direction = "LONG" if coin in ["SOL", "BTC"] else "SHORT"
        sl = round(entry_price * (0.995 if direction == "LONG" else 1.005), 5)
        tp = round(entry_price * (1.05 if direction == "LONG" else 0.95), 5)

        profit = round(user_margin * lev * abs(tp - entry_price) / entry_price, 2)
        if profit >= 500:
            messages.append(
                f"📢 Сигнал по {coin}/USDT\n"
                f"👉 Напрям: *{direction}*\n"
                f"💰 Вхід: `{entry_price}`\n"
                f"📉 SL: `{sl}`\n"
                f"📈 TP: `{tp}`\n"
                f"💸 Плече: {lev}×\n"
                f"📊 Маржа: ${user_margin}\n"
                f"💵 Потенційний прибуток: *${profit}*"
            )

    for msg in messages:
        await ctx.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")

# === Кнопки ===
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("Додати монету", callback_data="add_coin")],
        [InlineKeyboardButton("Ціни зараз", callback_data="get_prices")]
    ])

# === Обробники ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=get_main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "привіт":
        await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "get_prices":
        await query.edit_message_text("Ціни завантажуються...")
        text = ""
        for coin in coins:
            price = get_price(coin)
            text += f"{coin}/USDT: ${price}\n" if price else f"{coin}/USDT: помилка\n"
        await context.bot.send_message(chat_id=CHAT_ID, text=text)

    elif query.data == "change_margin":
        await context.bot.send_message(chat_id=CHAT_ID, text="Введи нову маржу (наприклад, 200):")
        context.user_data["awaiting_margin"] = True

    elif query.data == "change_leverage":
        await context.bot.send_message(chat_id=CHAT_ID, text="Напиши монету і нове плече, наприклад: SOL 400")
        context.user_data["awaiting_leverage"] = True

    elif query.data == "add_coin":
        await context.bot.send_message(chat_id=CHAT_ID, text="Введи назву монети (наприклад DOGE):")
        context.user_data["awaiting_coin"] = True

async def process_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_margin
    text = update.message.text.upper()

    if context.user_data.get("awaiting_margin"):
        try:
            user_margin = int(text)
            await update.message.reply_text(f"Маржу оновлено: ${user_margin}")
        except:
            await update.message.reply_text("Невірне значення маржі.")
        context.user_data["awaiting_margin"] = False

    elif context.user_data.get("awaiting_leverage"):
        try:
            parts = text.split()
            coin, lev = parts[0], int(parts[1])
            if coin in coins:
                leverage[coin] = lev
                await update.message.reply_text(f"Плече для {coin} оновлено на {lev}×")
            else:
                await update.message.reply_text("Монета не знайдена.")
        except:
            await update.message.reply_text("Невірний формат.")
        context.user_data["awaiting_leverage"] = False

    elif context.user_data.get("awaiting_coin"):
        if text not in coins:
            coins.append(text)
            leverage[text] = 300
            await update.message.reply_text(f"Монету {text} додано.")
        else:
            await update.message.reply_text("Ця монета вже є.")
        context.user_data["awaiting_coin"] = False

# === Запуск бота ===
if __name__ == '__main__':
    keep_alive()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    job_queue = application.job_queue

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), process_reply))

    # Перевірка сигналів кожні 30 секунд
    job_queue.run_repeating(generate_signal, interval=30)

    application.run_polling()
