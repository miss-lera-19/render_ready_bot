import asyncio
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackContext

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

user_settings = {
    "symbols": ["SOLUSDT", "BTCUSDT", "ETHUSDT"],
    "leverage": {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500},
    "margin": 100,
    "auto_signals": True,
}

keyboard = [
    ["Запитати сигнали", "Зупинити сигнали"],
    ["Змінити плече", "Змінити маржу"],
    ["Додати монету", "Видалити монету"]
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот активний. Сигнали надсилаються автоматично.", reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Запитати сигнали":
        await send_signals(context)
    elif text == "Зупинити сигнали":
        user_settings["auto_signals"] = False
        await update.message.reply_text("⛔️ Автоматичні сигнали зупинено.")
    elif text == "Змінити плече":
        await update.message.reply_text("Введіть монету та нове плече, напр.: SOLUSDT 300")
    elif text == "Змінити маржу":
        await update.message.reply_text("Введіть нову маржу, напр.: 150")
    elif text == "Додати монету":
        await update.message.reply_text("Введіть монету для додавання, напр.: XRPUSDT")
    elif text == "Видалити монету":
        await update.message.reply_text("Введіть монету для видалення, напр.: BTCUSDT")
    else:
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            symbol = parts[0].upper()
            if symbol in user_settings["symbols"]:
                user_settings["leverage"][symbol] = int(parts[1])
                await update.message.reply_text(f"Плече для {symbol} оновлено до {parts[1]}×")
            else:
                user_settings["symbols"].append(symbol)
                user_settings["leverage"][symbol] = int(parts[1])
                await update.message.reply_text(f"Додано монету {symbol} з плечем {parts[1]}×")
        elif len(parts) == 1 and parts[0].isdigit():
            user_settings["margin"] = int(parts[0])
            await update.message.reply_text(f"Маржа оновлена до ${parts[0]}")
        elif len(parts) == 1:
            symbol = parts[0].upper()
            if symbol in user_settings["symbols"]:
                user_settings["symbols"].remove(symbol)
                await update.message.reply_text(f"Монета {symbol} видалена.")
            else:
                user_settings["symbols"].append(symbol)
                await update.message.reply_text(f"Монета {symbol} додана.")
        else:
            await update.message.reply_text("⚠️ Невірний формат.")

async def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        return float(r.json()["price"])
    except:
        return None

def analyze_market(symbol, price):
    candles = requests.get(f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=3").json()
    if len(candles) < 3:
        return None

    last = candles[-2]
    open_price = float(last[1])
    close_price = float(last[4])
    volume = float(last[5])
    avg_volume = sum(float(c[5]) for c in candles) / len(candles)

    trend = "long" if close_price > open_price and volume >= avg_volume else "short" if close_price < open_price and volume >= avg_volume else None
    return trend

async def generate_signal(symbol, price):
    trend = analyze_market(symbol, price)
    if not trend:
        return None

    leverage = user_settings["leverage"].get(symbol, 100)
    margin = user_settings["margin"]
    entry = price
    tp = round(price * (1.10 if trend == "long" else 0.90), 4)
    sl = round(price * (0.98 if trend == "long" else 1.02), 4)

    return (
        f"📈 Сигнал на {trend.upper()} по {symbol}\n"
        f"🔹 Вхід: {entry} USDT\n"
        f"🎯 Take Profit: {tp}\n"
        f"🛡 Stop Loss: {sl}\n"
        f"⚙️ Плече: {leverage}×\n"
        f"💰 Маржа: ${margin}"
    )

async def send_signals(context: ContextTypes.DEFAULT_TYPE):
    for symbol in user_settings["symbols"]:
        price = await get_price(symbol)
        if price:
            signal = await generate_signal(symbol, price)
            if signal:
                await context.bot.send_message(chat_id=CHAT_ID, text=signal)

async def auto_check(app):
    while True:
        if user_settings["auto_signals"]:
            await send_signals(app.bot)
        await asyncio.sleep(60)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    loop = asyncio.get_event_loop()
    loop.create_task(auto_check(app))
    app.run_polling()
