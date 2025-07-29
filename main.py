import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = "681357425"
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

user_settings = {
    "leverage": {"SOL": 300, "BTC": 500, "ETH": 500},
    "margin": 100,
    "symbols": ["SOL", "BTC", "ETH"],
    "auto_signals": True
}

keyboard = ReplyKeyboardMarkup(
    keyboard=[["Запитати сигнали", "Зупинити сигнали"],
              ["Змінити плече", "Змінити маржу"],
              ["Додати монету", "Видалити монету"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущено ✅", reply_markup=keyboard)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if text == "зупинити сигнали":
        user_settings["auto_signals"] = False
        await update.message.reply_text("Автосигнали вимкнено ❌")

    elif text == "запитати сигнали":
        await send_signals(context)

    elif text == "змінити плече":
        await update.message.reply_text("Введи монету і нове плече (наприклад: SOL 200)")

    elif text == "змінити маржу":
        await update.message.reply_text("Введи нову маржу у $ (наприклад: 120)")

    elif text == "додати монету":
        await update.message.reply_text("Введи монету, яку хочеш додати (наприклад: ARB)")

    elif text == "видалити монету":
        await update.message.reply_text("Введи монету, яку хочеш видалити (наприклад: ETH)")

    else:
        words = text.upper().split()
        if len(words) == 2 and words[0] in user_settings["symbols"]:
            try:
                user_settings["leverage"][words[0]] = int(words[1])
                await update.message.reply_text(f"Плече для {words[0]} змінено на {words[1]}×")
            except:
                pass
        elif text.isdigit():
            user_settings["margin"] = int(text)
            await update.message.reply_text(f"Маржу змінено на ${text}")
        elif text.upper() in user_settings["symbols"]:
            user_settings["symbols"].remove(text.upper())
            await update.message.reply_text(f"{text.upper()} видалено з моніторингу")
        else:
            symbol = text.upper()
            user_settings["symbols"].append(symbol)
            await update.message.reply_text(f"{symbol} додано до моніторингу")

async def send_signals(context: ContextTypes.DEFAULT_TYPE):
    for symbol in user_settings["symbols"]:
        price = await get_price(symbol)
        if price:
            signal = await generate_signal(symbol, price)
            if signal:
                await context.bot.send_message(chat_id=CHAT_ID, text=signal)

async def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
        r = requests.get(url, timeout=5)
        return float(r.json()["price"])
    except:
        return None

async def generate_signal(symbol, price):
    # Імітація професійного аналізу: поточна ціна, динаміка свічки, тренд
    import random
    trend = random.choice(["long", "short"])
    leverage = user_settings["leverage"].get(symbol, 300)
    margin = user_settings["margin"]
    entry = price
    tp = round(price * (1.10 if trend == "long" else 0.90), 4)
    sl = round(price * (0.98 if trend == "long" else 1.02), 4)

    return (f"📉 Сигнал на {trend.upper()} по {symbol}/USDT\n"
            f"Вхід: {entry} USDT\n"
            f"Take Profit: {tp}\n"
            f"Stop Loss: {sl}\n"
            f"Плече: {leverage}×\n"
            f"Маржа: ${margin}\n")

async def auto_check_signals(app):
    while True:
        if user_settings["auto_signals"]:
            await send_signals(ContextTypes.DEFAULT_TYPE(application=app))
        await asyncio.sleep(60)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.job_queue.run_repeating(lambda ctx: send_signals(ctx) if user_settings["auto_signals"] else None, interval=60)

    loop = asyncio.get_event_loop()
    loop.create_task(auto_check_signals(app))
    app.run_polling()
