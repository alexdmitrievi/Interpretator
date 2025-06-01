import asyncio
import os
import requests
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import TELEGRAM_TOKEN, CHAT_ID, OPENAI_API_KEY
from parser import get_important_events
from datetime import datetime
import pytz
from interpreter import btc_eth_forecast
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

keyboard = ReplyKeyboardMarkup(
    [
        ["🧠 Интерпретировать новости"],
        ["🔬 Посмотреть ожидаемые события"],
        ["📉 Прогноз по BTC", "📉 Прогноз по ETH"],
        ["📊 Оценить альтсезон"],
        ["🔁 Перезапустить бота"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я интерпретирую макроэкономические новости.\nВыбери действие ниже:",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🧠 Интерпретировать новости":
        await send_digest(update.effective_chat.id, context, debug=False)
    elif text == "🔬 Посмотреть ожидаемые события":
        await send_digest(update.effective_chat.id, context, debug=True)
    elif text == "🔁 Перезапустить бота":
        await start(update, context)
    elif text == "📉 Прогноз по BTC":
        await update.message.reply_text("Введите текущую цену BTC (например, 104230):", reply_markup=keyboard)
        context.user_data["awaiting_btc_price"] = True
    elif text == "📉 Прогноз по ETH":
        await update.message.reply_text("Введите текущую цену ETH (например, 3820):", reply_markup=keyboard)
        context.user_data["awaiting_eth_price"] = True
    elif text == "📊 Оценить альтсезон":
        await assess_altseason(update, context)
    elif context.user_data.get("awaiting_btc_price"):
        context.user_data["awaiting_btc_price"] = False
        try:
            price = float(text.replace(",", ".").replace("$", "").strip())
            forecast = await gpt_price_forecast("BTC", price)
            await update.message.reply_text(forecast, reply_markup=keyboard)
        except ValueError:
            await update.message.reply_text("Некорректная цена. Введите число, например: 103500", reply_markup=keyboard)
    elif context.user_data.get("awaiting_eth_price"):
        context.user_data["awaiting_eth_price"] = False
        try:
            price = float(text.replace(",", ".").replace("$", "").strip())
            forecast = await gpt_price_forecast("ETH", price)
            await update.message.reply_text(forecast, reply_markup=keyboard)
        except ValueError:
            await update.message.reply_text("Некорректная цена. Введите число, например: 3820", reply_markup=keyboard)

async def assess_altseason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        data = r.json()
        btc_d = round(data["data"]["market_cap_percentage"]["btc"], 2)
        eth_d = round(data["data"]["market_cap_percentage"]["eth"], 2)

        eth_btc_resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=btc", timeout=10)
        eth_btc_data = eth_btc_resp.json()

        if "ethereum" not in eth_btc_data or "btc" not in eth_btc_data["ethereum"]:
            raise ValueError("Пара ETH/BTC не найдена в ответе CoinGecko")

        eth_btc = round(eth_btc_data["ethereum"]["btc"], 5)

        prompt = (
            f"BTC Dominance: {btc_d}%\nETH Dominance: {eth_d}%\nETH/BTC: {eth_btc}\n"
            "На основе этих показателей оцени, насколько вероятен альтсезон."
            " Ответь кратко: 1) оценка вероятности, 2) аргументы, 3) общее заключение."
        )

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        result = (
            f"📊 Оценка альтсезона:\n\n"
            f"▪️ BTC Dominance: {btc_d}%\n"
            f"▪️ ETH Dominance: {eth_d}%\n"
            f"▪️ ETH/BTC: {eth_btc}\n\n"
            f"🧠 GPT: {response.choices[0].message.content.strip()}"
        )
        await update.message.reply_text(result, reply_markup=keyboard)

    except Exception as e:
        print(f"[ОШИБКА альтсезона]: {e}")
        await update.message.reply_text(f"⚠️ Ошибка при оценке альтсезона: {e}", reply_markup=keyboard)

async def gpt_price_forecast(asset, price):
    prompt = (
        f"Цена {asset}: ${price}\n"
        "На основе типичных рыночных условий и поведения крипторынка оцени:\n"
        "1. Возможна ли техническая коррекция и до каких уровней?\n"
        "2. Каков риск медвежьего разворота?\n"
        "3. Сохраняется ли бычья структура?\n"
        "Ответь кратко и по пунктам."
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return f"📉 Прогноз по {asset}:\n\n{response.choices[0].message.content.strip()}"
    except Exception as e:
        return f"⚠️ Ошибка GPT: {e}"

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
        response = await client.chat.completions.create(
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
    from telegram import InlineKeyboardMarkup

    await asyncio.sleep(60)  # Подождать минуту после запуска

    keyboard = InlineKeyboardMarkup([])  # Замените на нужные кнопки, если они есть

    while True:
        try:
            await send_digest(CHAT_ID, app, debug=False)

            moscow = pytz.timezone("Europe/Moscow")
            now = datetime.now(moscow).strftime("%H:%M")

            await app.bot.send_message(
                chat_id=CHAT_ID,
                text=f"⏰ Цикл завершён в {now} (МСК). Следующее обновление через 3 часа.",
                reply_markup=keyboard
            )

        except Exception as e:
            await app.bot.send_message(
                chat_id=CHAT_ID,
                text=f"❌ Ошибка: {e}",
                reply_markup=keyboard
            )

        await asyncio.sleep(3 * 3600)  # Подождать 3 часа до следующего запуска

async def after_startup(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Перезапустить бота"),
        BotCommand("digest", "Интерпретировать новости"),
        BotCommand("upcoming", "Ожидаемые события"),
        BotCommand("btc", "Прогноз по BTC"),
        BotCommand("eth", "Прогноз по ETH"),
        BotCommand("alts", "Оценить альтсезон")
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












