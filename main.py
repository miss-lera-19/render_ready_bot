import requests
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
from keep_alive import keep_alive

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

leverage = {"SOL": 300, "BTC": 500, "ETH": 500}
active_coins = ["SOL", "BTC", "ETH"]
margin = 100
auto_signals = True

# ==== СТРАТЕГІЯ ====
def get_price(symbol: str):
    try:
        url = f'https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT'
        res = requests.get(url, timeout=5).json()
        return float(res['price'])
    except Exception:
        return None

def create_signal(symbol: str):
    price = get_price(symbol)
    if not price:
        return None

    direction = "LONG" if price % 2 > 1 else "SHORT"
    entry = round(price, 2)
    if direction == "LONG":
        tp = round(entry * 1.1, 3)
        sl = round(entry * 0.97, 3)
    else:
        tp = round(entry * 0.9, 3)
        sl = round(entry * 1.02, 3)

    signal_text = (
        f"📉 Сигнал на {direction} по {symbol}USDT
"
        f"🔷 Вхід: {entry} USDT
"
        f"🎯 Take Profit: {tp}
"
        f"🛡 Stop Loss: {sl}
"
        f"⚙️ Плече: {leverage[symbol]}×
"
        f"💰 Маржа: ${margin}"
    )
    return signal_text

# ==== TELEGRAM ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📩 Запитати сигнали", callback_data="get_signals")],
        [InlineKeyboardButton("🛑 Зупинити сигнали", callback_data="stop_signals")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Бот активний. Обери дію:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    global auto_signals

    if query.data == "get_signals":
        for symbol in active_coins:
            signal = create_signal(symbol)
            if signal:
                await query.message.reply_text(signal)
    elif query.data == "stop_signals":
        auto_signals = False
        await query.message.reply_text("Автоматичні сигнали зупинено.")

async def auto_signal_loop(app):
    global auto_signals
    while True:
        if auto_signals:
            for symbol in active_coins:
                signal = create_signal(symbol)
                if signal:
                    await app.bot.send_message(chat_id=CHAT_ID, text=signal)
        await asyncio.sleep(60)

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.create_task(auto_signal_loop(app))
    app.run_polling()