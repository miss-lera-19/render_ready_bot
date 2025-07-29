import os
import asyncio
import logging
import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

user_settings = {
    "margin": 100,
    "leverage": {"SOL": 300, "BTC": 500, "ETH": 500},
    "symbols": ["SOL", "BTC", "ETH"],
}

logging.basicConfig(level=logging.INFO)

# ========= MEXC API ==========
async def get_price(symbol: str) -> float:
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                return float(data["price"])
    except Exception as e:
        print(f"❌ Error getting price for {symbol}: {e}")
        return 0.0

# ========= Стратегія ==========
async def analyze_market(symbol: str) -> str:
    price = await get_price(symbol)
    if price == 0:
        return ""

    # Спрощена стратегія:
    # Якщо остання ціна кратно 5 — LONG
    # Якщо кратно 3 — SHORT
    if int(price) % 5 == 0:
        return "LONG"
    elif int(price) % 3 == 0:
        return "SHORT"
    return ""

async def send_signal(symbol: str, signal_type: str, app):
    price = await get_price(symbol)
    margin = user_settings["margin"]
    leverage = user_settings["leverage"].get(symbol, 100)

    sl = round(price * (0.995 if signal_type == "LONG" else 1.005), 2)
    tp = round(price * (1.05 if signal_type == "LONG" else 0.95), 2)

    msg = (
        f"📈 <b>{signal_type} сигнал</b> по {symbol}/USDT\n"
        f"💰 Вхід: <b>{price}</b>\n"
        f"🛡️ SL: <b>{sl}</b>\n"
        f"🎯 TP: <b>{tp}</b>\n"
        f"💵 Маржа: <b>{margin}$</b>\n"
        f"🚀 Плече: <b>{leverage}×</b>"
    )
    await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="HTML")

# ========= Перевірка ринку ==========
async def check_market(app):
    while True:
        for symbol in user_settings["symbols"]:
            signal_type = await analyze_market(symbol)
            if signal_type:
                await send_signal(symbol, signal_type, app)
        await asyncio.sleep(60)

# ========= Команди ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("Ціни зараз", callback_data="prices")],
    ]
    reply_markup = InlineKeyboardMarkup(kb)
    await update.message.reply_text("👋 Привіт! Я трейдинг-бот. Обери дію:", reply_markup=reply_markup)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.lower()
    if "привіт" in msg:
        await start(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "change_margin":
        await query.edit_message_text("Введи нову маржу в $:")
        context.user_data["awaiting_margin"] = True
    elif query.data == "change_leverage":
        await query.edit_message_text("Введи плече у форматі: SOL 200")
        context.user_data["awaiting_leverage"] = True
    elif query.data == "prices":
        prices = []
        for s in user_settings["symbols"]:
            p = await get_price(s)
            prices.append(f"{s}: {p}")
        await query.edit_message_text("📊 Поточні ціни:\n" + "\n".join(prices))

async def text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if context.user_data.get("awaiting_margin"):
        try:
            user_settings["margin"] = int(text)
            await update.message.reply_text(f"✅ Нова маржа: {text}$")
        except:
            await update.message.reply_text("❌ Помилка. Введи число.")
        context.user_data["awaiting_margin"] = False

    elif context.user_data.get("awaiting_leverage"):
        try:
            parts = text.split()
            symbol, lev = parts[0].upper(), int(parts[1])
            if symbol in user_settings["leverage"]:
                user_settings["leverage"][symbol] = lev
                await update.message.reply_text(f"✅ Нове плече для {symbol}: {lev}×")
            else:
                await update.message.reply_text("❌ Невідома монета.")
        except:
            await update.message.reply_text("❌ Формат: BTC 400")
        context.user_data["awaiting_leverage"] = False

# ========= Запуск ==========
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.TEXT, text_input_handler))

    asyncio.create_task(check_market(app))
    print("✅ Бот запущено")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
