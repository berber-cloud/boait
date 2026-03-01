FROM python:3.10-slim

# Принудительно прописываем DNS в конфиг системы
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:${PATH}"

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Запуск через небольшой bash-костыль, который обновит DNS при старте
CMD ["sh", "-c", "echo 'nameserver 8.8.8.8' > /etc/resolv.conf && python main.py"]
