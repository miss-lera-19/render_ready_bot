import os
import logging
import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# 🔐 Константи
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
COINS = ["SOL_USDT", "PEPE_USDT", "BTC_USDT", "ETH_USDT"]

# 🧠 Початкові параметри
leverage = {"SOL_USDT": 300, "PEPE_USDT": 300, "BTC_USDT": 500, "ETH_USDT": 500}
margin = 100

# 🔧 Логування
logging.basicConfig(level=logging.INFO)

# 🧮 Отримати поточну ціну монети з MEXC API
def get_price(symbol: str):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=5)
        data = response.json()
        return float(data["price"])
    except Exception as e:
        logging.warning(f"❌ Помилка отримання ціни для {symbol}: {e}")
        return None

# 📊 Стратегія: простий аналіз ціни
def generate_signal(symbol: str, price: float):
    if symbol == "SOL_USDT":
        if price < 181:
            return "SHORT"
        elif price > 182:
            return "LONG"
    elif symbol == "PEPE_USDT":
        if price < 0.0000124:
            return "LONG"
        elif price > 0.0000131:
            return "SHORT"
    elif symbol == "BTC_USDT":
        if price > 65000:
            return "LONG"
        elif price < 64000:
            return "SHORT"
    elif symbol == "ETH_USDT":
        if price > 3500:
            return "LONG"
        elif price < 3450:
            return "SHORT"
    return None

# 📢 Надсилання сигналу
async def send_signal(context: ContextTypes.DEFAULT_TYPE, symbol: str, signal: str, price: float):
    lev = leverage[symbol]
    global margin
    entry = price
    sl = round(entry * (0.995 if signal == "LONG" else 1.005), 4)
    tp = round(entry * (1.05 if signal == "LONG" else 0.95), 4)
    text = (
        f"📈 <b>{signal} сигнал</b> для <b>{symbol}</b>\n\n"
        f"💰 Вхід: <code>{entry}</code>\n"
        f"🛡️ SL: <code>{sl}</code>\n"
        f"🎯 TP: <code>{tp}</code>\n"
        f"💵 Маржа: <b>{margin}$</b>\n"
        f"⚙️ Плече: <b>{lev}×</b>\n"
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

# 🔄 Перевірка ринку кожні 30 секунд
async def check_market(context: ContextTypes.DEFAULT_TYPE):
    for symbol in COINS:
        price = get_price(symbol)
        if price:
            signal = generate_signal(symbol, price)
            if signal:
                await send_signal(context, symbol, signal, price)

# 🟢 Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["Ціни зараз"], ["Змінити маржу", "Змінити плече"], ["Додати монету"]]
    await update.message.reply_text("Привіт! Обери дію ⬇️", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

# 📍 Команди
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin
    text = update.message.text
    if text == "Ціни зараз":
        msg = "📊 Поточні ціни:\n"
        for s in COINS:
            p = get_price(s)
            msg += f"{s}: {p}\n" if p else f"{s}: недоступно\n"
        await update.message.reply_text(msg)
    elif text == "Змінити маржу":
        await update.message.reply_text("Введи нову маржу $:")
        context.user_data["action"] = "set_margin"
    elif text == "Змінити плече":
        await update.message.reply_text("Введи через пробіл монету і плече (наприклад: SOL_USDT 500):")
        context.user_data["action"] = "set_leverage"
    elif text == "Додати монету":
        await update.message.reply_text("Введи символ монети (наприклад: DOGE_USDT):")
        context.user_data["action"] = "add_coin"
    elif context.user_data.get("action") == "set_margin":
        try:
            margin = int(text)
            await update.message.reply_text(f"Нова маржа: {margin}$")
        except:
            await update.message.reply_text("❌ Помилка. Введи число.")
        context.user_data["action"] = None
    elif context.user_data.get("action") == "set_leverage":
        try:
            parts = text.split()
            coin, lev = parts[0].upper(), int(parts[1])
            leverage[coin] = lev
            await update.message.reply_text(f"Плече для {coin} оновлено: {lev}×")
        except:
            await update.message.reply_text("❌ Помилка. Приклад: SOL_USDT 500")
        context.user_data["action"] = None
    elif context.user_data.get("action") == "add_coin":
        coin = text.upper()
        if coin not in COINS:
            COINS.append(coin)
            leverage[coin] = 100
            await update.message.reply_text(f"✅ Додано монету: {coin}")
        else:
            await update.message.reply_text("⚠️ Монета вже є.")
        context.user_data["action"] = None
    else:
        await update.message.reply_text("Вибери дію з меню або введи коректну команду.")

# 🚀 Запуск бота
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ✅ Оновлений правильний виклик job queue
    application.job_queue.run_repeating(check_market, interval=30, first=10)

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
