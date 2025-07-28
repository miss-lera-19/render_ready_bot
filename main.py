import os
import logging
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes, MessageHandler, filters
)

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

MEXC_API_KEY = "mx0vglwSqWMNfUkdXo"
MEXC_SECRET_KEY = "7107c871e7dc4e3db79f4fddb07e917d"

user_margin = 100
user_leverage = {"SOL": 300, "BTC": 500, "ETH": 500}
enabled_coins = ["SOL", "BTC", "ETH"]

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Змінити маржу", callback_data="change_margin")],
        [InlineKeyboardButton("Змінити плече", callback_data="change_leverage")],
        [InlineKeyboardButton("Додати монету", callback_data="add_coin")],
        [InlineKeyboardButton("Видалити монету", callback_data="remove_coin")],
        [InlineKeyboardButton("Ціни зараз", callback_data="prices")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Вітаю! Оберіть опцію:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "change_margin":
        await query.edit_message_text("Введіть нову маржу в $:")
        context.user_data["awaiting_margin"] = True
    elif query.data == "change_leverage":
        await query.edit_message_text("Введіть монету і нове плече (наприклад: SOL 250):")
        context.user_data["awaiting_leverage"] = True
    elif query.data == "add_coin":
        await query.edit_message_text("Введіть назву монети, яку хочете додати:")
        context.user_data["awaiting_add_coin"] = True
    elif query.data == "remove_coin":
        await query.edit_message_text("Введіть назву монети, яку хочете видалити:")
        context.user_data["awaiting_remove_coin"] = True
    elif query.data == "prices":
        await send_prices(context.bot)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_margin, user_leverage, enabled_coins
    text = update.message.text.upper()

    if context.user_data.get("awaiting_margin"):
        try:
            user_margin = float(text)
            await update.message.reply_text(f"Маржа оновлена: ${user_margin}")
        except:
            await update.message.reply_text("❌ Невірне значення.")
        context.user_data["awaiting_margin"] = False

    elif context.user_data.get("awaiting_leverage"):
        try:
            coin, lev = text.split()
            user_leverage[coin] = int(lev)
            await update.message.reply_text(f"Плече для {coin} встановлено: {lev}×")
        except:
            await update.message.reply_text("❌ Введіть у форматі: SOL 250")
        context.user_data["awaiting_leverage"] = False

    elif context.user_data.get("awaiting_add_coin"):
        if text not in enabled_coins:
            enabled_coins.append(text)
            await update.message.reply_text(f"✅ Монета {text} додана.")
        else:
            await update.message.reply_text("⚠️ Монета вже додана.")
        context.user_data["awaiting_add_coin"] = False

    elif context.user_data.get("awaiting_remove_coin"):
        if text in enabled_coins:
            enabled_coins.remove(text)
            await update.message.reply_text(f"🗑️ Монета {text} видалена.")
        else:
            await update.message.reply_text("⚠️ Такої монети немає.")
        context.user_data["awaiting_remove_coin"] = False

async def send_prices(bot):
    text = "📊 Актуальні ціни:\n"
    for coin in enabled_coins:
        price = await get_price(coin)
        text += f"{coin}: {price} USDT\n"
    await bot.send_message(chat_id=CHAT_ID, text=text)

async def get_price(symbol):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        res = requests.get(url, timeout=5)
        return float(res.json().get("price", 0))
    except:
        return 0

async def check_signals(app):
    while True:
        for coin in enabled_coins:
            price = await get_price(coin)
            if price == 0:
                continue

            impulse = price % 2 < 1.5  # умовний імпульс
            bullish = int(str(price)[-1]) % 2 == 0  # напрямок свічки
            volume_ok = price % 10 > 1.5  # умовний обʼєм

            if impulse and bullish and volume_ok:
                entry = round(price, 2)
                sl = round(entry * 0.995, 2)
                tp = round(entry * 1.03, 2)
                leverage = user_leverage.get(coin, 100)

                await app.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"📈 Сигнал на LONG по {coin}\n💰 Вхід: {entry} USDT\n🛡️ SL: {sl}\n🎯 TP: {tp}\n💵 Маржа: ${user_margin}\n🚀 Плече: {leverage}×"
                )

        await asyncio.sleep(60)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))

    app.run_async(check_signals(app))
    app.run_polling()
