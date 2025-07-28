import logging
import asyncio
import aiohttp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackContext

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
WEBHOOK_URL = "https://render-ready-bot.onrender.com"

symbols = {
    "SOL": {"leverage": 300},
    "PEPE": {"leverage": 300},
    "BTC": {"leverage": 500},
    "ETH": {"leverage": 500}
}

user_margin = 100

logging.basicConfig(level=logging.INFO)

keyboard = ReplyKeyboardMarkup(
    [["Змінити маржу", "Змінити плече"],
     ["Додати монету", "Ціни зараз"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущено! ✅", reply_markup=keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_margin
    msg = update.message.text

    if msg.lower() == "привіт":
        await update.message.reply_text("Привіт! Я активний ✅", reply_markup=keyboard)
    elif msg == "Ціни зараз":
        await send_prices(context)
    elif msg == "Змінити маржу":
        await update.message.reply_text("Введи нову маржу (наприклад: 120):")
        context.user_data["awaiting_margin"] = True
    elif msg == "Змінити плече":
        await update.message.reply_text("Введи монету і нове плече (наприклад: SOL 250):")
        context.user_data["awaiting_leverage"] = True
    elif msg == "Додати монету":
        await update.message.reply_text("Введи символ монети (наприклад: XRP):")
        context.user_data["awaiting_new_symbol"] = True
    elif context.user_data.get("awaiting_margin"):
        try:
            user_margin = float(msg)
            await update.message.reply_text(f"Маржу оновлено: ${user_margin}")
        except:
            await update.message.reply_text("❌ Помилка! Введи число.")
        context.user_data["awaiting_margin"] = False
    elif context.user_data.get("awaiting_leverage"):
        try:
            parts = msg.upper().split()
            symbol, lev = parts[0], int(parts[1])
            if symbol in symbols:
                symbols[symbol]["leverage"] = lev
                await update.message.reply_text(f"Плече для {symbol} оновлено: {lev}×")
            else:
                await update.message.reply_text("Монета не знайдена.")
        except:
            await update.message.reply_text("❌ Формат: BTC 400")
        context.user_data["awaiting_leverage"] = False
    elif context.user_data.get("awaiting_new_symbol"):
        sym = msg.upper()
        if sym not in symbols:
            symbols[sym] = {"leverage": 100}
            await update.message.reply_text(f"Монету {sym} додано з плечем 100×.")
        else:
            await update.message.reply_text("Монета вже існує.")
        context.user_data["awaiting_new_symbol"] = False

async def fetch_price(symbol):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return float(data["price"])
    except:
        return None

async def check_market(app: ApplicationBuilder):
    for symbol in symbols:
        price = await fetch_price(symbol)
        if price is None:
            continue

        direction = "LONG" if int(price * 100) % 2 == 0 else "SHORT"

        lev = symbols[symbol]["leverage"]
        entry = price
        sl = round(entry * (0.995 if direction == "LONG" else 1.005), 6)
        tp = round(entry * (1.05 if direction == "LONG" else 0.95), 6)

        text = f"""
💰 <b>{symbol}/USDT СИГНАЛ ({direction})</b>
▶ Вхід: <code>{entry}</code>
🎯 TP: <code>{tp}</code>
🛡 SL: <code>{sl}</code>
💵 Маржа: <b>${user_margin}</b>
📈 Плече: <b>{lev}×</b>
        """.strip()

        await app.bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

async def send_prices(context: CallbackContext):
    msg = "📊 Поточні ціни:\n"
    for sym in symbols:
        p = await fetch_price(sym)
        if p:
            msg += f"• {sym}: <b>{p}</b>\n"
    await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="HTML")

async def run():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def loop_check(_):
        while True:
            await check_market(app)
            await asyncio.sleep(30)

    app.create_task(loop_check(app))

    await app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    asyncio.run(run())
