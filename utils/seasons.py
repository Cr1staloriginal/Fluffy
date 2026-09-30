import datetime
import os


def get_server_birthday() -> tuple:
    """Возвращает день и месяц дня рождения сервера из .env.
    По умолчанию: 30 октября."""
    date_str = os.getenv("SERVER_BIRTHDAY", "30-10")  # формат ДД-ММ
    try:
        day, month = map(int, date_str.split("-"))
        return (day, month)
    except:
        return (30, 10)  # fallback


def get_current_season() -> str:
    """Определяет текущий сезон по дате.
    Приоритет: server_birthday > valentine > halloween > new_year > spring > easter > default.
    Возвращает: 'halloween', 'new_year', 'valentine', 'spring', 'easter', 'server_birthday', 'default'."""
    now = datetime.datetime.now()
    month = now.month
    day = now.day

    # 🎂 День рождения сервера — НАИВЫСШИЙ ПРИОРИТЕТ (проверяется первым)
    server_bday_day, server_bday_month = get_server_birthday()
    if month == server_bday_month and day == server_bday_day:
        return "server_birthday"

    # 💖 День святого Валентина: 7 февраля — 15 февраля
    if month == 2 and 7 <= day <= 15:
        return "valentine"

    # 🎃 Хэллоуин: 20 октября — 5 ноября
    if (month == 10 and day >= 20) or (month == 11 and day <= 5):
        return "halloween"

    # 🎄 Новый год: 15 декабря — 15 января
    if (month == 12 and day >= 15) or (month == 1 and day <= 15):
        return "new_year"

    # 🌸 Весна / 8 марта: 1 марта — 10 марта
    if month == 3 and 1 <= day <= 10:
        return "spring"

    # 🐣 Пасха (условно): 1 апреля — 10 апреля
    if month == 4 and 1 <= day <= 10:
        return "easter"

    return "default"


def get_season_name(season: str) -> str:
    """Возвращает человекочитаемое название сезона."""
    names = {
        "halloween": "🎃 Хэллоуин",
        "new_year": "🎄 Новый год",
        "valentine": "💖 День Валентина",
        "spring": "🌸 Весна / 8 марта",
        "easter": "🐣 Пасха",
        "server_birthday": "🎂 День рождения сервера",
        "default": "🌟 Обычный"
    }
    return names.get(season, season)


def get_season_end_date(season: str) -> str:
    """Возвращает описание периода сезона."""
    if season == "server_birthday":
        day, month = get_server_birthday()
        return f"{day:02d}.{month:02d} (один день)"
    
    periods = {
        "halloween": "20 октября — 5 ноября",
        "new_year": "15 декабря — 15 января",
        "valentine": "7 февраля — 15 февраля",
        "spring": "1 марта — 10 марта",
        "easter": "1 апреля — 10 апреля",
        "default": "весь год"
    }
    return periods.get(season, "—")


def get_all_seasons() -> list:
    """Возвращает список всех сезонов."""
    return ["halloween", "new_year", "valentine", "spring", "easter", "server_birthday"]