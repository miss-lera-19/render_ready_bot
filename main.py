import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler
from keep_alive import keep_alive

BOT_TOKEN = "8441710554:AAGFDgaFwQpcx3bFQ-2FgjjlkK7CEKxmz34"
CHAT_ID = 681357425

symbols = {'SOLUSDT': 300, 'BTCUSDT': 500, 'ETHUSDT': 500}
margin = 100
auto_signals = True

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Бот запущено ✅", reply_markup=main_keyboard())

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Запитати сигнали", callback_data='get_signals')],
        [InlineKeyboardButton("🛑 Зупинити сигнали", callback_data='stop_signals')],
        [InlineKeyboardButton("💰 Змінити маржу", callback_data='change_margin')],
        [InlineKeyboardButton("⚙️ Змінити плече", callback_data='change_leverage')],
        [InlineKeyboardButton("➕ Додати монету", callback_data='add_symbol')],
        [InlineKeyboardButton("➖ Видалити монету", callback_data='remove_symbol')],
    ])

async def button(update: Update, context: CallbackContext):
    global auto_signals
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'get_signals':
        await send_signals(context)
    elif data == 'stop_signals':
        auto_signals = False
        await query.edit_message_text("⛔ Авто-сигнали зупинено.")
    elif data == 'change_margin':
        await query.edit_message_text("Введіть нову маржу (напишіть сюди число):")
        context.user_data['awaiting_margin'] = True
    elif data == 'change_leverage':
        await query.edit_message_text("Формат: SOLUSDT 300 або BTCUSDT 500")
        context.user_data['awaiting_leverage'] = True
    elif data == 'add_symbol':
        await query.edit_message_text("Напишіть монету для додавання (наприклад, XRPUSDT):")
        context.user_data['awaiting_add'] = True
    elif data == 'remove_symbol':
        await query.edit_message_text("Напишіть монету для видалення (наприклад, ETHUSDT):")
        context.user_data['awaiting_remove'] = True

async def handle_message(update: Update, context: CallbackContext):
    global margin
    text = update.message.text.strip().upper()
    if context.user_data.get('awaiting_margin'):
        if text.isdigit():
            margin = int(text)
            await update.message.reply_text(f"Нова маржа встановлена: ${margin}")
        else:
            await update.message.reply_text("Невірне значення. Введіть лише число.")
        context.user_data['awaiting_margin'] = False
    elif context.user_data.get('awaiting_leverage'):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            symbols[parts[0]] = int(parts[1])
            await update.message.reply_text(f"Плече для {parts[0]} встановлено: {parts[1]}x")
        else:
            await update.message.reply_text("Формат неправильний. Наприклад: SOLUSDT 300")
        context.user_data['awaiting_leverage'] = False
    elif context.user_data.get('awaiting_add'):
        symbols[text] = 300
        await update.message.reply_text(f"Монета {text} додана з плечем 300x.")
        context.user_data['awaiting_add'] = False
    elif context.user_data.get('awaiting_remove'):
        if text in symbols:
            del symbols[text]
            await update.message.reply_text(f"Монета {text} видалена.")
        else:
            await update.message.reply_text("Монета не знайдена.")
        context.user_data['awaiting_remove'] = False

async def send_signals(context: CallbackContext):
    for symbol, leverage in symbols.items():
        price = fetch_price(symbol)
        if price:
            entry = round(price, 2)
            tp = round(entry * 0.9, 3)
            sl = round(entry * 1.02, 3)
            signal = f"📉 Сигнал на SHORT по {symbol}
"                      f"🔷 Вхід: {entry} USDT
"                      f🎯 Take Profit: {tp}
"                      f"🛡️ Stop Loss: {sl}
"                      f"⚙️ Плече: {leverage}×
"                      f"💰 Маржа: ${margin}"
            await context.bot.send_message(chat_id=CHAT_ID, text=signal)

def fetch_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=5)
        return float(response.json()['price'])
    except:
        return None

async def auto_loop(app):
    global auto_signals
    while True:
        if auto_signals:
            await send_signals(app)
        await asyncio.sleep(60)

def main():
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(None, handle_message))
    app.post_init = lambda _: asyncio.create_task(auto_loop(app))
    app.run_polling()

if __name__ == "__main__":
    main()
