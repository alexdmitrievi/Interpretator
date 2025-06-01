import logging
import requests
import asyncio
from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config import TELEGRAM_TOKEN, OPENAI_API_KEY
from openai import AsyncOpenAI
from parser import get_important_events
import re

logging.basicConfig(level=logging.INFO)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

reply_keyboard = [["🧠 Интерпретировать новости"], ["📉 Прогноз по BTC", "📉 Прогноз по ETH"], ["📊 Оценить альтсезон"]]
menu_keyboard = [["🔁 Перезапустить бота"], ["📢 Опубликовать пост"]]

# Пользователи, которые ждут автоматическую интерпретацию следующей новости
waiting_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Выбери действие ниже:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text == "📉 Прогноз по BTC":
        context.user_data["price_asset"] = "BTC"
        await update.message.reply_text("Введите текущую цену BTC (например, 103500):")
    elif text == "📉 Прогноз по ETH":
        context.user_data["price_asset"] = "ETH"
        await update.message.reply_text("Введите цену ETH (например, 3820):")
    elif "price_asset" in context.user_data:
        try:
            price = float(text.replace(",", ".").replace("$", ""))
            asset = context.user_data.pop("price_asset")
            prompt = (
                f"Цена {asset}: ${price}\n"
                "Оцени:\n"
                "1. Возможна ли коррекция?\n"
                "2. Риск разворота вниз?\n"
                "3. Сохраняется ли бычий тренд?\nОтветь кратко."
            )
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            await update.message.reply_text(f"📉 Прогноз по {asset}:\n\n{response.choices[0].message.content.strip()}", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        except ValueError:
            await update.message.reply_text("Введите корректную цену.", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

    elif text == "📊 Оценить альтсезон":
        try:
            global_data = requests.get("https://api.coingecko.com/api/v3/global", timeout=10).json()

            if "data" not in global_data:
                raise ValueError(f"Некорректный ответ от CoinGecko: {global_data}")

            btc_d = round(global_data["data"]["market_cap_percentage"]["btc"], 2)
            eth_d = round(global_data["data"]["market_cap_percentage"]["eth"], 2)

            eth_btc_resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=btc",
                timeout=10
            )
            eth_btc_data = eth_btc_resp.json()
            eth_btc = round(eth_btc_data["ethereum"]["btc"], 5)

            prompt = (
                f"BTC Dominance: {btc_d}%
ETH Dominance: {eth_d}%
ETH/BTC: {eth_btc}
"
                "Оцени вероятность альтсезона."
            )
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            await update.message.reply_text(
                f"📊 Альтсезон:

{response.choices[0].message.content.strip()}",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
            )
        except Exception as e:
            await update.message.reply_text(
                f"⚠️ Ошибка при получении данных альтсезона: {e}",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
            )

    elif text == "🧠 Интерпретировать новости":
        waiting_users.add(user_id)
        await update.message.reply_text("⏳ Жду ближайшее важное событие. Интерпретация придёт автоматически!", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

    elif text == "🔁 Перезапустить бота":
        await start(update, context)

    elif text == "📢 Опубликовать пост":
        await publish_post(update)

    else:
        await update.message.reply_text("Выбери пункт из меню.", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

async def publish_post(update: Update):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Перейти к боту", url="https://t.me/Parser_newbot")]
    ])
    text = (
        "👋 Добро пожаловать!\n\n"
        "🔔 Здесь вы получите:\n"
        "• Важные макроданные\n"
        "• Интерпретации событий\n"
        "• Торговые идеи и прогнозы\n\n"
        "👇 Нажмите, чтобы начать"
    )
    await update.message.reply_text(text, reply_markup=keyboard)

async def hourly_news_check(app):
    global waiting_users
    await asyncio.sleep(10)
    while True:
        try:
            events = get_important_events(debug=False)
            for e in events:
                if e.get("actual") and e.get("forecast") and e.get("bulls", 0) == 3:
                    try:
                        event = e['event']
                        actual = float(e['actual'].replace(',', '.').replace('%', ''))
                        forecast = float(e['forecast'].replace(',', '.').replace('%', ''))
                        prompt = (
                            f"Событие: {event}\n"
                            f"Факт: {actual} | Прогноз: {forecast}\n\n"
                            "Как это повлияет на доллар, рынок и крипту? Кратко."
                        )
                        response = await client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        interpretation = response.choices[0].message.content.strip()
                        summary = (
                            f"🔔 Новость: {event}\n"
                            f"🕒 Время: {e['time']}\n"
                            f"Факт: {e['actual']} | Прогноз: {e['forecast']}\n"
                            f"{e['summary']}\n\n"
                            f"🧠 Интерпретация GPT:\n{interpretation}"
                        )
                        # отправляем только тем, кто ждёт интерпретацию
                        for user_id in waiting_users:
                            await app.bot.send_message(chat_id=user_id, text=summary, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
                        waiting_users.clear()
                    except Exception as ex:
                        logging.error(f"Ошибка автоинтерпретации: {ex}")
                        continue
        except Exception as e:
            logging.error(f"Ошибка в парсинге новостей: {e}")
        await asyncio.sleep(3600)

async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Перезапустить бота"),
        BotCommand("publish", "Опубликовать пост")
    ])
    asyncio.create_task(hourly_news_check(app))

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()


















