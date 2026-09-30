import datetime


def get_current_season() -> str:
    """Определяет текущий сезон по дате.
    Возвращает: 'halloween', 'new_year', 'valentine', 'spring', 'easter', 'default'."""
    now = datetime.datetime.now()
    month = now.month
    day = now.day

    # 🎃 Хэллоуин: 20 октября — 5 ноября
    if (month == 10 and day >= 20) or (month == 11 and day <= 5):
        return "halloween"

    # 🎄 Новый год: 15 декабря — 15 января
    if (month == 12 and day >= 15) or (month == 1 and day <= 15):
        return "new_year"

    # 💖 День святого Валентина: 7 февраля — 15 февраля
    if month == 2 and 7 <= day <= 15:
        return "valentine"

    # 🌸 Весна / 8 марта: 1 марта — 10 марта
    if month == 3 and 1 <= day <= 10:
        return "spring"

    # 🐣 Пасха (условно — первая неделя апреля): 1 апреля — 10 апреля
    if month == 4 and 1 <= day <= 10:
        return "easter"

    # 🎉 День рождения сервера (можно настроить): 3 декабря
    if month == 12 and day == 3:
        return "server_birthday"

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
    periods = {
        "halloween": "20 октября — 5 ноября",
        "new_year": "15 декабря — 15 января",
        "valentine": "7 февраля — 15 февраля",
        "spring": "1 марта — 10 марта",
        "easter": "1 апреля — 10 апреля",
        "server_birthday": "3 декабря",
        "default": "весь год"
    }
    return periods.get(season, "—")


def get_all_seasons() -> list:
    """Возвращает список всех сезонов."""
    return ["halloween", "new_year", "valentine", "spring", "easter", "server_birthday"]