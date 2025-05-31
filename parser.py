import requests
from bs4 import BeautifulSoup
from interpreter import interpret_event

def get_important_events():
    url = "https://www.investing.com/economic-calendar/"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        error_message = f"[Ошибка подключения к Investing.com]: {e}"
        print(error_message)
        return [{"error": error_message}]  # возвращаем ошибку в bot.py

    soup = BeautifulSoup(r.text, 'lxml')
    results = []

    for row in soup.select("tr.js-event-item"):
        bull_icons = row.select(".grayFullBullishIcon")
        impact = len(bull_icons)
        if impact < 2:
            continue

        try:
            event = row.select_one(".event").text.strip()
            time = row.get("data-event-datetime")
            actual = row.select_one(".actual").text.strip().replace('%', '').replace(',', '.')
            forecast = row.select_one(".forecast").text.strip().replace('%', '').replace(',', '.')

            if actual and forecast:
                actual_val = float(actual)
                forecast_val = float(forecast)
                summary, probability = interpret_event(event, actual_val, forecast_val)

                results.append({
                    "event": event,
                    "time": time,
                    "actual": actual,
                    "forecast": forecast,
                    "summary": summary,
                    "probability": probability,
                    "bulls": impact
                })
        except:
            continue

    return results


