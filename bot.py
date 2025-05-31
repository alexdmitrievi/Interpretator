import asyncio
import openai
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import TELEGRAM_TOKEN, CHAT_ID, OPENAI_API_KEY
from parser import get_important_events
from datetime import datetime
import pytz
from interpreter import btc_eth_forecast

openai.api_key = OPENAI_API_KEY

keyboard = ReplyKeyboardMarkup(
    [["🧠 Интерпретировать новости"]],
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
        await send_digest(update.effective_chat.id, context)

async def gpt_interpretation(event, actual, forecast):
    prompt = (
        f"Событие: {event}\n"
        f"Факт: {actual}, Прогноз: {forecast}\n"
        "Дай краткий комментарий как аналитик: как это может повлиять на доллар, фондовый рынок и криптовалюту?"
    )
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Ошибка GPT: {e}"

async def send_digest(chat_id, context):
    events = get_important_events()

    if not events:
        await context.bot.send_message(chat_id=chat_id, text="🔍 Сейчас нет важных новостей.")
        return

    if "error" in events[0]:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {events[0]['error']}")
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

        if e.get("bulls") == 3:
            delta = float(e['actual']) - float(e['forecast'])
            forecast = btc_eth_forecast(e['event'], delta)
            text += f"\n\n💡 {forecast}"

        gpt_comment = await gpt_interpretation(e['event'], e['actual'], e['forecast'])
        text += f"\n\n🧠 Мнение аналитика:\n{gpt_comment}"

        await context.bot.send_message(chat_id=chat_id, text=text)

async def auto_loop(app: Application):
    await asyncio.sleep(60)
    while True:
        try:
            await send_digest(CHAT_ID, app)
            moscow = pytz.timezone("Europe/Moscow")
            now = datetime.now(moscow).strftime("%H:%M")
            await app.bot.send_message(chat_id=CHAT_ID, text=f"⏰ Цикл завершён в {now} (МСК). Следующее обновление через 60 минут.")
        except Exception as e:
            await app.bot.send_message(chat_id=CHAT_ID, text=f"❌ Ошибка: {e}")
        await asyncio.sleep(3600)

async def after_startup(app: Application):
    await app.bot.send_message(chat_id=CHAT_ID, text="🤖 Бот запущен. Я буду присылать макроэкономические события каждый час.")
    asyncio.create_task(auto_loop(app))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(after_startup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()




