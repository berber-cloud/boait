FROM python:3.10-slim

# Создаем пользователя, под которым работает Hugging Face
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:${PATH}"

WORKDIR /home/user/app

# Копируем зависимости
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота
COPY --chown=user . .

# Запуск бота (убедись, что главный файл называется main.py)
CMD ["python", "main.py"]
