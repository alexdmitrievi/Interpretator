import asyncio
import openai
import os
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import TELEGRAM_TOKEN, CHAT_ID, OPENAI_API_KEY
from parser import get_important_events
from datetime import datetime
import pytz
from interpreter import btc_eth_forecast

openai.api_key = OPENAI_API_KEY

keyboard = ReplyKeyboardMarkup(
    [
        ["🧠 Интерпретировать новости"],
        ["🔬 Посмотреть ожидаемые события"],
        ["🔁 Перезапустить бота"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я интерпретирую макроэкономические новости.\n"
        "Нажми кнопку ниже или жди — я сам пришлю важные события.",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🧠 Интерпретировать новости":
        await send_digest(update.effective_chat.id, context, debug=False)
    elif update.message.text == "🔬 Посмотреть ожидаемые события":
        await send_digest(update.effective_chat.id, context, debug=True)
    elif update.message.text == "🔁 Перезапустить бота":
        await start(update, context)

async def gpt_interpretation(event, actual, forecast):
    prompt = (
        f"Событие: {event}\n"
        f"Факт: {actual}, Прогноз: {forecast}\n"
        "1. Как это может повлиять на доллар, фондовый рынок и криптовалюту?\n"
        "2. Может ли это событие стать катализатором для притока ликвидности и бычьего тренда?\n"
        "3. Может ли это событие спровоцировать разворот и возвращение к медвежьему рынку?\n"
        "Ответь кратко, но по существу."
    )
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()

        text_lower = content.lower()
        is_bullish = any(word in text_lower for word in ["катализатор", "приток ликвидности", "сильный рост"])
        is_bearish = any(word in text_lower for word in ["разворот", "медвежий", "обвал", "уход в риски"])

        return content, is_bullish, is_bearish
    except Exception as e:
        return f"⚠️ Ошибка GPT: {e}", False, False

async def send_digest(chat_id, context, debug=False):
    events = get_important_events(debug=debug)

    if not events:
        await context.bot.send_message(chat_id=chat_id, text="🔍 Сейчас нет важных новостей.", reply_markup=keyboard)
        return

    if "error" in events[0]:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {events[0]['error']}", reply_markup=keyboard)
        return

    for e in events:
        bull_emoji = "🐂" * e.get("bulls", 0)
        header = f"{bull_emoji} {e['event']}"

        text = (
            f"📊 {header}\n"
            f"🕒 Время: {e['time']}\n"
            f"Факт: {e['actual']} | Прогноз: {e['forecast']}\n"
            f"{e['summary']}\n"
            f"🔮 Вероятность: {e['probability']}%"
        )

        if not debug and e.get("bulls") == 3:
            try:
                delta = float(e['actual']) - float(e['forecast'])
                forecast = btc_eth_forecast(e['event'], delta)
                text += f"\n\n💡 {forecast}"
            except:
                pass

        if not debug:
            gpt_comment, is_bullish, is_bearish = await gpt_interpretation(e['event'], e['actual'], e['forecast'])
            text += f"\n\n🧠 Мнение аналитика:\n{gpt_comment}"
            if is_bullish:
                text += "\n\n🚀 Потенциальный катализатор роста"
            if is_bearish:
                text += "\n\n⚠️ Возможный разворот тренда в медвежью фазу"

        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

async def auto_loop(app: Application):
    await asyncio.sleep(60)
    while True:
        try:
            await send_digest(CHAT_ID, app, debug=False)
            moscow = pytz.timezone("Europe/Moscow")
            now = datetime.now(moscow).strftime("%H:%M")
            await app.bot.send_message(chat_id=CHAT_ID, text=f"⏰ Цикл завершён в {now} (МСК). Следующее обновление через 60 минут.", reply_markup=keyboard)
        except Exception as e:
            await app.bot.send_message(chat_id=CHAT_ID, text=f"❌ Ошибка: {e}", reply_markup=keyboard)
        await asyncio.sleep(3600)

async def after_startup(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Перезапустить бота"),
        BotCommand("digest", "Интерпретировать новости"),
        BotCommand("upcoming", "Ожидаемые события")
    ])
    await app.bot.send_message(chat_id=CHAT_ID, text="🤖 Бот запущен. Я буду присылать макроэкономические события каждый час.", reply_markup=keyboard)
    asyncio.create_task(auto_loop(app))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(after_startup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()








