import asyncio
import logging
import os
import time
import aiohttp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- КОНСТАНТИ ---
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

coins = ["SOL", "PEPE", "BTC", "ETH"]
leverage = {"SOL": 300, "PEPE": 300, "BTC": 500, "ETH": 500}
margin = 100  # Стартова маржа в USDT

# --- ЛОГІ ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- Отримання поточної ціни ---
async def get_price(symbol: str) -> float:
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                data = await resp.json()
                return float(data["price"])
    except Exception:
        return None

# --- Генерація сигналу ---
async def generate_signal(symbol: str, price: float) -> str:
    lev = leverage[symbol]
    entry = round(price, 5 if symbol == "PEPE" else 2)
    tp = round(entry * 1.02, 5 if symbol == "PEPE" else 2)
    sl = round(entry * 0.985, 5 if symbol == "PEPE" else 2)
    direction = "LONG" if symbol in ["SOL", "PEPE"] else "SHORT"

    return (
        f"📡 Сигнал ({symbol}/USDT)\n"
        f"➡️ Напрям: *{direction}*\n"
        f"💰 Вхід: `{entry}`\n"
        f"🎯 TP: `{tp}`\n"
        f"🛡 SL: `{sl}`\n"
        f"💵 Маржа: `${margin}`\n"
        f"💥 Плече: `{lev}×`\n"
        f"#trade #signal #crypto"
    )

# --- Перевірка ринку ---
async def check_market(application):
    for coin in coins:
        price = await get_price(coin)
        if price:
            signal = await generate_signal(coin, price)
            await application.bot.send_message(chat_id=CHAT_ID, text=signal, parse_mode="Markdown")
        else:
            await application.bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Не вдалося отримати ціну {coin}")

# --- Команди ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Ціни зараз"], ["Змінити маржу", "Змінити плече", "Додати монету"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👋 Привіт! Бот активний.", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin
    text = update.message.text

    if text == "Ціни зараз":
        msg = ""
        for coin in coins:
            price = await get_price(coin)
            if price:
                msg += f"{coin}/USDT: {price}\n"
            else:
                msg += f"{coin}/USDT: помилка\n"
        await update.message.reply_text(msg)

    elif text == "Змінити маржу":
        await update.message.reply_text("Введи нову маржу у $ (наприклад: 150):")
        context.user_data["expecting_margin"] = True

    elif context.user_data.get("expecting_margin"):
        try:
            new_margin = int(text)
            margin = new_margin
            await update.message.reply_text(f"✅ Нова маржа: ${margin}")
        except ValueError:
            await update.message.reply_text("❌ Невірний формат. Введи число.")
        context.user_data["expecting_margin"] = False

    elif text == "Змінити плече":
        await update.message.reply_text("Введи монету і нове плече через пробіл (наприклад: BTC 400):")
        context.user_data["expecting_leverage"] = True

    elif context.user_data.get("expecting_leverage"):
        parts = text.split()
        if len(parts) == 2 and parts[0].upper() in coins and parts[1].isdigit():
            coin = parts[0].upper()
            leverage[coin] = int(parts[1])
            await update.message.reply_text(f"✅ Нове плече для {coin}: {leverage[coin]}×")
        else:
            await update.message.reply_text("❌ Формат: COIN 300")
        context.user_data["expecting_leverage"] = False

    elif text == "Додати монету":
        await update.message.reply_text("Введи назву монети (наприклад: DOGE):")
        context.user_data["expecting_coin"] = True

    elif context.user_data.get("expecting_coin"):
        coin = text.upper()
        if coin not in coins:
            coins.append(coin)
            leverage[coin] = 300
            await update.message.reply_text(f"✅ Монета {coin} додана з плечем 300×")
        else:
            await update.message.reply_text("⚠️ Монета вже є")
        context.user_data["expecting_coin"] = False

# --- Запуск ---
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(lambda ctx: check_market(app), interval=30, first=10)
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot close a running event loop" in str(e).lower():
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise
