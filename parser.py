import requests
from bs4 import BeautifulSoup
from interpreter import interpret_event
from datetime import datetime
import pytz

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
    parse_errors = 0

    for row in soup.select("tr.js-event-item"):
        sentiment = row.select_one(".sentiment")
        if not sentiment:
            continue

        title = sentiment.get("title", "").lower()
        if "high" in title:
            bulls = 3
        else:
            continue

        try:
            event = row.select_one(".event").text.strip()
            time_raw = row.get("data-event-datetime")

            if time_raw:
                utc_dt = datetime.strptime(time_raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
                local_dt = utc_dt.astimezone(pytz.timezone("Europe/Moscow"))
                time_str = local_dt.strftime("%Y-%m-%d %H:%M:%S (%Z)")
            else:
                time_str = "—"

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
                    "time": time_str,
                    "actual": actual,
                    "forecast": forecast,
                    "summary": summary,
                    "probability": probability,
                    "bulls": bulls
                })
            elif debug:
                results.append({
                    "event": event,
                    "time": time_str,
                    "actual": actual or "–",
                    "forecast": forecast or "–",
                    "summary": "Ожидается событие",
                    "probability": 0,
                    "bulls": bulls
                })
        except Exception as e:
            parse_errors += 1
            print(f"[Парсер: ошибка при обработке строки] {e}")
            continue

    if debug and parse_errors > 0:
        print(f"⚠️ Обнаружено ошибок при парсинге: {parse_errors}")

    return results

def parse_event_page(url: str):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return {"error": f"Ошибка при подключении: {e}"}

    soup = BeautifulSoup(r.text, 'lxml')

    try:
        title_tag = soup.select_one("h1")
        event_name = title_tag.text.strip() if title_tag else "Неизвестное событие"

        actual = None
        forecast = None

        for row in soup.select("div[class*=genTbl] tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            label = cols[0].text.strip().lower()
            value = cols[1].text.strip()
            if "факт" in label:
                actual = value
            elif "прогноз" in label:
                forecast = value

        # Если данные ещё не опубликованы (– или пусто)
        if not actual or actual == "–" or not forecast or forecast == "–":
            return {
                "event": event_name,
                "summary": "⏳ Данные ещё не опубликованы."
            }

        actual_val = float(actual.replace("%", "").replace(",", "."))
        forecast_val = float(forecast.replace("%", "").replace(",", "."))

        summary, probability = interpret_event(event_name, actual_val, forecast_val)

        return {
            "event": event_name,
            "actual": actual,
            "forecast": forecast,
            "summary": summary,
            "probability": probability
        }
    except Exception as e:
        return {"error": f"Ошибка парсинга страницы: {e}"}










