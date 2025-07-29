import logging
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

user_settings = {
    "symbols": ["SOLUSDT", "BTCUSDT", "ETHUSDT"],
    "leverage": {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500},
    "margin": 100,
    "auto_signals": True
}

logging.basicConfig(level=logging.INFO)

# Отримання ціни з MEXC API
async def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/24hr?symbol={symbol}"
        r = requests.get(url, timeout=5)
        data = r.json()
        return float(data["lastPrice"]), float(data["quoteVolume"]), float(data["highPrice"]), float(data["lowPrice"])
    except:
        return None, None, None, None

# Стратегія генерації сигналу
async def generate_signal(symbol):
    price, volume, high, low = await get_price(symbol)
    if not price:
        return None

    try:
        candles = requests.get(f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=5").json()
        last_close = float(candles[-1][4])
        prev_close = float(candles[-2][4])
        last_volume = float(candles[-1][5])
        avg_volume = sum(float(c[5]) for c in candles[:-1]) / (len(candles) - 1)
    except:
        return None

    if last_close > prev_close and last_volume >= avg_volume:
        trend = "long"
    elif last_close < prev_close and last_volume >= avg_volume:
        trend = "short"
    else:
        return None

    leverage = user_settings["leverage"].get(symbol, 100)
    margin = user_settings["margin"]
    entry = price
    tp = round(price * (1.10 if trend == "long" else 0.90), 4)
    sl = round(price * (0.98 if trend == "long" else 1.02), 4)

    return (
        f"📈 Сигнал на {trend.upper()} по {symbol}:\n"
        f"🔹 Вхід: {entry} USDT\n"
        f"🎯 Take Profit: {tp}\n"
        f"🛑 Stop Loss: {sl}\n"
        f"💥 Плече: {leverage}x\n"
        f"💰 Маржа: ${margin}"
    )

# Надсилання сигналів
async def send_signals(context: ContextTypes.DEFAULT_TYPE):
    for symbol in user_settings["symbols"]:
        signal = await generate_signal(symbol)
        if signal:
            await context.bot.send_message(chat_id=CHAT_ID, text=signal)

# Авто-сигнали
async def auto_check_signals(app):
    while True:
        if user_settings["auto_signals"]:
            await send_signals(ContextTypes.DEFAULT_TYPE(application=app))
        await asyncio.sleep(60)

# Команди Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("Запитати сигнали", callback_data="signal")],
        [InlineKeyboardButton("Зупинити сигнали", callback_data="stop")],
        [InlineKeyboardButton("Змінити плече", callback_data="leverage")],
        [InlineKeyboardButton("Змінити маржу", callback_data="margin")],
        [InlineKeyboardButton("Додати монету", callback_data="add")],
        [InlineKeyboardButton("Видалити монету", callback_data="remove")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("👋 Бот активний. Оберіть дію:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "signal":
        await send_signals(context)
    elif query.data == "stop":
        user_settings["auto_signals"] = False
        await query.edit_message_text("⛔️ Автоматичні сигнали вимкнено.")
    elif query.data == "leverage":
        await query.edit_message_text("Введіть монету та нове плече (наприклад: SOLUSDT 300):")
        context.user_data["awaiting"] = "leverage"
    elif query.data == "margin":
        await query.edit_message_text("Введіть нову маржу (наприклад: 150):")
        context.user_data["awaiting"] = "margin"
    elif query.data == "add":
        await query.edit_message_text("Введіть монету для додавання (наприклад: ETHUSDT):")
        context.user_data["awaiting"] = "add"
    elif query.data == "remove":
        await query.edit_message_text("Введіть монету для видалення (наприклад: BTCUSDT):")
        context.user_data["awaiting"] = "remove"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()
    awaiting = context.user_data.get("awaiting")

    if awaiting == "leverage":
        try:
            symbol, lev = text.split()
            user_settings["leverage"][symbol] = int(lev)
            await update.message.reply_text(f"Плече для {symbol} змінено на {lev}x.")
        except:
            await update.message.reply_text("⚠️ Неправильний формат.")
    elif awaiting == "margin":
        try:
            user_settings["margin"] = float(text)
            await update.message.reply_text(f"Маржа змінена на ${text}")
        except:
            await update.message.reply_text("⚠️ Введіть число.")
    elif awaiting == "add":
        user_settings["symbols"].append(text)
        await update.message.reply_text(f"Додано монету: {text}")
    elif awaiting == "remove":
        try:
            user_settings["symbols"].remove(text)
            await update.message.reply_text(f"Видалено монету: {text}")
        except:
            await update.message.reply_text(f"⚠️ Монета {text} не знайдена.")
    context.user_data["awaiting"] = None

# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_button))

    app.run_polling()
    asyncio.run(auto_check_signals(app))
