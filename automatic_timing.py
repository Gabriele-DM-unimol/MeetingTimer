import datetime
import re

import requests
from bs4 import BeautifulSoup


MONTHS_IT = {
    1: "gennaio",
    2: "febbraio",
    3: "marzo",
    4: "aprile",
    5: "maggio",
    6: "giugno",
    7: "luglio",
    8: "agosto",
    9: "settembre",
    10: "ottobre",
    11: "novembre",
    12: "dicembre",
}
JW_BASE_URL = "https://www.jw.org/it/biblioteca-digitale/guida-attivita-adunanza"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def ottieni_url_sito_ufficiale():
    """Genera l'URL ufficiale di jw.org per la settimana corrente."""
    monday, sunday = _current_week_range()
    publication_slug = _publication_slug(monday, sunday)
    week_slug = _week_slug(monday, sunday)
    return f"{JW_BASE_URL}/{publication_slug}/{week_slug}/"


def estrai_programma_con_titoli():
    url = ottieni_url_sito_ufficiale()
    print(f"Collegamento a: {url}\n")

    response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
    if response.status_code != 200:
        print(f"Errore di connessione: {response.status_code}")
        return []

    page_text = _extract_main_text(response.text)
    numbered_titles = re.findall(
        r"\b\d+\.\s+(.+?)\s*[\(\[]\s*\d+\s*min\.?\s*[\)\]]",
        page_text,
        re.IGNORECASE,
    )
    durations = re.findall(r"[\(\[]\s*(\d+)\s*min\.?\s*[\)\]]", page_text, re.IGNORECASE)[1:-1]

    return _build_program(numbered_titles, durations)


def _current_week_range():
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


def _publication_slug(monday, sunday):
    start_month = monday.month if monday.month % 2 != 0 else monday.month - 1
    end_month = start_month + 1

    if start_month == 11 and sunday.month == 1:
        return f"mwb-novembre-dicembre-{monday.year}"

    return f"mwb-{MONTHS_IT[start_month]}-{MONTHS_IT[end_month]}-{monday.year}"


def _week_slug(monday, sunday):
    if monday.month != sunday.month:
        return (
            "Programma-adunanza-Vita-e-ministero-dal-"
            f"{monday.day}-{MONTHS_IT[monday.month]}-al-"
            f"{sunday.day}-{MONTHS_IT[sunday.month]}-{sunday.year}"
        )

    return (
        "Programma-adunanza-Vita-e-ministero-dal-"
        f"{monday.day}-al-{sunday.day}-{MONTHS_IT[sunday.month]}-{sunday.year}"
    )


def _extract_main_text(html):
    soup = BeautifulSoup(html, "html.parser")
    main_content = soup.find(id="regionMain") or soup.find("article") or soup.body
    return main_content.get_text(" ", strip=True)


def _build_program(numbered_titles, durations):
    program = [
        _timer(1, "Cantico e preghiera", 5),
        _timer(2, "Commenti introduttivi", 1),
    ]
    control_durations = [5]
    title_index = 0

    for duration in durations:
        duration_minutes = int(duration)
        control_durations.append(duration_minutes)

        title = _next_title(numbered_titles, title_index)
        title_index += 1
        program.append(_timer(len(program) + 1, title, duration_minutes))

        if 25 < sum(control_durations) < 46:
            control_durations.append(1)
            program.append(_timer(len(program) + 1, "Consigli", 1))

        if sum(control_durations) == 45:
            control_durations.append(5)
            program.append(_timer(len(program) + 1, "Cantico", 5))

    program.append(_timer(len(program) + 1, "Commenti conclusivi", 3))
    program.append(_timer(len(program) + 1, "Cantico e preghiera", 5))
    return program


def _next_title(numbered_titles, title_index):
    if title_index >= len(numbered_titles):
        return "Parte Adunanza"
    return numbered_titles[title_index].rstrip(":- ").strip()


def _timer(timer_id, name, duration_minutes):
    duration_seconds = duration_minutes * 60
    return {
        "id": timer_id,
        "name": name,
        "start": "19:00:00",
        "end": "19:00:00",
        "maxDuration": duration_seconds,
        "duration": duration_seconds,
        "active": False,
    }
