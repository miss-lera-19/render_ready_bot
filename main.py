import os
import logging
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from keep_alive import keep_alive

# === Налаштування ===
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

# === Логи ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Стартова маржа і плече ===
user_state = {
    "margin": 100,
    "leverage": {
        "SOL": 300,
        "PEPE": 300,
        "BTC": 500,
        "ETH": 500
    }
}

# === Отримання ціни монети з MEXC ===
async def get_price(symbol: str):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return float(data['price'])
    except Exception as e:
        logger.warning(f"Помилка отримання ціни для {symbol}: {e}")
        return None

# === Генерація сигналу ===
async def generate_signal(symbol: str):
    price = await get_price(symbol)
    if price is None:
        return None

    direction = "LONG" if price % 2 < 1 else "SHORT"
    entry = round(price, 6)
    leverage = user_state["leverage"].get(symbol, 100)
    margin = user_state["margin"]
    size = margin * leverage

    if direction == "LONG":
        sl = round(entry * 0.98, 6)
        tp = round(entry * 1.05, 6)
    else:
        sl = round(entry * 1.02, 6)
        tp = round(entry * 0.95, 6)

    return f"🚀 <b>{symbol}</b> {direction} SIGNAL\n💰 Entry: <code>{entry}</code>\n🎯 TP: <code>{tp}</code>\n🛡 SL: <code>{sl}</code>\n📊 Leverage: <b>{leverage}×</b>\n💼 Margin: <b>{margin}$</b>"

# === Цикл перевірки ринку ===
async def check_market(context: ContextTypes.DEFAULT_TYPE):
    for symbol in ["SOLUSDT", "PEPEUSDT", "BTCUSDT", "ETHUSDT"]:
        signal = await generate_signal(symbol)
        if signal:
            await context.bot.send_message(chat_id=CHAT_ID, text=signal, parse_mode="HTML")

# === Обробка кнопок ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "margin":
        await query.edit_message_text("Введіть нову маржу:")
        context.user_data["expecting"] = "margin"
    elif query.data == "leverage":
        await query.edit_message_text("Введіть монету і нове плече (наприклад: SOL 400):")
        context.user_data["expecting"] = "leverage"
    elif query.data == "prices":
        prices = []
        for symbol in ["SOLUSDT", "PEPEUSDT", "BTCUSDT", "ETHUSDT"]:
            price = await get_price(symbol)
            prices.append(f"{symbol}: <b>{price}</b>" if price else f"{symbol}: помилка")
        await query.edit_message_text("\n".join(prices), parse_mode="HTML")

# === Повідомлення користувача ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "expecting" in context.user_data:
        if context.user_data["expecting"] == "margin":
            try:
                user_state["margin"] = int(update.message.text)
                await update.message.reply_text(f"✅ Маржа оновлена: {user_state['margin']}$")
            except:
                await update.message.reply_text("⚠️ Введіть правильне число.")
        elif context.user_data["expecting"] == "leverage":
            try:
                parts = update.message.text.strip().upper().split()
                coin, lev = parts[0], int(parts[1])
                if coin in user_state["leverage"]:
                    user_state["leverage"][coin] = lev
                    await update.message.reply_text(f"✅ Плече для {coin} оновлено: {lev}×")
                else:
                    await update.message.reply_text("⚠️ Монета не знайдена.")
            except:
                await update.message.reply_text("⚠️ Введіть у форматі: SOL 400")
        context.user_data["expecting"] = None
    else:
        await update.message.reply_text("👋 Напишіть /start для запуску.")

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📈 Змінити маржу", callback_data="margin")],
        [InlineKeyboardButton("⚙️ Змінити плече", callback_data="leverage")],
        [InlineKeyboardButton("💵 Ціни зараз", callback_data="prices")]
    ]
    await update.message.reply_text("🤖 Бот активний. Оберіть дію:", reply_markup=InlineKeyboardMarkup(keyboard))

# === Головна функція ===
async def main():
    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_repeating(check_market, interval=30, first=10)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
