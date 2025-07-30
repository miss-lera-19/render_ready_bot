import time
import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from keep_alive import keep_alive

# 🔐 Дані користувача (замінено на твої)
BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425
MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

# 📈 Початкові налаштування
margin = 100
leverage_map = {"SOL": 300, "BTC": 500, "ETH": 500}
monitored_coins = ["SOL", "BTC", "ETH"]
auto_signals = True

# 📊 Отримати ціну монети
def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return float(response.json()["price"])
    except Exception as e:
        print(f"Помилка отримання ціни для {symbol}: {e}")
        return None

# 🧠 Аналіз ринку (псевдо-логіка для реального сигналу)
def analyze_market(symbol):
    price = get_price(symbol)
    if not price:
        return None

    # Псевдо-умови для сигналу (реальні можна вставити з MEXC Volume + Candles)
    if int(price) % 10 in [1, 2]:  # Імітація імпульсу
        direction = "LONG"
        entry = price
        tp = price * 1.05
        sl = price * 0.985
    elif int(price) % 10 in [7, 8]:  # Імітація SHORT
        direction = "SHORT"
        entry = price
        tp = price * 0.9
        sl = price * 1.017
    else:
        return None

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "leverage": leverage_map.get(symbol, 100),
        "margin": margin
    }

# 📤 Надіслати сигнал
async def send_signal(context: ContextTypes.DEFAULT_TYPE, signal):
    symbol = signal["symbol"]
    direction = signal["direction"]
    entry_price = signal["entry"]
    tp = signal["tp"]
    sl = signal["sl"]
    leverage = signal["leverage"]
    msg = (
        f"📉 Сигнал на {direction.upper()} по {symbol}USDT\n"
        f"🔹Вхід: {entry_price:.2f} USDT\n"
        f"🎯Take Profit: {tp:.3f}\n"
        f"🛡Stop Loss: {sl:.4f}\n"
        f"⚙️Плече: {leverage}×\n"
        f"💰Маржа: ${margin}"
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=msg)

# 🔁 Автоаналіз кожну хвилину
async def auto_check(app):
    while True:
        if auto_signals:
            for coin in monitored_coins:
                signal = analyze_market(coin)
                if signal:
                    await send_signal(app.bot, signal)
        await asyncio.sleep(60)

# 🧠 Обробка команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Запитати сигнали", "Зупинити сигнали"],
        ["Змінити плече", "Змінити маржу"],
        ["Додати монету", "Видалити монету"]
    ]
    await update.message.reply_text("Обери дію:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin, auto_signals
    text = update.message.text

    if text == "Запитати сигнали":
        for coin in monitored_coins:
            signal = analyze_market(coin)
            if signal:
                await send_signal(context, signal)
        return

    if text == "Зупинити сигнали":
        auto_signals = False
        await update.message.reply_text("Автоматичні сигнали вимкнено.")
        return

    if text == "Змінити плече":
        await update.message.reply_text("Введи монету (наприклад, SOL):")
        context.user_data["awaiting"] = "leverage_coin"
        return

    if context.user_data.get("awaiting") == "leverage_coin":
        context.user_data["coin"] = text.upper()
        await update.message.reply_text("Введи нове плече:")
        context.user_data["awaiting"] = "leverage_value"
        return

    if context.user_data.get("awaiting") == "leverage_value":
        coin = context.user_data["coin"]
        try:
            leverage_map[coin] = int(text)
            await update.message.reply_text(f"Плече для {coin} змінено на {text}×")
        except:
            await update.message.reply_text("Помилка. Введи ціле число.")
        context.user_data["awaiting"] = None
        return

    if text == "Змінити маржу":
        await update.message.reply_text("Введи нову маржу в $:")
        context.user_data["awaiting"] = "margin"
        return

    if context.user_data.get("awaiting") == "margin":
        try:
            margin = int(text)
            await update.message.reply_text(f"Маржа оновлена: ${margin}")
        except:
            await update.message.reply_text("Помилка. Введи число.")
        context.user_data["awaiting"] = None
        return

    if text == "Додати монету":
        await update.message.reply_text("Введи символ монети (без USDT):")
        context.user_data["awaiting"] = "add_coin"
        return

    if context.user_data.get("awaiting") == "add_coin":
        coin = text.upper()
        if coin not in monitored_coins:
            monitored_coins.append(coin)
            await update.message.reply_text(f"Монету {coin} додано.")
        else:
            await update.message.reply_text(f"Монета {coin} вже є.")
        context.user_data["awaiting"] = None
        return

    if text == "Видалити монету":
        await update.message.reply_text("Введи символ монети, яку видалити:")
        context.user_data["awaiting"] = "remove_coin"
        return

    if context.user_data.get("awaiting") == "remove_coin":
        coin = text.upper()
        if coin in monitored_coins:
            monitored_coins.remove(coin)
            await update.message.reply_text(f"Монету {coin} видалено.")
        else:
            await update.message.reply_text(f"Монета {coin} не знайдена.")
        context.user_data["awaiting"] = None
        return

    await update.message.reply_text("Команду не розпізнано.")

# ▶️ Запуск
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    keep_alive()
    asyncio.create_task(auto_check(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
