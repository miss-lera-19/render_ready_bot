
import asyncio
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from keep_alive import keep_alive

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
margin = 100
leverage = {"SOL": 300, "BTC": 500, "ETH": 500}
active_coins = ["SOL", "BTC", "ETH"]
auto_signals = True

def get_price(symbol: str):
    try:
        url = f'https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT'
        res = requests.get(url, timeout=5).json()
        return float(res['price'])
    except:
        return None

def create_signal(symbol: str):
    price = get_price(symbol)
    if not price:
        return None

    direction = "LONG" if price % 10 > 5 else "SHORT"
    entry = round(price, 2)
    if direction == "LONG":
        tp = round(entry * 1.1, 3)
        sl = round(entry * 0.97, 3)
    else:
        tp = round(entry * 0.9, 3)
        sl = round(entry * 1.02, 3)

    signal_text = (
        f"📉 Сигнал на {direction} по {symbol}USDT\n"
        f"🔷 Вхід: {entry} USDT\n"
        f"🎯 Take Profit: {tp}\n"
        f"🛡 Stop Loss: {sl}\n"
        f"⚙️ Плече: {leverage[symbol]}×\n"
        f"💰 Маржа: ${margin}"
    )
    return signal_text

async def send_signals(app):
    global auto_signals
    while auto_signals:
        for coin in active_coins:
            signal = create_signal(coin)
            if signal:
                await app.bot.send_message(chat_id=CHAT_ID, text=signal)
        await asyncio.sleep(60)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧾 Запитати сигнали", callback_data="ask")],
        [InlineKeyboardButton("🛑 Зупинити сигнали", callback_data="stop")]
    ]
    await update.message.reply_text("Бот активний ✅", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signals
    query = update.callback_query
    await query.answer()

    if query.data == "ask":
        for coin in active_coins:
            signal = create_signal(coin)
            if signal:
                await query.message.reply_text(signal)
    elif query.data == "stop":
        auto_signals = False
        await query.message.reply_text("⛔️ Авто-сигнали зупинено.")

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    asyncio.create_task(send_signals(app))
    app.run_polling()
