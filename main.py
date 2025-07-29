import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

user_settings = {
    "symbols": ["SOLUSDT", "BTCUSDT", "ETHUSDT"],
    "leverage": {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500},
    "margin": 100,
    "auto_signals": True
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Запитати сигнали", callback_data="ask_signals")],
        [InlineKeyboardButton("🛑 Зупинити сигнали", callback_data="stop_signals")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Додати монету", callback_data="add_symbol")],
        [InlineKeyboardButton("Видалити монету", callback_data="remove_symbol")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Виберіть опцію:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "ask_signals":
        await send_signals(context)
    elif data == "stop_signals":
        user_settings["auto_signals"] = False
        await query.edit_message_text("⛔ Автоматичні сигнали зупинено.")
    elif data == "change_leverage":
        await query.edit_message_text("Введіть монету і плече (наприклад: SOLUSDT 300):")
    elif data == "change_margin":
        await query.edit_message_text("Введіть нову маржу в USD (наприклад: 120):")
    elif data == "add_symbol":
        await query.edit_message_text("Введіть монету, яку додати (наприклад: BTCUSDT):")
    elif data == "remove_symbol":
        await query.edit_message_text("Введіть монету, яку видалити (наприклад: ETHUSDT):")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if text.replace(" ", "").isdigit():
        user_settings["margin"] = int(text)
        await update.message.reply_text(f"Маржа змінена на ${text}")
    elif " " in text:
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            symbol, lev = parts
            user_settings["leverage"][symbol.upper()] = int(lev)
            await update.message.reply_text(f"Плече для {symbol.upper()} змінено на {lev}x")
    elif text in user_settings["symbols"]:
        user_settings["symbols"].remove(text)
        await update.message.reply_text(f"{text} видалено зі списку монет.")
    else:
        user_settings["symbols"].append(text)
        await update.message.reply_text(f"{text} додано до списку монет.")

async def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        return float(r.json()["price"])
    except:
        return None

async def generate_signal(symbol, price):
    try:
        url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=2"
        r = requests.get(url, timeout=5)
        data = r.json()
        if len(data) < 2:
            return None
        open1, close1 = float(data[-2][1]), float(data[-2][4])
        open2, close2 = float(data[-1][1]), float(data[-1][4])
        volume2 = float(data[-1][5])
        trend = "long" if close1 < close2 and open2 < close2 else "short"
        if volume2 < sum(float(d[5]) for d in data) / len(data):
            return None
        leverage = user_settings["leverage"].get(symbol, 300)
        margin = user_settings["margin"]
        entry = price
        tp = round(entry * (1.10 if trend == "long" else 0.90), 4)
        sl = round(entry * (0.98 if trend == "long" else 1.02), 4)
        return (
            f"📈 Сигнал на {trend.upper()} по {symbol}
"
            f"🔹 Вхід: {entry} USDT
"
            f"🎯 Take Profit: {tp}
"
            f"🛡 Stop Loss: {sl}
"
            f"⚙ Плече: {leverage}x
"
            f"💰 Маржа: ${margin}
"
        )
    except:
        return None

async def send_signals(context: ContextTypes.DEFAULT_TYPE):
    for symbol in user_settings["symbols"]:
        price = await get_price(symbol)
        if price:
            signal = await generate_signal(symbol, price)
            if signal:
                await context.bot.send_message(chat_id=CHAT_ID, text=signal)

async def auto_check_signals(app):
    while True:
        if user_settings["auto_signals"]:
            await send_signals(app)
        await asyncio.sleep(60)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_button))

    async def run():
        asyncio.create_task(auto_check_signals(app))
        await app.run_polling()

    asyncio.run(run())