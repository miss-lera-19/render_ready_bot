import logging
import asyncio
import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# === ТВОЇ ДАНІ ===
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

# === НАЛАШТУВАННЯ ===
symbols = {
    "SOL": {"leverage": 300},
    "BTC": {"leverage": 500},
    "ETH": {"leverage": 500}
}
margin = 100

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === ФУНКЦІЯ: Отримання ціни з MEXC ===
def get_price(symbol):
    try:
        url = f"https://contract.mexc.com/api/v1/contract/market/ticker?symbol={symbol}_USDT"
        res = requests.get(url).json()
        return float(res["data"][0]["lastPrice"])
    except Exception as e:
        print("Помилка отримання ціни:", e)
        return None

# === ФУНКЦІЯ: Генерація сигналу ===
async def check_market(app):
    while True:
        for symbol in symbols:
            price = get_price(symbol)
            if not price:
                continue

            # Простий приклад імпульсу: якщо остання ціна кратно 5 — формуємо сигнал
            if int(price) % 5 == 0:
                direction = "LONG" if int(price * 10) % 2 == 0 else "SHORT"
                leverage = symbols[symbol]["leverage"]

                entry = round(price, 4)
                sl = round(entry * (0.997 if direction == "LONG" else 1.003), 4)
                tp = round(entry * (1.015 if direction == "LONG" else 0.985), 4)

                signal = (
                    f"📢 <b>{direction} сигнал</b> по <b>{symbol}/USDT</b>\n\n"
                    f"💰 Вхід: <b>{entry}</b>\n"
                    f"🛡️ SL: <b>{sl}</b>\n"
                    f"🎯 TP: <b>{tp}</b>\n"
                    f"💵 Маржа: <b>${margin}</b>\n"
                    f"⚙️ Плече: <b>{leverage}×</b>"
                )

                await app.bot.send_message(chat_id=CHAT_ID, text=signal, parse_mode="HTML")

        await asyncio.sleep(60)

# === КНОПКИ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Ціни зараз", callback_data="prices")],
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Вітаю! Обери опцію:", reply_markup=reply_markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "prices":
        msg = ""
        for symbol in symbols:
            price = get_price(symbol)
            if price:
                msg += f"{symbol}/USDT: {price}\n"
        await query.edit_message_text(f"📊 Поточні ціни:\n{msg}")
    elif query.data == "change_margin":
        await query.edit_message_text("✍️ Введи нову маржу (в $):")
        context.user_data["awaiting_margin"] = True
    elif query.data == "change_leverage":
        await query.edit_message_text("✍️ Введи монету та нове плече (наприклад: BTC 200):")
        context.user_data["awaiting_leverage"] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin

    if context.user_data.get("awaiting_margin"):
        try:
            margin = int(update.message.text.strip())
            await update.message.reply_text(f"✅ Нова маржа встановлена: ${margin}")
        except:
            await update.message.reply_text("❌ Помилка. Введи число.")
        context.user_data["awaiting_margin"] = False

    elif context.user_data.get("awaiting_leverage"):
        try:
            parts = update.message.text.upper().split()
            symbol, lev = parts[0], int(parts[1])
            if symbol in symbols:
                symbols[symbol]["leverage"] = lev
                await update.message.reply_text(f"✅ Нове плече для {symbol}: {lev}×")
            else:
                await update.message.reply_text("❌ Монета не знайдена.")
        except:
            await update.message.reply_text("❌ Формат: BTC 200")
        context.user_data["awaiting_leverage"] = False

# === ЗАПУСК ===
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    asyncio.create_task(check_market(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
