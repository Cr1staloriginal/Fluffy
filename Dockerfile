FROM python:3.13-slim

# Метаданные образа (опционально, но полезно)
LABEL maintainer="your-email@example.com"
LABEL description="Discord bot based on discord.py/disnake"

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем только необходимые файлы (лучше, чем COPY . /app/)
COPY requirements.txt ./

# Обновляем pip и устанавливаем зависимости
# --no-cache-dir экономит место, т.к. кэш pip не нужен в финальном образе
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальной код ПОСЛЕ установки зависимостей
# Это ускоряет сборку при изменении кода (зависимости кешируются)
COPY . ./

# Проверяем наличие main.py (защита от ошибки)
RUN if [ ! -f "main.py" ]; then echo "Error: main.py not found!" && exit 1; fi

# Порт, если бот использует веб-сервер (например, для healthcheck)
# EXPOSE 8080

# Запускаем бота
CMD ["python", "main.py"]
