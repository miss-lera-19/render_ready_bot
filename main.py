import asyncio
import logging
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import aiohttp

# --- Змінні ---
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

# --- Початкові параметри ---
user_data = {
    "margin": 100,
    "leverage": {
        "SOLUSDT": 300,
        "BTCUSDT": 500,
        "ETHUSDT": 500
    },
    "symbols": ["SOLUSDT", "BTCUSDT", "ETHUSDT"]
}

# --- Налаштування логів ---
logging.basicConfig(level=logging.INFO)

# --- Кнопки ---
keyboard = [
    ["Змінити маржу", "Змінити плече"],
    ["Додати монету", "Ціни зараз"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Отримання ціни ---
async def get_price(symbol):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                return float(data["price"])
    except Exception:
        return None

# --- Показати ціни ---
async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📊 Актуальні ціни:\n"
    for symbol in user_data["symbols"]:
        price = await get_price(symbol)
        if price:
            text += f"{symbol}: {price:.2f} USDT\n"
        else:
            text += f"{symbol}: помилка отримання ціни\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

# --- Команди ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот запущено! ✅", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    if msg == "Ціни зараз":
        await show_prices(update, context)
    elif msg == "Змінити маржу":
        await update.message.reply_text("Введи нову маржу (у $):")
        context.user_data["awaiting"] = "margin"
    elif msg == "Змінити плече":
        await update.message.reply_text("Введи монету та нове плече, наприклад: SOLUSDT 350")
        context.user_data["awaiting"] = "leverage"
    elif msg == "Додати монету":
        await update.message.reply_text("Введи символ монети для додавання (наприклад: DOGEUSDT):")
        context.user_data["awaiting"] = "add_symbol"
    else:
        await process_user_input(update, context, msg)

# --- Обробка змін від користувача ---
async def process_user_input(update, context, msg):
    waiting = context.user_data.get("awaiting")
    if waiting == "margin":
        try:
            user_data["margin"] = float(msg)
            await update.message.reply_text(f"✅ Маржу змінено на ${msg}")
        except:
            await update.message.reply_text("❌ Помилка. Введи число.")
    elif waiting == "leverage":
        try:
            parts = msg.split()
            symbol = parts[0].upper()
            lev = int(parts[1])
            user_data["leverage"][symbol] = lev
            await update.message.reply_text(f"✅ Плече для {symbol} змінено на {lev}×")
        except:
            await update.message.reply_text("❌ Помилка. Приклад: SOLUSDT 350")
    elif waiting == "add_symbol":
        symbol = msg.upper()
        if symbol not in user_data["symbols"]:
            user_data["symbols"].append(symbol)
            user_data["leverage"][symbol] = 100  # стандартне плече
            await update.message.reply_text(f"✅ Монету {symbol} додано.")
        else:
            await update.message.reply_text(f"{symbol} вже є в списку.")
    context.user_data["awaiting"] = None

# --- Стратегія сигналів ---
async def check_market_and_send_signals(app):
    while True:
        for symbol in user_data["symbols"]:
            price = await get_price(symbol)
            if price:
                direction = "LONG" if int(price) % 2 == 0 else "SHORT"
                margin = user_data["margin"]
                leverage = user_data["leverage"].get(symbol, 100)
                entry = price
                sl = entry * (0.98 if direction == "LONG" else 1.02)
                tp = entry * (1.25 if direction == "LONG" else 0.75)
                text = (
                    f"📈 Сигнал: {direction}\n"
                    f"Монета: {symbol}\n"
                    f"Вхід: {entry:.2f} USDT\n"
                    f"SL: {sl:.2f} USDT\n"
                    f"TP: {tp:.2f} USDT\n"
                    f"Маржа: ${margin}\n"
                    f"Плече: {leverage}×"
                )
                await app.bot.send_message(chat_id=CHAT_ID, text=text)
        await asyncio.sleep(60)

# --- Запуск ---
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    asyncio.create_task(check_market_and_send_signals(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
