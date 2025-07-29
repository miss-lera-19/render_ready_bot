import logging
import requests
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime

# === КОНФІГУРАЦІЯ ===
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_URL = "https://api.mexc.com"
CHECK_INTERVAL = 60  # кожну хвилину

# === СТАН КОРИСТУВАЧА ===
leverage = {'SOL': 300, 'BTC': 500, 'ETH': 500}
margin = 100
enabled = True
tracked_symbols = ['SOLUSDT', 'BTCUSDT', 'ETHUSDT']

# === ЛОГУВАННЯ ===
logging.basicConfig(level=logging.INFO)

# === ДОПОМОЖНІ ФУНКЦІЇ ===

def get_price(symbol):
    try:
        url = f"{MEXC_API_URL}/api/v3/klines?symbol={symbol}&interval=1m&limit=3"
        response = requests.get(url)
        data = response.json()
        if isinstance(data, list) and len(data) >= 3:
            last = data[-2]
            current = data[-1]
            return {
                "last_open": float(last[1]),
                "last_close": float(last[4]),
                "last_volume": float(last[5]),
                "current_open": float(current[1]),
                "current_close": float(current[4]),
                "current_volume": float(current[5])
            }
        else:
            return None
    except Exception as e:
        print(f"Помилка при отриманні ціни: {e}")
        return None

def analyze_market(symbol):
    data = get_price(symbol)
    if not data:
        return None

    direction = None
    impulse = abs(data['current_close'] - data['current_open']) > 0.002 * data['current_close']
    growing_volume = data['current_volume'] > data['last_volume']

    if data['last_close'] < data['current_close'] and impulse and growing_volume:
        direction = 'LONG'
    elif data['last_close'] > data['current_close'] and impulse and growing_volume:
        direction = 'SHORT'

    return {
        "symbol": symbol,
        "price": data["current_close"],
        "direction": direction,
        "impulse": impulse,
        "volume_confirmed": growing_volume
    }

def generate_signal(analysis):
    if not analysis or not analysis['direction']:
        return None

    entry = analysis['price']
    direction = analysis['direction']
    coin = analysis['symbol'].replace('USDT', '')
    lev = leverage.get(coin, 300)

    if direction == "LONG":
        sl = round(entry * 0.99, 4)
        tp = round(entry * 1.05, 4)
    else:
        sl = round(entry * 1.01, 4)
        tp = round(entry * 0.95, 4)

    return f"""
📢 Сигнал {direction} ({coin})
Вхід: {entry}
SL: {sl}
TP: {tp}
Маржа: ${margin}
Плече: {lev}×

#ТорговаСтратегія #{coin}
"""

# === ОБРОБНИКИ КОМАНД ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📥 Запитати сигнали", callback_data="signal")],
        [InlineKeyboardButton("🛑 Зупинити сигнали", callback_data="stop")],
        [InlineKeyboardButton("🔁 Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("💰 Змінити маржу", callback_data="change_margin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 Бот запущено. Обери дію:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global enabled, margin

    query = update.callback_query
    await query.answer()

    if query.data == "signal":
        await query.edit_message_text("🔍 Аналіз ринку...")
        for symbol in tracked_symbols:
            analysis = analyze_market(symbol)
            signal = generate_signal(analysis)
            if signal:
                await context.bot.send_message(chat_id=CHAT_ID, text=signal)
            else:
                await context.bot.send_message(chat_id=CHAT_ID, text=f"{symbol}: Немає сигналу ❌")
    elif query.data == "stop":
        enabled = False
        await query.edit_message_text("⛔️ Автоматичні сигнали вимкнено.")
    elif query.data == "change_leverage":
        await query.edit_message_text("⚙️ Щоб змінити плече, напишіть: `плече SOL 400`")
    elif query.data == "change_margin":
        await query.edit_message_text("💼 Щоб змінити маржу, напишіть: `маржа 200`")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global leverage, margin

    msg = update.message.text.upper()
    if msg.startswith("ПЛЕЧЕ"):
        parts = msg.split()
        if len(parts) == 3:
            coin, val = parts[1], parts[2]
            if coin in leverage:
                leverage[coin] = int(val)
                await update.message.reply_text(f"✅ Плече для {coin} оновлено: {val}×")
    elif msg.startswith("МАРЖА"):
        parts = msg.split()
        if len(parts) == 2:
            margin = int(parts[1])
            await update.message.reply_text(f"✅ Нова маржа: ${margin}")
    elif msg.lower() in ["привіт", "старт", "/start"]:
        await start(update, context)

# === АВТОМАТИЧНІ СИГНАЛИ ===

async def auto_signals(app):
    global enabled
    while True:
        if enabled:
            for symbol in tracked_symbols:
                analysis = analyze_market(symbol)
                signal = generate_signal(analysis)
                if signal:
                    await app.bot.send_message(chat_id=CHAT_ID, text=signal)
        await asyncio.sleep(CHECK_INTERVAL)

# === ЗАПУСК ===

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))

    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("change_margin", handle_button))
    app.add_handler(CommandHandler("change_leverage", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("ping", start))
    app.add_handler(CommandHandler("pong", start))
    app.add_handler(CommandHandler("margin", handle_button))
    app.add_handler(CommandHandler("leverage", handle_button))
    app.add_handler(CommandHandler("price", handle_button))

    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", handle_button))
    app.add_handler(CommandHandler("stop", handle_button))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("start", start))

    await app.initialize()
    await app.start()
    await app.bot.send_message(chat_id=CHAT_ID, text="✅ Бот запущено!")
    asyncio.create_task(auto_signals(app))
    await app.updater.start_polling()
    await app.idle()

if __name__ == "__main__":
    asyncio.run(main())
