def interpret_event(event_name, actual, forecast):
    delta = actual - forecast
    if "безработица" in event_name.lower():
        if delta > 0:
            return "❗Безработица выше прогноза — возможны стимулы → рост крипты", 70
        else:
            return "✅Безработица ниже прогноза — доллар может укрепиться", 60

    elif "ставка" in event_name.lower():
        if delta > 0:
            return "📈Ставка повышена — укрепление доллара, шорт крипты", 80
        else:
            return "📉Ставка понижена — рост крипты, вливание ликвидности", 75

    elif "инфляция" in event_name.lower() or "CPI" in event_name:
        if delta > 0:
            return "⚠️Инфляция выше прогноза — рынок может просесть", 65
        else:
            return "✅Инфляция ниже прогноза — позитив для крипты", 70

    return "ℹ️ Нет шаблона для интерпретации", 50

def btc_eth_forecast(event_name, delta):
    event = event_name.lower()

    # базовая логика — можешь кастомизировать под себя
    if "ставка" in event:
        if delta > 0:
            return "📉 Прогноз: возможна коррекция BTC и ETH из-за ужесточения денежной политики."
        else:
            return "🚀 Прогноз: ожидание роста BTC и ETH на фоне смягчения условий."

    elif "инфляция" in event or "cpi" in event:
        if delta > 0:
            return "📉 Инфляция выше прогноза — возможен краткосрочный отскок доллара и давление на крипту."
        else:
            return "🚀 Инфляция падает — вероятен приток ликвидности, BTC/ETH могут укрепиться."

    elif "безработица" in event:
        if delta > 0:
            return "🚀 Рост безработицы → возможны стимулы → шанс для роста BTC и ETH."
        else:
            return "📉 Сильный рынок труда — крипта может замедлиться."

    return "ℹ️ Прогноз по BTC/ETH не сформирован (неизвестный тип события)."
