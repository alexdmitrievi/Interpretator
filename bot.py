import logging
import requests
import asyncio
from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config import TELEGRAM_TOKEN, OPENAI_API_KEY
from openai import AsyncOpenAI
from parser import get_important_events, parse_event_page
from interpreter import interpret_event, get_trading_signal
import re

logging.basicConfig(level=logging.INFO)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

reply_keyboard = [["🧠 Интерпретировать новости"], ["📉 Прогноз по BTC", "📉 Прогноз по ETH"], ["📊 Оценить альтсезон"]]
menu_keyboard = [["🔁 Перезапустить бота"], ["📢 Опубликовать пост"]]

waiting_users = set()
DEBUG_MODE = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"[COMMAND] /start от {update.effective_user.id}")
    await update.message.reply_text("👋 Привет! Выбери действие ниже:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

if "investing.com/economic-calendar" in text:
    import re
    match = re.search(r"https?://[^\s]+", text)
    if not match:
        await update.message.reply_text("⚠️ Не удалось извлечь ссылку из текста.", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        return

    url = match.group(0)
    await update.message.reply_text("⏳ Анализируем событие...")
    result = parse_event_page(url)

    if "error" in result:
        await update.message.reply_text(f"⚠️ {result['error']}", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        return

    if "actual" not in result or "forecast" not in result:
        msg = f"📊 Событие: {result['event']}\n{result['summary']}"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        return

    msg = (
        f"📊 Событие: {result['event']}\n"
        f"Факт: {result['actual']} | Прогноз: {result['forecast']}\n"
        f"🧠 Интерпретация: {result['summary']}"
    )

    delta = float(result['actual'].replace('%', '').replace(',', '.')) - float(result['forecast'].replace('%', '').replace(',', '.'))
    signal_btc, signal_eth = get_trading_signal(result['event'], delta)
    msg += f"\n📈 Рекомендации:\n• BTC: {signal_btc}\n• ETH: {signal_eth}"

    try:
        gpt_prompt = (
            f"Событие: {result['event']}\n"
            f"Факт: {result['actual']} | Прогноз: {result['forecast']}\n"
            "Как это повлияет на доллар, рынок и криптовалюты? Кратко."
        )
        gpt_response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": gpt_prompt}]
        )
        gpt_text = gpt_response.choices[0].message.content.strip()
        msg += f"\n🧠 GPT: {gpt_text}"
    except Exception as e:
        msg += f"\n⚠️ GPT-ошибка: {e}"

    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
    return


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
            eth_btc_resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=btc", timeout=10)
            eth_btc_data = eth_btc_resp.json()
            eth_btc = round(eth_btc_data["ethereum"]["btc"], 5)
            prompt = (
                f"BTC Dominance: {btc_d}%\n"
                f"ETH Dominance: {eth_d}%\n"
                f"ETH/BTC: {eth_btc}\n"
                "Оцени вероятность альтсезона."
            )
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            await update.message.reply_text(f"📊 Альтсезон:\n\n{response.choices[0].message.content.strip()}", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка при получении данных: {e}", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

    elif text == "🧠 Интерпретировать новости":
        await update.message.reply_text("📎 Пришлите ссылку на событие с Investing.com (например, https://ru.investing.com/economic-calendar/gdp-119)", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

    elif text == "🔁 Перезапустить бота":
        await start(update, context)

    elif text == "📢 Опубликовать пост":
        await publish_post(update, context)

    else:
        await update.message.reply_text("Выбери пункт из меню.", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"[COMMAND] /publish от {update.effective_user.id}")
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

async def post_init(app):
    logging.info("[INIT] post_init запущен")
    await app.bot.set_my_commands([
        BotCommand("start", "Перезапустить бота"),
        BotCommand("publish", "Опубликовать пост")
    ])
    asyncio.create_task(hourly_news_check(app))

async def hourly_news_check(app):
    await asyncio.sleep(10)
    return

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()






















