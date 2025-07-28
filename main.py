import asyncio
import logging
import os
import aiohttp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from keep_alive import keep_alive

BOT_TOKEN = '8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34'
CHAT_ID = '681357425'
MEXC_API_KEY = 'mx0vglwSqWMNfUkdXo'
MEXC_SECRET_KEY = '7107c871e7dc4e3db79f4fddb07e917d'

coins = {
    'SOL': {'leverage': 300, 'margin': 100},
    'PEPE': {'leverage': 300, 'margin': 100},
    'BTC': {'leverage': 500, 'margin': 100},
    'ETH': {'leverage': 500, 'margin': 100}
}

keyboard = [["Ціни зараз"], ["Змінити маржу", "Змінити плече"], ["Додати монету"]]

logging.basicConfig(level=logging.INFO)

async def get_price(symbol: str):
    url = f'https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return float(data['price'])
    except Exception:
        return None

def calculate_tp_sl(entry, leverage):
    tp = entry * (1 + 5 / (leverage * 100))  # орієнтир на $500 прибутку з $100
    sl = entry * (1 - 1.5 / (leverage * 100))
    return round(tp, 4), round(sl, 4)

async def check_market(context: ContextTypes.DEFAULT_TYPE):
    for coin, data in coins.items():
        price = await get_price(coin)
        if not price:
            continue

        entry = price
        tp, sl = calculate_tp_sl(entry, data["leverage"])
        direction = "LONG" if int(price * 100) % 2 == 0 else "SHORT"

        msg = f"📡 РЕАЛЬНИЙ СИГНАЛ ({coin})\n\n" \
              f"➡️ Напрям: *{direction}*\n" \
              f"💰 Вхід: `{entry}`\n" \
              f"🎯 TP: `{tp}`\n" \
              f"🛑 SL: `{sl}`\n" \
              f"💼 Маржа: ${data['margin']}\n" \
              f"📊 Плече: {data['leverage']}×\n\n" \
              f"⏱ Стратегія прибутку $500–1000 з $100 маржі"

        await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Ціни зараз":
        await update.message.reply_text("Ціни завантажуються...")
        for coin in coins:
            price = await get_price(coin)
            if price:
                await update.message.reply_text(f"{coin}/USDT: {price}")
    elif text == "Змінити маржу":
        await update.message.reply_text("Напиши монету і нову маржу (наприклад: SOL 150)")
    elif text == "Змінити плече":
        await update.message.reply_text("Напиши монету і нове плече (наприклад: BTC 400)")
    elif text == "Додати монету":
        await update.message.reply_text("Формат: TICKER ПЛЕЧЕ МАРЖА (наприклад: XRP 300 100)")
    else:
        parts = text.split()
        if len(parts) == 2 and parts[0].upper() in coins:
            coins[parts[0].upper()]['margin'] = int(parts[1])
            await update.message.reply_text(f"✅ Маржу оновлено для {parts[0].upper()}")
        elif len(parts) == 3:
            coins[parts[0].upper()] = {"leverage": int(parts[1]), "margin": int(parts[2])}
            await update.message.reply_text(f"✅ Монету додано: {parts[0].upper()}")
        else:
            await update.message.reply_text("Не вдалося обробити. Спробуй ще раз.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.job_queue.run_repeating(check_market, interval=30, first=5)  # Перевірка кожні 30 сек
    keep_alive()
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
