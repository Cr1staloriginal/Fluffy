FROM python:3.13-slim

# Метаданные образа
LABEL maintainer="your-email@example.com"
LABEL description="Discord bot based on disnake"

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем ffmpeg и системные библиотеки (добавлено!)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    libblas3 \
    liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . ./

# Проверяем наличие main.py
RUN if [ ! -f "main.py" ]; then echo "Error: main.py not found!" && exit 1; fi

# Запускаем бота
CMD ["python", "main.py"]