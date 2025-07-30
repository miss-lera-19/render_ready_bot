
import requests
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from keep_alive import keep_alive

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = "681357425"

leverage = {"SOL": 300, "BTC": 500, "ETH": 500}
margin = 100
active_coins = ["SOL", "BTC", "ETH"]
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
        f"📈 Сигнал на {direction} по {symbol}USDT\n"
        f"🔹 Вхід: {entry} USDT\n"
        f"🎯 Take Profit: {tp}\n"
        f"🛡 Stop Loss: {sl}\n"
        f"⚙️ Плече: {leverage[symbol]}×\n"
        f"💰 Маржа: ${margin}"
    )
    return signal_text

# ==== ФУНКЦІЇ TELEGRAM ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📥 Запитати сигнали", callback_data="get_signals")],
        [InlineKeyboardButton("⛔ Зупинити сигнали", callback_data="stop_signals")],
        [InlineKeyboardButton("🔍 Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("💵 Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("➕ Додати монету", callback_data="add_coin")],
        [InlineKeyboardButton("➖ Видалити монету", callback_data="remove_coin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Бот активний. Обери дію:", reply_markup=reply_markup)

# Запуск автоаналізу
async def auto_check(app):
    while auto_signals:
        for coin in active_coins:
            signal = create_signal(coin)
            if signal:
                await app.bot.send_message(chat_id=CHAT_ID, text=signal)
        await asyncio.sleep(60)

# ==== ЗАПУСК ====
keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
asyncio.get_event_loop().create_task(auto_check(app))
app.run_polling()
