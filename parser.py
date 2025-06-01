import requests
from bs4 import BeautifulSoup
from interpreter import interpret_event

def get_important_events(debug=False):
    url = "https://www.investing.com/economic-calendar/"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        error_message = f"[Ошибка подключения к Investing.com]: {e}"
        print(error_message)
        return [{"error": error_message}]

    soup = BeautifulSoup(r.text, 'lxml')
    results = []

    for row in soup.select("tr.js-event-item"):
        sentiment = row.select_one(".sentiment")
        if not sentiment:
            continue

        title = sentiment.get("title", "").lower()
        if "medium" in title:
            bulls = 2
        elif "high" in title:
            bulls = 3
        else:
            continue

        try:
            event = row.select_one(".event").text.strip()
            time = row.get("data-event-datetime")
            actual_tag = row.select_one(".actual")
            forecast_tag = row.select_one(".forecast")

            actual = actual_tag.text.strip().replace('%', '').replace(',', '.') if actual_tag else ""
            forecast = forecast_tag.text.strip().replace('%', '').replace(',', '.') if forecast_tag else ""

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
                    "bulls": bulls
                })
            elif debug:
                results.append({
                    "event": event,
                    "time": time,
                    "actual": actual or "–",
                    "forecast": forecast or "–",
                    "summary": "Ожидается событие",
                    "probability": 0,
                    "bulls": bulls
                })
        except:
            continue

    return results




