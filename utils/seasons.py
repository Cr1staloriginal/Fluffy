import datetime
import os


def get_server_birthday() -> tuple[int, int]:
    """Return configured server birthday as (day, month); default is 30 October."""
    date_str = os.getenv("SERVER_BIRTHDAY", "30-10")
    try:
        day, month = map(int, date_str.split("-", maxsplit=1))
        datetime.date(2000, month, day)  # validate day/month, including leap-day support
        return day, month
    except (TypeError, ValueError):
        return 30, 10


def get_local_time() -> datetime.datetime:
    """Current time in the configured server timezone (TIMEZONE_OFFSET, default UTC+3)."""
    try:
        offset = int(os.getenv("TIMEZONE_OFFSET", "3"))
        if not -12 <= offset <= 14:
            raise ValueError
    except (TypeError, ValueError):
        offset = 3
    tz = datetime.timezone(datetime.timedelta(hours=offset))
    return datetime.datetime.now(tz)


def get_current_season() -> str:
    """Determine the active seasonal theme using server-local time."""
    now = get_local_time()
    month, day = now.month, now.day

    birthday_day, birthday_month = get_server_birthday()
    if (month, day) == (birthday_month, birthday_day):
        return "server_birthday"
    if month == 2 and 7 <= day <= 15:
        return "valentine"
    if (month == 10 and day >= 20) or (month == 11 and day <= 5):
        return "halloween"
    if (month == 12 and day >= 15) or (month == 1 and day <= 15):
        return "new_year"
    if month == 3 and 1 <= day <= 10:
        return "spring"
    if month == 4 and 1 <= day <= 10:
        return "easter"
    return "default"


def get_season_name(season: str) -> str:
    names = {
        "halloween": "🎃 Хэллоуин",
        "new_year": "🎄 Новый год",
        "valentine": "💖 День Валентина",
        "spring": "🌸 Весна / 8 марта",
        "easter": "🐣 Пасха",
        "server_birthday": "🎂 День рождения сервера",
        "default": "🌟 Обычный",
    }
    return names.get(season, season)


def get_season_end_date(season: str) -> str:
    if season == "server_birthday":
        day, month = get_server_birthday()
        return f"{day:02d}.{month:02d} (один день)"
    periods = {
        "halloween": "20 октября — 5 ноября",
        "new_year": "15 декабря — 15 января",
        "valentine": "7 февраля — 15 февраля",
        "spring": "1 марта — 10 марта",
        "easter": "1 апреля — 10 апреля",
        "default": "весь год",
    }
    return periods.get(season, "—")


def get_all_seasons() -> list[str]:
    return ["halloween", "new_year", "valentine", "spring", "easter", "server_birthday"]
