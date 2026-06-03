import os
from pathlib import Path

# Попытка загрузить переменные из .env если файл есть
if Path('.env').exists():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception as e:
        print(f"[WARN] Не удалось загрузить .env: {e}")

# Получение токена и пути к базе из переменных окружения
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/database.db')

# Обработка ошибок: выводим ошибку, если токен не задан
if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN не найден. Задайте его в .env или переменных окружения!"
    )