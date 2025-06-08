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

    elif "инфляция" in event_name.lower() or "cpi" in event_name.lower():
        if delta > 0:
            return "⚠️Инфляция выше прогноза — рынок может просесть", 65
        else:
            return "✅Инфляция ниже прогноза — позитив для крипты", 70

    return "ℹ️ Нет шаблона для интерпретации", 50

def get_trading_signal(event_name, delta):
    event = event_name.lower()

    if "ставка" in event:
        if delta > 0:
            return ("Sell", "Sell")
        else:
            return ("Buy", "Buy")

    elif "инфляция" in event or "cpi" in event:
        if delta > 0:
            return ("Sell", "Sell")
        else:
            return ("Buy", "Buy")

    elif "безработица" in event:
        if delta > 0:
            return ("Buy", "Buy")
        else:
            return ("Neutral", "Neutral")

    return ("Neutral", "Neutral")

