
import logging
import asyncio
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import aiohttp

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
coins = ["SOL_USDT", "PEPE_USDT", "BTC_USDT", "ETH_USDT"]
leverage = {"SOL_USDT": 300, "PEPE_USDT": 300, "BTC_USDT": 500, "ETH_USDT": 500}
margin = 100

keyboard = [["Змінити маржу", "Змінити плече"], ["Додати монету", "Ціни зараз"]]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin
    text = update.message.text
    if text == "Ціни зараз":
        await update.message.reply_text("Ціни завантажуються...")
        await send_prices(context)
    elif text == "Змінити маржу":
        await update.message.reply_text("Введи нову маржу ($):")
        context.user_data["awaiting_margin"] = True
    elif text == "Змінити плече":
        await update.message.reply_text("Функція зміни плеча ще в розробці.")
    elif text == "Додати монету":
        await update.message.reply_text("Введи назву монети у форматі XXX_USDT:")
        context.user_data["awaiting_coin"] = True
    elif context.user_data.get("awaiting_margin"):
        try:
            margin = float(text)
            await update.message.reply_text(f"Маржа оновлена: {margin}$")
        except:
            await update.message.reply_text("Помилка. Введи число.")
        context.user_data["awaiting_margin"] = False
    elif context.user_data.get("awaiting_coin"):
        coin = text.upper()
        if coin not in coins:
            coins.append(coin)
            leverage[coin] = 300
            await update.message.reply_text(f"Монету {coin} додано.")
        else:
            await update.message.reply_text("Монета вже існує.")
        context.user_data["awaiting_coin"] = False

async def send_prices(context: ContextTypes.DEFAULT_TYPE):
    async with aiohttp.ClientSession() as session:
        messages = []
        for coin in coins:
            try:
                async with session.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={coin}") as resp:
                    data = await resp.json()
                    price = float(data["price"])
                    signal = await generate_signal(coin, price)
                    messages.append(signal)
            except:
                messages.append(f"❌ {coin}: помилка отримання ціни")
        await context.bot.send_message(chat_id=CHAT_ID, text="\n".join(messages))

async def generate_signal(coin, price):
    # Спрощена стратегія імпульсу (демо логіка)
    direction = "LONG" if price % 2 > 1 else "SHORT"
    sl = round(price * (0.995 if direction == "LONG" else 1.005), 4)
    tp = round(price * (1.05 if direction == "LONG" else 0.95), 4)
    lev = leverage.get(coin, 100)
    return f"📈 Сигнал {direction} по {coin}\nЦіна входу: {price}\nSL: {sl}\nTP: {tp}\nМаржа: ${margin}\nПлече: {lev}×"

async def periodic_check(app):
    while True:
        try:
            await send_prices(app.bot)
        except Exception as e:
            print(f"Помилка: {e}")
        await asyncio.sleep(30)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.job_queue.run_once(lambda ctx: send_prices(ctx), when=5)
    asyncio.create_task(periodic_check(app))
    app.run_polling()
