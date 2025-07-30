import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

margin = 100
leverage = {"SOLUSDT": 300, "BTCUSDT": 500, "ETHUSDT": 500}
symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]

main_menu = ReplyKeyboardMarkup(
    [["Ціни зараз"], ["Змінити маржу", "Змінити плече"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущено", reply_markup=main_menu)

async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Поточні ціни:\n"
    for symbol in symbols:
        try:
            response = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}")
            price = float(response.json()["price"])
            text += f"{symbol}: {price}\n"
        except Exception:
            text += f"{symbol}: помилка\n"
    await update.message.reply_text(text)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global margin
    text = update.message.text

    if text == "Ціни зараз":
        await show_prices(update, context)

    elif text == "Змінити маржу":
        await update.message.reply_text("Введіть нову маржу у $:")

    elif text.replace(".", "").isdigit():
        margin = float(text)
        await update.message.reply_text(f"Нова маржа: ${margin}")

    elif text == "Змінити плече":
        await update.message.reply_text("Введіть монету і плече (наприклад: SOLUSDT 400)")

    elif any(sym in text for sym in symbols) and any(char.isdigit() for char in text):
        parts = text.split()
        if len(parts) == 2 and parts[0] in symbols:
            leverage[parts[0]] = int(parts[1])
            await update.message.reply_text(f"Нове плече для {parts[0]}: {parts[1]}x")

async def market_check(app):
    import asyncio
    while True:
        for symbol in symbols:
            try:
                r = requests.get(f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=3")
                data = r.json()
                if not isinstance(data, list) or len(data) < 3:
                    continue

                last = data[-1]
                prev = data[-2]

                last_open, last_close, last_vol = float(last[1]), float(last[4]), float(last[5])
                prev_open, prev_close, prev_vol = float(prev[1]), float(prev[4]), float(prev[5])

                signal = ""
                if last_close > last_open and last_close > prev_close and last_vol >= prev_vol:
                    signal = "LONG"
                elif last_close < last_open and last_close < prev_close and last_vol >= prev_vol:
                    signal = "SHORT"

                if signal:
                    entry = last_close
                    stop_loss = round(entry * (0.995 if signal == "LONG" else 1.005), 4)
                    take_profit = round(entry * (1.05 if signal == "LONG" else 0.95), 4)
                    msg = (
                        f"Сигнал {signal} ({symbol})\n"
                        f"Вхід: {entry}\n"
                        f"SL: {stop_loss}\n"
                        f"TP: {take_profit}\n"
                        f"Маржа: ${margin}\n"
                        f"Плече: {leverage[symbol]}x\n\n"
                        f"Стратегія: імпульс, обсяг, напрям свічки"
                    )
                    await app.bot.send_message(chat_id=CHAT_ID, text=msg)
            except Exception as e:
                print(f"Помилка при перевірці {symbol}: {e}")
                continue
        await asyncio.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    import asyncio
    app.run_task(market_check(app))
    app.run_polling()
