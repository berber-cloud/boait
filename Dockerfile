FROM python:3.10-slim

# Создаем пользователя
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:${PATH}"
WORKDIR /home/user/app

# Копируем и ставим зависимости
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY --chown=user . .

# Запуск
CMD ["python", "main.py"]
