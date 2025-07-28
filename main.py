import os
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from keep_alive import keep_alive

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MEXC_API_KEY = os.getenv("MEXC_API_KEY")
MEXC_SECRET_KEY = os.getenv("MEXC_SECRET_KEY")

user_margin = 100
leverage = {"SOL": 300, "BTC": 500, "ETH": 500}
symbols = ["SOL", "BTC", "ETH"]

def get_price(symbol):
    try:
        response = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT", timeout=10)
        return float(response.json()["price"])
    except Exception:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Ціни зараз", callback_data="prices")],
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("Додати монету", callback_data="add_coin")],
        [InlineKeyboardButton("Видалити монету", callback_data="remove_coin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привіт! Вибери опцію:", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "prices":
        text = "📊 Актуальні ціни:
"
        for sym in symbols:
            price = get_price(sym)
            if price:
                text += f"{sym}/USDT: {price:.4f}
"
            else:
                text += f"{sym}/USDT: помилка API
"
        await query.edit_message_text(text=text)
    elif data == "change_margin":
        await query.edit_message_text("Введи нову маржу у $ (наприклад, 120):")
        context.user_data["awaiting_margin"] = True
    elif data == "change_leverage":
        await query.edit_message_text("Напиши монету і нове плече (наприклад, SOL 400):")
        context.user_data["awaiting_leverage"] = True
    elif data == "add_coin":
        await query.edit_message_text("Введи монету, яку хочеш додати (наприклад, ARB):")
        context.user_data["awaiting_add"] = True
    elif data == "remove_coin":
        await query.edit_message_text("Введи монету, яку хочеш видалити:")
        context.user_data["awaiting_remove"] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if context.user_data.get("awaiting_margin"):
        try:
            global user_margin
            user_margin = float(text)
            await update.message.reply_text(f"✅ Маржу змінено на {user_margin}$")
        except:
            await update.message.reply_text("⚠️ Помилка. Введи число.")
        context.user_data["awaiting_margin"] = False

    elif context.user_data.get("awaiting_leverage"):
        try:
            parts = text.split()
            symbol, lev = parts[0], int(parts[1])
            leverage[symbol] = lev
            await update.message.reply_text(f"✅ Плече для {symbol} встановлено: {lev}×")
        except:
            await update.message.reply_text("⚠️ Формат: BTC 500")
        context.user_data["awaiting_leverage"] = False

    elif context.user_data.get("awaiting_add"):
        if text not in symbols:
            symbols.append(text)
            await update.message.reply_text(f"✅ Додано монету: {text}")
        else:
            await update.message.reply_text("⚠️ Така монета вже є.")
        context.user_data["awaiting_add"] = False

    elif context.user_data.get("awaiting_remove"):
        if text in symbols:
            symbols.remove(text)
            await update.message.reply_text(f"✅ Видалено монету: {text}")
        else:
            await update.message.reply_text("⚠️ Такої монети немає.")
        context.user_data["awaiting_remove"] = False

async def check_market(application):
    while True:
        for symbol in symbols:
            price = get_price(symbol)
            if price:
                direction = "LONG" if int(str(price)[-1]) % 2 == 0 else "SHORT"
                sl = price * (0.985 if direction == "LONG" else 1.015)
                tp = price * (1.05 if direction == "LONG" else 0.95)
                msg = (
                    f"📈 Сигнал {direction} по {symbol}
"
                    f"Ціна входу: {price:.4f} USDT
"
                    f"SL: {sl:.4f}
"
                    f"TP: {tp:.4f}
"
                    f"Маржа: {user_margin}$, Плече: {leverage.get(symbol, '—')}×"
                )
                await application.bot.send_message(chat_id=CHAT_ID, text=msg)
        await asyncio.sleep(60)

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling(non_stop=True, close_loop=False, on_startup=check_market)
